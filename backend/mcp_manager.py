"""
MCP 서버 관리자 - Grafana 및 CloudWatch MCP 서버 통합

이 모듈은 MCP(Model Context Protocol) 서버의 수명 주기를 관리하고
LangChain 에이전트에서 사용할 수 있는 도구를 제공합니다.

주요 기능:
- Grafana MCP 서버 초기화 및 관리
- CloudWatch MCP 서버 초기화 및 관리
- 모든 MCP 서버에서 도구 집계
- MCP 도구 실행 및 결과 처리
- 도구 호출 오류 처리 및 로깅

요구사항: 5.1, 5.2, 5.3, 5.4, 5.5
"""

import asyncio
import logging
import time
import traceback
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field
from enum import Enum

from mcp import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters
from langchain_core.tools import BaseTool, StructuredTool

from config import GrafanaConfig, CloudWatchConfig

# 로거 설정
logger = logging.getLogger(__name__)


# =============================================================================
# MCP 도구 실행 관련 예외 클래스
# =============================================================================

class MCPToolError(Exception):
    """
    MCP 도구 실행 오류 기본 예외 클래스
    
    모든 MCP 도구 관련 오류의 기본 클래스입니다.
    
    Attributes:
        tool_name: 오류가 발생한 도구 이름
        server_name: MCP 서버 이름
        message: 오류 메시지
        original_error: 원본 예외 (있는 경우)
    
    요구사항: 5.5
    """
    
    def __init__(
        self,
        tool_name: str,
        server_name: str,
        message: str,
        original_error: Optional[Exception] = None
    ):
        self.tool_name = tool_name
        self.server_name = server_name
        self.message = message
        self.original_error = original_error
        super().__init__(self._format_message())
    
    def _format_message(self) -> str:
        """오류 메시지 포맷팅"""
        base_msg = f"[{self.server_name}] 도구 '{self.tool_name}' 오류: {self.message}"
        if self.original_error:
            base_msg += f" (원인: {type(self.original_error).__name__}: {str(self.original_error)})"
        return base_msg


class MCPToolExecutionError(MCPToolError):
    """
    MCP 도구 실행 중 발생한 오류
    
    도구 호출 중 발생하는 런타임 오류를 나타냅니다.
    
    요구사항: 5.5
    """
    pass


class MCPToolTimeoutError(MCPToolError):
    """
    MCP 도구 실행 시간 초과 오류
    
    도구 호출이 지정된 시간 내에 완료되지 않은 경우 발생합니다.
    
    Attributes:
        timeout_seconds: 시간 초과 값 (초)
    
    요구사항: 5.5
    """
    
    def __init__(
        self,
        tool_name: str,
        server_name: str,
        timeout_seconds: float,
        original_error: Optional[Exception] = None
    ):
        self.timeout_seconds = timeout_seconds
        message = f"실행 시간 초과 ({timeout_seconds}초)"
        super().__init__(tool_name, server_name, message, original_error)


class MCPToolConnectionError(MCPToolError):
    """
    MCP 서버 연결 오류
    
    MCP 서버와의 연결이 끊어졌거나 사용할 수 없는 경우 발생합니다.
    
    요구사항: 5.5
    """
    pass


class MCPToolValidationError(MCPToolError):
    """
    MCP 도구 인자 검증 오류
    
    도구 호출 시 잘못된 인자가 전달된 경우 발생합니다.
    
    Attributes:
        invalid_args: 잘못된 인자 정보
    
    요구사항: 5.5
    """
    
    def __init__(
        self,
        tool_name: str,
        server_name: str,
        message: str,
        invalid_args: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None
    ):
        self.invalid_args = invalid_args or {}
        super().__init__(tool_name, server_name, message, original_error)


class MCPToolResultStatus(Enum):
    """
    MCP 도구 실행 결과 상태
    
    도구 실행 결과의 상태를 나타내는 열거형입니다.
    """
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"
    CONNECTION_ERROR = "connection_error"
    VALIDATION_ERROR = "validation_error"


@dataclass
class MCPToolResult:
    """
    MCP 도구 실행 결과를 저장하는 데이터 클래스
    
    도구 실행의 결과, 상태, 메타데이터를 포함합니다.
    
    Attributes:
        tool_name: 실행된 도구 이름
        server_name: MCP 서버 이름
        status: 실행 결과 상태
        result: 실행 결과 (성공 시)
        error_message: 오류 메시지 (실패 시)
        execution_time_ms: 실행 시간 (밀리초)
        arguments: 도구에 전달된 인자
    
    요구사항: 5.4, 5.5
    """
    tool_name: str
    server_name: str
    status: MCPToolResultStatus
    result: Optional[str] = None
    error_message: Optional[str] = None
    execution_time_ms: float = 0.0
    arguments: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MCPServerInfo:
    """
    MCP 서버 정보를 저장하는 데이터 클래스
    
    Attributes:
        name: 서버 이름 (예: 'grafana', 'cloudwatch')
        session: MCP 클라이언트 세션
        tools: 서버에서 제공하는 도구 목록
        is_connected: 연결 상태
    """
    name: str
    session: Optional[ClientSession] = None
    tools: List[Any] = field(default_factory=list)
    is_connected: bool = False


# =============================================================================
# MCP 도구 실행 래퍼 함수
# =============================================================================

async def execute_mcp_tool(
    session: Any,
    tool_name: str,
    server_name: str,
    arguments: Dict[str, Any],
    timeout_seconds: float = 30.0
) -> MCPToolResult:
    """
    MCP 도구를 실행하고 결과를 처리하는 래퍼 함수
    
    이 함수는 MCP 도구 호출을 래핑하여 일관된 오류 처리, 로깅,
    결과 포맷팅을 제공합니다.
    
    Args:
        session: MCP 클라이언트 세션
        tool_name: 실행할 도구 이름
        server_name: MCP 서버 이름
        arguments: 도구에 전달할 인자
        timeout_seconds: 실행 시간 제한 (초, 기본값: 30.0)
    
    Returns:
        MCPToolResult: 도구 실행 결과
    
    요구사항: 5.4, 5.5
    """
    start_time = time.time()
    
    # 도구 호출 시작 로깅
    logger.info(
        f"MCP 도구 실행 시작: tool={tool_name}, server={server_name}, "
        f"timeout={timeout_seconds}s"
    )
    logger.debug(f"도구 인자: {_sanitize_arguments_for_logging(arguments)}")
    
    try:
        # 세션 유효성 검사
        if session is None:
            raise MCPToolConnectionError(
                tool_name=tool_name,
                server_name=server_name,
                message="MCP 세션이 None입니다. 서버 연결을 확인하세요."
            )
        
        # 시간 제한이 있는 도구 호출
        try:
            result = await asyncio.wait_for(
                session.call_tool(tool_name, arguments),
                timeout=timeout_seconds
            )
        except asyncio.TimeoutError:
            execution_time_ms = (time.time() - start_time) * 1000
            logger.error(
                f"MCP 도구 시간 초과: tool={tool_name}, server={server_name}, "
                f"timeout={timeout_seconds}s, execution_time={execution_time_ms:.2f}ms"
            )
            raise MCPToolTimeoutError(
                tool_name=tool_name,
                server_name=server_name,
                timeout_seconds=timeout_seconds
            )
        
        # 결과 처리
        result_text = _process_mcp_result(result)
        execution_time_ms = (time.time() - start_time) * 1000
        
        # 성공 로깅
        logger.info(
            f"MCP 도구 실행 성공: tool={tool_name}, server={server_name}, "
            f"execution_time={execution_time_ms:.2f}ms, "
            f"result_length={len(result_text)} chars"
        )
        logger.debug(f"도구 결과 (처음 500자): {result_text[:500]}...")
        
        return MCPToolResult(
            tool_name=tool_name,
            server_name=server_name,
            status=MCPToolResultStatus.SUCCESS,
            result=result_text,
            execution_time_ms=execution_time_ms,
            arguments=arguments
        )
        
    except MCPToolTimeoutError:
        # 시간 초과 오류는 이미 로깅됨
        execution_time_ms = (time.time() - start_time) * 1000
        return MCPToolResult(
            tool_name=tool_name,
            server_name=server_name,
            status=MCPToolResultStatus.TIMEOUT,
            error_message=f"도구 실행 시간 초과 ({timeout_seconds}초)",
            execution_time_ms=execution_time_ms,
            arguments=arguments
        )
        
    except MCPToolConnectionError as e:
        execution_time_ms = (time.time() - start_time) * 1000
        logger.error(
            f"MCP 연결 오류: tool={tool_name}, server={server_name}, "
            f"error={str(e)}"
        )
        return MCPToolResult(
            tool_name=tool_name,
            server_name=server_name,
            status=MCPToolResultStatus.CONNECTION_ERROR,
            error_message=str(e),
            execution_time_ms=execution_time_ms,
            arguments=arguments
        )
        
    except Exception as e:
        execution_time_ms = (time.time() - start_time) * 1000
        error_details = _format_error_details(e)
        
        logger.error(
            f"MCP 도구 실행 실패: tool={tool_name}, server={server_name}, "
            f"error_type={type(e).__name__}, error={str(e)}, "
            f"execution_time={execution_time_ms:.2f}ms"
        )
        logger.debug(f"오류 스택 트레이스:\n{traceback.format_exc()}")
        
        return MCPToolResult(
            tool_name=tool_name,
            server_name=server_name,
            status=MCPToolResultStatus.ERROR,
            error_message=error_details,
            execution_time_ms=execution_time_ms,
            arguments=arguments
        )


def _process_mcp_result(result: Any) -> str:
    """
    MCP 도구 실행 결과를 문자열로 처리합니다.
    
    다양한 형식의 MCP 결과를 일관된 문자열 형식으로 변환합니다.
    
    Args:
        result: MCP 도구 실행 결과
    
    Returns:
        str: 처리된 결과 문자열
    
    요구사항: 5.4
    """
    if result is None:
        return ""
    
    # content 속성이 있는 경우
    if hasattr(result, 'content'):
        content = result.content
        
        if isinstance(content, list):
            # 여러 콘텐츠 블록이 있는 경우
            text_parts = []
            for content_block in content:
                if hasattr(content_block, 'text'):
                    text_parts.append(content_block.text)
                elif isinstance(content_block, str):
                    text_parts.append(content_block)
                elif isinstance(content_block, dict) and 'text' in content_block:
                    text_parts.append(content_block['text'])
                else:
                    text_parts.append(str(content_block))
            return "\n".join(text_parts)
        
        elif hasattr(content, 'text'):
            return content.text
        
        elif isinstance(content, str):
            return content
        
        elif isinstance(content, dict) and 'text' in content:
            return content['text']
        
        else:
            return str(content)
    
    # 문자열인 경우
    if isinstance(result, str):
        return result
    
    # 딕셔너리인 경우
    if isinstance(result, dict):
        if 'text' in result:
            return result['text']
        if 'result' in result:
            return str(result['result'])
        if 'data' in result:
            return str(result['data'])
    
    # 기타 경우
    return str(result)


def _sanitize_arguments_for_logging(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    로깅을 위해 인자를 정제합니다.
    
    민감한 정보(API 키, 비밀번호 등)를 마스킹합니다.
    
    Args:
        arguments: 원본 인자 딕셔너리
    
    Returns:
        Dict[str, Any]: 정제된 인자 딕셔너리
    
    요구사항: 5.4
    """
    sensitive_keys = {'api_key', 'apikey', 'password', 'secret', 'token', 'credential'}
    sanitized = {}
    
    for key, value in arguments.items():
        key_lower = key.lower()
        if any(sensitive in key_lower for sensitive in sensitive_keys):
            sanitized[key] = "***REDACTED***"
        elif isinstance(value, str) and len(value) > 200:
            sanitized[key] = f"{value[:100]}...({len(value)} chars)"
        else:
            sanitized[key] = value
    
    return sanitized


def _format_error_details(error: Exception) -> str:
    """
    예외를 사용자 친화적인 오류 메시지로 포맷팅합니다.
    
    Args:
        error: 예외 객체
    
    Returns:
        str: 포맷된 오류 메시지
    
    요구사항: 5.5
    """
    error_type = type(error).__name__
    error_msg = str(error)
    
    # 일반적인 오류 유형에 대한 사용자 친화적 메시지
    error_messages = {
        "ConnectionError": "서버 연결에 실패했습니다. 네트워크 상태를 확인하세요.",
        "TimeoutError": "요청 시간이 초과되었습니다. 나중에 다시 시도하세요.",
        "AuthenticationError": "인증에 실패했습니다. 자격 증명을 확인하세요.",
        "PermissionError": "권한이 없습니다. 접근 권한을 확인하세요.",
        "ValueError": f"잘못된 값이 전달되었습니다: {error_msg}",
        "TypeError": f"잘못된 타입이 전달되었습니다: {error_msg}",
    }
    
    if error_type in error_messages:
        return error_messages[error_type]
    
    return f"{error_type}: {error_msg}"


def create_user_friendly_error_message(
    tool_name: str,
    server_name: str,
    error: Union[MCPToolError, Exception]
) -> str:
    """
    사용자에게 표시할 친화적인 오류 메시지를 생성합니다.
    
    이 함수는 MCP 도구 오류를 사용자가 이해하기 쉬운 메시지로 변환합니다.
    
    Args:
        tool_name: 도구 이름
        server_name: 서버 이름
        error: 발생한 오류
    
    Returns:
        str: 사용자 친화적인 오류 메시지
    
    요구사항: 5.5
    """
    if isinstance(error, MCPToolTimeoutError):
        return (
            f"'{tool_name}' 도구 실행이 시간 초과되었습니다. "
            f"서버({server_name})가 응답하지 않습니다. "
            "잠시 후 다시 시도해 주세요."
        )
    
    elif isinstance(error, MCPToolConnectionError):
        return (
            f"'{server_name}' 서버에 연결할 수 없습니다. "
            "서버 상태를 확인하거나 관리자에게 문의하세요."
        )
    
    elif isinstance(error, MCPToolValidationError):
        return (
            f"'{tool_name}' 도구에 잘못된 인자가 전달되었습니다. "
            f"입력 값을 확인해 주세요."
        )
    
    elif isinstance(error, MCPToolExecutionError):
        return (
            f"'{tool_name}' 도구 실행 중 오류가 발생했습니다: {error.message}"
        )
    
    elif isinstance(error, MCPToolError):
        return str(error)
    
    else:
        return (
            f"'{tool_name}' 도구 실행 중 예기치 않은 오류가 발생했습니다. "
            "관리자에게 문의하세요."
        )


class MCPToolWrapper(BaseTool):
    """
    MCP 도구를 LangChain 도구로 래핑하는 클래스
    
    MCP 서버에서 제공하는 도구를 LangChain 에이전트에서 사용할 수 있도록
    BaseTool 인터페이스로 래핑합니다. 오류 처리 및 로깅 기능을 포함합니다.
    
    Attributes:
        name: 도구 이름
        description: 도구 설명
        mcp_tool: 원본 MCP 도구 정보
        session: MCP 클라이언트 세션 (Any 타입으로 테스트 시 모의 객체 허용)
        server_name: MCP 서버 이름
        timeout_seconds: 도구 실행 시간 제한 (초)
    
    요구사항: 5.4, 5.5
    """
    
    name: str
    description: str
    mcp_tool: Dict[str, Any]
    session: Any  # Any 타입으로 변경하여 테스트 시 모의 객체 허용
    server_name: str
    timeout_seconds: float = 30.0
    
    class Config:
        """Pydantic 모델 구성"""
        arbitrary_types_allowed = True
    
    def _run(self, **kwargs) -> str:
        """
        동기 실행 메서드 (비동기 실행을 래핑)
        
        Args:
            **kwargs: 도구 인자
        
        Returns:
            str: 도구 실행 결과
        
        요구사항: 5.4
        """
        return asyncio.run(self._arun(**kwargs))
    
    async def _arun(self, **kwargs) -> str:
        """
        비동기 도구 실행 메서드
        
        MCP 도구를 실행하고 결과를 처리합니다.
        오류 발생 시 사용자 친화적인 메시지를 반환합니다.
        
        Args:
            **kwargs: 도구 인자
        
        Returns:
            str: 도구 실행 결과 또는 오류 메시지
        
        Raises:
            MCPToolExecutionError: 도구 실행 실패 시 (재시도 불가능한 오류)
        
        요구사항: 5.4, 5.5
        """
        # 래퍼 함수를 사용하여 도구 실행
        result = await execute_mcp_tool(
            session=self.session,
            tool_name=self.name,
            server_name=self.server_name,
            arguments=kwargs,
            timeout_seconds=self.timeout_seconds
        )
        
        # 결과 상태에 따른 처리
        if result.status == MCPToolResultStatus.SUCCESS:
            return result.result or ""
        
        # 오류 발생 시 사용자 친화적 메시지 생성
        error_message = self._create_error_response(result)
        
        # 오류 상태에 따라 예외 발생 또는 메시지 반환
        if result.status == MCPToolResultStatus.CONNECTION_ERROR:
            # 연결 오류는 예외로 발생시켜 에이전트가 재시도하지 않도록 함
            raise MCPToolConnectionError(
                tool_name=self.name,
                server_name=self.server_name,
                message=result.error_message or "연결 오류"
            )
        
        # 기타 오류는 메시지로 반환 (에이전트가 다른 방법을 시도할 수 있도록)
        return error_message
    
    def _create_error_response(self, result: MCPToolResult) -> str:
        """
        오류 결과에 대한 응답 메시지를 생성합니다.
        
        Args:
            result: MCP 도구 실행 결과
        
        Returns:
            str: 오류 응답 메시지
        
        요구사항: 5.5
        """
        status_messages = {
            MCPToolResultStatus.TIMEOUT: (
                f"도구 '{self.name}' 실행이 시간 초과되었습니다. "
                f"서버({self.server_name})가 응답하지 않습니다."
            ),
            MCPToolResultStatus.CONNECTION_ERROR: (
                f"서버 '{self.server_name}'에 연결할 수 없습니다. "
                "서버 상태를 확인해 주세요."
            ),
            MCPToolResultStatus.VALIDATION_ERROR: (
                f"도구 '{self.name}'에 잘못된 인자가 전달되었습니다. "
                f"오류: {result.error_message}"
            ),
            MCPToolResultStatus.ERROR: (
                f"도구 '{self.name}' 실행 중 오류가 발생했습니다: "
                f"{result.error_message}"
            ),
        }
        
        return status_messages.get(
            result.status,
            f"알 수 없는 오류가 발생했습니다: {result.error_message}"
        )


class MCPServerManager:
    """
    MCP 서버 관리자 클래스
    
    Grafana 및 CloudWatch MCP 서버의 수명 주기를 관리하고
    LangChain 에이전트에서 사용할 수 있는 도구를 제공합니다.
    
    주요 기능:
    - MCP 서버 초기화 및 연결
    - 서버별 도구 등록
    - 모든 서버에서 도구 집계
    - 서버 연결 상태 관리
    
    요구사항: 5.1, 5.2, 5.3
    """
    
    def __init__(
        self,
        grafana_config: Optional[GrafanaConfig] = None,
        cloudwatch_config: Optional[CloudWatchConfig] = None
    ):
        """
        MCPServerManager 초기화
        
        Args:
            grafana_config: Grafana MCP 서버 구성 (선택사항)
            cloudwatch_config: CloudWatch MCP 서버 구성 (선택사항)
        """
        self.grafana_config = grafana_config
        self.cloudwatch_config = cloudwatch_config
        
        # 서버 정보 저장
        self.servers: Dict[str, MCPServerInfo] = {}
        
        # 초기화 상태
        self._initialized = False
        
        logger.info("MCPServerManager 인스턴스 생성")
    
    async def initialize_servers(self) -> None:
        """
        모든 MCP 서버를 초기화하고 연결합니다.
        
        구성된 모든 MCP 서버(Grafana, CloudWatch)를 시작하고
        각 서버에서 사용 가능한 도구를 등록합니다.
        
        Raises:
            Exception: 서버 초기화 실패 시
        
        요구사항: 5.1, 5.2, 5.3
        """
        logger.info("MCP 서버 초기화 시작")
        
        try:
            # Grafana MCP 서버 시작
            if self.grafana_config:
                grafana_server = await self._start_grafana_mcp()
                if grafana_server:
                    self.servers['grafana'] = grafana_server
                    logger.info("Grafana MCP 서버 초기화 완료")
            else:
                logger.warning("Grafana 구성이 없어 서버를 시작하지 않습니다")
            
            # CloudWatch MCP 서버 시작
            if self.cloudwatch_config:
                cloudwatch_server = await self._start_cloudwatch_mcp()
                if cloudwatch_server:
                    self.servers['cloudwatch'] = cloudwatch_server
                    logger.info("CloudWatch MCP 서버 초기화 완료")
            else:
                logger.warning("CloudWatch 구성이 없어 서버를 시작하지 않습니다")
            
            self._initialized = True
            logger.info(f"MCP 서버 초기화 완료: {len(self.servers)}개 서버 활성화")
            
        except Exception as e:
            logger.error(f"MCP 서버 초기화 실패: {e}")
            raise
    
    async def _start_grafana_mcp(self) -> Optional[MCPServerInfo]:
        """
        Grafana MCP 서버를 초기화합니다.
        
        Grafana 구성을 사용하여 MCP 서버를 시작하고
        사용 가능한 도구를 등록합니다.
        
        Returns:
            Optional[MCPServerInfo]: 서버 정보 또는 None (실패 시)
        
        요구사항: 5.1
        """
        if not self.grafana_config:
            logger.warning("Grafana 구성이 없습니다")
            return None
        
        try:
            logger.info(f"Grafana MCP 서버 시작: {self.grafana_config.url}")
            
            # Grafana MCP 서버 파라미터 설정
            # 참고: 실제 Grafana MCP 서버 패키지에 따라 명령어가 다를 수 있음
            server_params = StdioServerParameters(
                command="npx",
                args=[
                    "-y",
                    "@modelcontextprotocol/server-grafana"
                ],
                env={
                    "GRAFANA_URL": self.grafana_config.url,
                    "GRAFANA_API_KEY": self.grafana_config.api_key
                }
            )
            
            # MCP 클라이언트 세션 생성
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    # 세션 초기화
                    await session.initialize()
                    
                    # 사용 가능한 도구 목록 가져오기
                    tools_response = await session.list_tools()
                    tools = tools_response.tools if hasattr(tools_response, 'tools') else []
                    
                    logger.info(f"Grafana MCP 서버에서 {len(tools)}개 도구 발견")
                    
                    server_info = MCPServerInfo(
                        name='grafana',
                        session=session,
                        tools=tools,
                        is_connected=True
                    )
                    
                    return server_info
                    
        except FileNotFoundError:
            logger.error("Grafana MCP 서버 실행 파일을 찾을 수 없습니다. npx가 설치되어 있는지 확인하세요.")
            return None
        except Exception as e:
            logger.error(f"Grafana MCP 서버 시작 실패: {e}")
            return None
    
    async def _start_cloudwatch_mcp(self) -> Optional[MCPServerInfo]:
        """
        CloudWatch MCP 서버를 초기화합니다.
        
        CloudWatch 구성을 사용하여 MCP 서버를 시작하고
        사용 가능한 도구를 등록합니다.
        
        Returns:
            Optional[MCPServerInfo]: 서버 정보 또는 None (실패 시)
        
        요구사항: 5.2
        """
        if not self.cloudwatch_config:
            logger.warning("CloudWatch 구성이 없습니다")
            return None
        
        try:
            logger.info(f"CloudWatch MCP 서버 시작: 리전 {self.cloudwatch_config.region}")
            
            # CloudWatch MCP 서버 파라미터 설정
            # 참고: 실제 CloudWatch MCP 서버 패키지에 따라 명령어가 다를 수 있음
            server_params = StdioServerParameters(
                command="npx",
                args=[
                    "-y",
                    "@modelcontextprotocol/server-aws-cloudwatch"
                ],
                env={
                    "AWS_ACCESS_KEY_ID": self.cloudwatch_config.aws_access_key_id,
                    "AWS_SECRET_ACCESS_KEY": self.cloudwatch_config.aws_secret_access_key,
                    "AWS_REGION": self.cloudwatch_config.region
                }
            )
            
            # MCP 클라이언트 세션 생성
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    # 세션 초기화
                    await session.initialize()
                    
                    # 사용 가능한 도구 목록 가져오기
                    tools_response = await session.list_tools()
                    tools = tools_response.tools if hasattr(tools_response, 'tools') else []
                    
                    logger.info(f"CloudWatch MCP 서버에서 {len(tools)}개 도구 발견")
                    
                    server_info = MCPServerInfo(
                        name='cloudwatch',
                        session=session,
                        tools=tools,
                        is_connected=True
                    )
                    
                    return server_info
                    
        except FileNotFoundError:
            logger.error("CloudWatch MCP 서버 실행 파일을 찾을 수 없습니다. npx가 설치되어 있는지 확인하세요.")
            return None
        except Exception as e:
            logger.error(f"CloudWatch MCP 서버 시작 실패: {e}")
            return None
    
    def get_all_tools(self, timeout_seconds: float = 30.0) -> List[BaseTool]:
        """
        모든 MCP 서버에서 도구를 집계하여 반환합니다.
        
        각 MCP 서버에서 제공하는 도구를 LangChain BaseTool 형식으로
        변환하여 반환합니다.
        
        Args:
            timeout_seconds: 각 도구의 실행 시간 제한 (초, 기본값: 30.0)
        
        Returns:
            List[BaseTool]: LangChain 호환 도구 목록
        
        요구사항: 5.3, 5.4
        """
        all_tools: List[BaseTool] = []
        
        for server_name, server_info in self.servers.items():
            if not server_info.is_connected:
                logger.warning(f"서버 '{server_name}'이 연결되지 않아 도구를 가져올 수 없습니다")
                continue
            
            for mcp_tool in server_info.tools:
                try:
                    # MCP 도구 정보 추출
                    tool_name = mcp_tool.name if hasattr(mcp_tool, 'name') else str(mcp_tool)
                    tool_description = mcp_tool.description if hasattr(mcp_tool, 'description') else f"{tool_name} 도구"
                    
                    # 도구 스키마 추출 (있는 경우)
                    input_schema = {}
                    if hasattr(mcp_tool, 'inputSchema'):
                        input_schema = mcp_tool.inputSchema
                    
                    # LangChain 도구로 래핑
                    if server_info.session:
                        wrapped_tool = MCPToolWrapper(
                            name=f"{server_name}_{tool_name}",
                            description=f"[{server_name.upper()}] {tool_description}",
                            mcp_tool={"name": tool_name, "schema": input_schema},
                            session=server_info.session,
                            server_name=server_name,
                            timeout_seconds=timeout_seconds
                        )
                        all_tools.append(wrapped_tool)
                        logger.debug(f"도구 등록: {server_name}_{tool_name}")
                    
                except Exception as e:
                    logger.error(f"도구 래핑 실패 ({server_name}): {e}")
                    continue
        
        logger.info(f"총 {len(all_tools)}개 도구 집계 완료")
        return all_tools
    
    def get_server_status(self) -> Dict[str, Dict[str, Any]]:
        """
        모든 MCP 서버의 상태를 반환합니다.
        
        Returns:
            Dict[str, Dict[str, Any]]: 서버별 상태 정보
        """
        status = {}
        
        for server_name, server_info in self.servers.items():
            status[server_name] = {
                "is_connected": server_info.is_connected,
                "tool_count": len(server_info.tools),
                "tools": [
                    mcp_tool.name if hasattr(mcp_tool, 'name') else str(mcp_tool)
                    for mcp_tool in server_info.tools
                ]
            }
        
        return status
    
    async def shutdown(self) -> None:
        """
        모든 MCP 서버 연결을 종료합니다.
        
        리소스 정리를 위해 애플리케이션 종료 시 호출해야 합니다.
        """
        logger.info("MCP 서버 종료 시작")
        
        for server_name, server_info in self.servers.items():
            try:
                if server_info.is_connected and server_info.session:
                    # 세션 종료 (필요한 경우)
                    server_info.is_connected = False
                    logger.info(f"서버 '{server_name}' 연결 종료")
            except Exception as e:
                logger.error(f"서버 '{server_name}' 종료 실패: {e}")
        
        self.servers.clear()
        self._initialized = False
        logger.info("MCP 서버 종료 완료")
    
    @property
    def is_initialized(self) -> bool:
        """
        서버 초기화 상태를 반환합니다.
        
        Returns:
            bool: 초기화 완료 여부
        """
        return self._initialized
    
    @property
    def connected_server_count(self) -> int:
        """
        연결된 서버 수를 반환합니다.
        
        Returns:
            int: 연결된 서버 수
        """
        return sum(1 for server in self.servers.values() if server.is_connected)
