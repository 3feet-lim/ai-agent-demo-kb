"""
LangChain 에이전트 빌더 - AWS Bedrock Claude Sonnet 4.5 통합

이 모듈은 LangChain을 사용하여 AWS Bedrock Claude Sonnet 4.5 모델과
MCP 도구를 통합하는 에이전트를 구성합니다.

주요 기능:
- BedrockChat 클라이언트 초기화
- MCP 도구와 대화 메모리를 사용하는 도구 호출 에이전트 생성
- Bedrock API 실패에 대한 오류 처리
- 대화 컨텍스트 관리

요구사항: 4.2, 4.3, 5.3
"""

import logging
from typing import List, Optional, Any, Dict, Union

from langchain_aws import ChatBedrock
from langchain_core.tools import BaseTool
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, BaseMessage
from langgraph.prebuilt import create_react_agent
from langgraph.graph.state import CompiledStateGraph

from config import BedrockConfig

# 로거 설정
logger = logging.getLogger(__name__)


# =============================================================================
# Bedrock API 관련 예외 클래스
# =============================================================================

class BedrockAPIError(Exception):
    """
    Bedrock API 오류 기본 예외 클래스
    
    AWS Bedrock API 호출 중 발생하는 모든 오류의 기본 클래스입니다.
    
    Attributes:
        message: 오류 메시지
        original_error: 원본 예외 (있는 경우)
        error_code: AWS 오류 코드 (있는 경우)
    
    요구사항: 4.2
    """
    
    def __init__(
        self,
        message: str,
        original_error: Optional[Exception] = None,
        error_code: Optional[str] = None
    ):
        self.message = message
        self.original_error = original_error
        self.error_code = error_code
        super().__init__(self._format_message())
    
    def _format_message(self) -> str:
        """오류 메시지 포맷팅"""
        base_msg = f"Bedrock API 오류: {self.message}"
        if self.error_code:
            base_msg = f"[{self.error_code}] {base_msg}"
        if self.original_error:
            base_msg += f" (원인: {type(self.original_error).__name__}: {str(self.original_error)})"
        return base_msg


class BedrockConnectionError(BedrockAPIError):
    """
    Bedrock 연결 오류
    
    AWS Bedrock 서비스에 연결할 수 없는 경우 발생합니다.
    
    요구사항: 4.2
    """
    pass


class BedrockAuthenticationError(BedrockAPIError):
    """
    Bedrock 인증 오류
    
    AWS 자격 증명이 유효하지 않거나 권한이 없는 경우 발생합니다.
    
    요구사항: 4.2
    """
    pass


class BedrockRateLimitError(BedrockAPIError):
    """
    Bedrock 속도 제한 오류
    
    API 호출 속도 제한에 도달한 경우 발생합니다.
    
    Attributes:
        retry_after_seconds: 재시도까지 대기 시간 (초)
    
    요구사항: 4.2
    """
    
    def __init__(
        self,
        message: str,
        retry_after_seconds: Optional[float] = None,
        original_error: Optional[Exception] = None
    ):
        self.retry_after_seconds = retry_after_seconds
        super().__init__(message, original_error, error_code="ThrottlingException")


class BedrockModelError(BedrockAPIError):
    """
    Bedrock 모델 오류
    
    모델 호출 중 발생하는 오류 (토큰 제한 초과, 잘못된 입력 등)
    
    요구사항: 4.2
    """
    pass


# =============================================================================
# 시스템 프롬프트 정의
# =============================================================================

# 인프라 모니터링 챗봇을 위한 시스템 프롬프트
SYSTEM_PROMPT = """당신은 인프라 모니터링 및 분석을 위한 AI 어시스턴트입니다.

당신의 역할:
1. 사용자의 인프라 관련 질문에 답변합니다.
2. Grafana 및 CloudWatch에서 메트릭, 로그, 알람 데이터를 가져옵니다.
3. 가져온 데이터를 분석하고 인사이트를 제공합니다.
4. 시스템 상태 및 잠재적 문제에 대해 요약합니다.

사용 가능한 도구:
- Grafana 도구: 대시보드, 메트릭, 알림 조회
- CloudWatch 도구: 로그, 메트릭, 알람 조회

응답 지침:
- 항상 한국어로 응답하세요.
- 데이터를 가져올 때는 적절한 도구를 사용하세요.
- 분석 결과는 명확하고 구조화된 형식으로 제공하세요.
- 문제가 발견되면 가능한 원인과 해결 방안을 제안하세요.
- 불확실한 정보는 명확히 표시하세요.

주의사항:
- 민감한 정보(비밀번호, API 키 등)는 절대 노출하지 마세요.
- 도구 호출 실패 시 사용자에게 명확히 알리세요.
- 데이터가 없거나 접근할 수 없는 경우 정직하게 알리세요."""


# =============================================================================
# LLMChainBuilder 클래스
# =============================================================================

class LLMChainBuilder:
    """
    LangChain 에이전트 빌더 클래스
    
    AWS Bedrock Claude Sonnet 4.5 모델을 사용하여 MCP 도구와 통합된
    LangChain 에이전트를 구성합니다.
    
    주요 기능:
    - BedrockChat 클라이언트 초기화
    - 도구 호출 에이전트 생성 (langgraph 사용)
    - 대화 메모리 구성
    - Bedrock API 오류 처리
    
    Attributes:
        config: Bedrock 구성 정보
        llm: BedrockChat 클라이언트 인스턴스
        system_prompt: 시스템 프롬프트
    
    요구사항: 4.2, 4.3, 5.3
    """
    
    def __init__(self, config: BedrockConfig, system_prompt: Optional[str] = None):
        """
        LLMChainBuilder 초기화
        
        BedrockConfig를 사용하여 AWS Bedrock 클라이언트를 초기화합니다.
        
        Args:
            config: Bedrock 구성 정보 (리전, 모델 ID, 자격 증명 등)
            system_prompt: 커스텀 시스템 프롬프트 (선택사항, 기본값 사용)
        
        Raises:
            BedrockConnectionError: Bedrock 서비스 연결 실패 시
            BedrockAuthenticationError: AWS 자격 증명 오류 시
        
        요구사항: 4.2
        """
        self.config = config
        self.system_prompt = system_prompt or SYSTEM_PROMPT
        self.llm: Optional[ChatBedrock] = None
        
        logger.info(
            f"LLMChainBuilder 초기화: region={config.region}, "
            f"model_id={config.model_id}"
        )
        
        # BedrockChat 클라이언트 초기화
        self._initialize_llm()
    
    def _initialize_llm(self) -> None:
        """
        BedrockChat 클라이언트를 초기화합니다.
        
        AWS 자격 증명과 모델 파라미터를 사용하여 ChatBedrock 인스턴스를 생성합니다.
        
        Raises:
            BedrockConnectionError: Bedrock 서비스 연결 실패 시
            BedrockAuthenticationError: AWS 자격 증명 오류 시
        
        요구사항: 4.2
        """
        try:
            logger.info("BedrockChat 클라이언트 초기화 시작")
            
            # ChatBedrock 인스턴스 생성
            # langchain-aws 패키지의 ChatBedrock 클래스 사용
            self.llm = ChatBedrock(
                model_id=self.config.model_id,
                region_name=self.config.region,
                credentials_profile_name=None,  # 환경 변수에서 자격 증명 사용
                model_kwargs={
                    "temperature": self.config.temperature,
                    "max_tokens": self.config.max_tokens,
                },
                # AWS 자격 증명 직접 전달
                aws_access_key_id=self.config.aws_access_key_id,
                aws_secret_access_key=self.config.aws_secret_access_key,
            )
            
            logger.info(
                f"BedrockChat 클라이언트 초기화 완료: "
                f"model={self.config.model_id}, "
                f"temperature={self.config.temperature}, "
                f"max_tokens={self.config.max_tokens}"
            )
            
        except Exception as e:
            error_msg = str(e).lower()
            
            # 인증 관련 오류 처리
            if any(keyword in error_msg for keyword in [
                'credential', 'authentication', 'access denied', 
                'unauthorized', 'invalid security token'
            ]):
                logger.error(f"Bedrock 인증 오류: {e}")
                raise BedrockAuthenticationError(
                    message="AWS 자격 증명이 유효하지 않거나 Bedrock 접근 권한이 없습니다.",
                    original_error=e
                )
            
            # 연결 관련 오류 처리
            if any(keyword in error_msg for keyword in [
                'connection', 'timeout', 'endpoint', 'network',
                'could not connect', 'unreachable'
            ]):
                logger.error(f"Bedrock 연결 오류: {e}")
                raise BedrockConnectionError(
                    message="AWS Bedrock 서비스에 연결할 수 없습니다. 네트워크 및 리전 설정을 확인하세요.",
                    original_error=e
                )
            
            # 기타 오류
            logger.error(f"BedrockChat 클라이언트 초기화 실패: {e}")
            raise BedrockAPIError(
                message=f"BedrockChat 클라이언트 초기화 실패: {str(e)}",
                original_error=e
            )

    def build_chain(
        self,
        mcp_tools: List[BaseTool],
        chat_history: Optional[List[BaseMessage]] = None,
        verbose: bool = False,
        max_iterations: int = 10
    ) -> CompiledStateGraph:
        """
        MCP 도구와 대화 메모리로 LangChain 에이전트를 구성합니다.
        
        langgraph의 create_react_agent를 사용하여 도구 호출 에이전트를 생성합니다.
        
        Args:
            mcp_tools: MCP 서버에서 가져온 LangChain 호환 도구 목록
            chat_history: 이전 대화 기록 (BaseMessage 목록, 선택사항)
            verbose: 상세 로깅 활성화 여부 (기본값: False)
            max_iterations: 최대 에이전트 반복 횟수 (기본값: 10)
        
        Returns:
            CompiledStateGraph: 구성된 langgraph 에이전트
        
        Raises:
            BedrockAPIError: 에이전트 생성 실패 시
            ValueError: LLM이 초기화되지 않은 경우
        
        요구사항: 4.3, 5.3
        """
        if self.llm is None:
            raise ValueError("LLM이 초기화되지 않았습니다. _initialize_llm()을 먼저 호출하세요.")
        
        logger.info(
            f"에이전트 빌드 시작: tools={len(mcp_tools)}, "
            f"max_iterations={max_iterations}"
        )
        
        try:
            # langgraph의 create_react_agent를 사용하여 에이전트 생성
            # 시스템 프롬프트를 state_modifier로 전달
            agent = create_react_agent(
                model=self.llm,
                tools=mcp_tools,
                state_modifier=self.system_prompt
            )
            
            logger.info(
                f"에이전트 빌드 완료: "
                f"tools={[tool.name for tool in mcp_tools]}"
            )
            
            return agent
            
        except Exception as e:
            error_msg = str(e).lower()
            
            # 속도 제한 오류 처리
            if any(keyword in error_msg for keyword in [
                'throttl', 'rate limit', 'too many requests'
            ]):
                logger.error(f"Bedrock 속도 제한 오류: {e}")
                raise BedrockRateLimitError(
                    message="API 호출 속도 제한에 도달했습니다. 잠시 후 다시 시도하세요.",
                    original_error=e
                )
            
            # 모델 관련 오류 처리
            if any(keyword in error_msg for keyword in [
                'model', 'token', 'context length', 'input too long'
            ]):
                logger.error(f"Bedrock 모델 오류: {e}")
                raise BedrockModelError(
                    message=f"모델 호출 오류: {str(e)}",
                    original_error=e
                )
            
            # 기타 오류
            logger.error(f"에이전트 빌드 실패: {e}")
            raise BedrockAPIError(
                message=f"에이전트 빌드 실패: {str(e)}",
                original_error=e
            )
    
    def build_chain_with_history(
        self,
        mcp_tools: List[BaseTool],
        chat_history: List[Dict[str, str]],
        verbose: bool = False,
        max_iterations: int = 10
    ) -> CompiledStateGraph:
        """
        기존 대화 기록을 포함하여 에이전트를 구성합니다.
        
        이전 대화 기록을 BaseMessage 형식으로 변환한 후 에이전트를 생성합니다.
        세션 복원 시 유용합니다.
        
        Args:
            mcp_tools: MCP 서버에서 가져온 LangChain 호환 도구 목록
            chat_history: 이전 대화 기록 목록
                [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]
            verbose: 상세 로깅 활성화 여부 (기본값: False)
            max_iterations: 최대 에이전트 반복 횟수 (기본값: 10)
        
        Returns:
            CompiledStateGraph: 대화 기록이 포함된 에이전트
        
        요구사항: 4.3
        """
        logger.info(f"대화 기록 포함 에이전트 빌드: history_length={len(chat_history)}")
        
        # 대화 기록을 BaseMessage 형식으로 변환
        messages = self._convert_chat_history(chat_history)
        
        logger.debug(f"대화 기록 {len(chat_history)}개 메시지 변환 완료")
        
        # 에이전트 빌드
        return self.build_chain(
            mcp_tools=mcp_tools,
            chat_history=messages,
            verbose=verbose,
            max_iterations=max_iterations
        )
    
    def _convert_chat_history(
        self,
        chat_history: List[Dict[str, str]]
    ) -> List[BaseMessage]:
        """
        딕셔너리 형식의 대화 기록을 BaseMessage 목록으로 변환합니다.
        
        Args:
            chat_history: 딕셔너리 형식의 대화 기록
                [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]
        
        Returns:
            List[BaseMessage]: 변환된 메시지 목록
        """
        messages: List[BaseMessage] = []
        
        for message in chat_history:
            role = message.get("role", "")
            content = message.get("content", "")
            
            if role == "user":
                messages.append(HumanMessage(content=content))
            elif role == "assistant":
                messages.append(AIMessage(content=content))
            elif role == "system":
                messages.append(SystemMessage(content=content))
        
        return messages
    
    async def invoke_agent(
        self,
        agent: CompiledStateGraph,
        user_input: str,
        chat_history: Optional[List[BaseMessage]] = None
    ) -> Dict[str, Any]:
        """
        에이전트를 호출하여 사용자 입력을 처리합니다.
        
        에이전트를 실행하고 결과를 반환합니다. Bedrock API 오류를
        적절히 처리합니다.
        
        Args:
            agent: 구성된 langgraph 에이전트
            user_input: 사용자 입력 메시지
            chat_history: 이전 대화 기록 (선택사항)
        
        Returns:
            Dict[str, Any]: 에이전트 실행 결과
                - messages: 대화 메시지 목록
                - output: 최종 응답 텍스트
        
        Raises:
            BedrockAPIError: API 호출 실패 시
            BedrockRateLimitError: 속도 제한 도달 시
        
        요구사항: 4.3
        """
        logger.info(f"에이전트 호출: input_length={len(user_input)}")
        
        try:
            # 입력 메시지 구성
            messages = chat_history or []
            messages.append(HumanMessage(content=user_input))
            
            # 에이전트 실행
            result = await agent.ainvoke({"messages": messages})
            
            # 결과에서 출력 추출
            output = ""
            if "messages" in result and result["messages"]:
                last_message = result["messages"][-1]
                if hasattr(last_message, "content"):
                    output = last_message.content
            
            logger.info(
                f"에이전트 호출 완료: "
                f"output_length={len(output)}, "
                f"messages={len(result.get('messages', []))}"
            )
            
            return {
                "messages": result.get("messages", []),
                "output": output
            }
            
        except Exception as e:
            error_msg = str(e).lower()
            
            # 속도 제한 오류
            if any(keyword in error_msg for keyword in [
                'throttl', 'rate limit', 'too many requests'
            ]):
                logger.error(f"Bedrock 속도 제한: {e}")
                raise BedrockRateLimitError(
                    message="API 호출 속도 제한에 도달했습니다.",
                    original_error=e
                )
            
            # 인증 오류
            if any(keyword in error_msg for keyword in [
                'credential', 'authentication', 'access denied'
            ]):
                logger.error(f"Bedrock 인증 오류: {e}")
                raise BedrockAuthenticationError(
                    message="AWS 자격 증명 오류가 발생했습니다.",
                    original_error=e
                )
            
            # 연결 오류
            if any(keyword in error_msg for keyword in [
                'connection', 'timeout', 'network'
            ]):
                logger.error(f"Bedrock 연결 오류: {e}")
                raise BedrockConnectionError(
                    message="Bedrock 서비스 연결 오류가 발생했습니다.",
                    original_error=e
                )
            
            # 모델 오류
            if any(keyword in error_msg for keyword in [
                'model', 'token', 'context'
            ]):
                logger.error(f"Bedrock 모델 오류: {e}")
                raise BedrockModelError(
                    message=f"모델 처리 오류: {str(e)}",
                    original_error=e
                )
            
            # 기타 오류
            logger.error(f"에이전트 호출 실패: {e}")
            raise BedrockAPIError(
                message=f"에이전트 호출 실패: {str(e)}",
                original_error=e
            )
    
    def get_llm_info(self) -> Dict[str, Any]:
        """
        LLM 구성 정보를 반환합니다.
        
        Returns:
            Dict[str, Any]: LLM 구성 정보
        """
        return {
            "model_id": self.config.model_id,
            "region": self.config.region,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
            "is_initialized": self.llm is not None
        }


# =============================================================================
# 편의 함수
# =============================================================================

def create_agent_executor(
    config: BedrockConfig,
    mcp_tools: List[BaseTool],
    chat_history: Optional[List[Dict[str, str]]] = None,
    system_prompt: Optional[str] = None,
    verbose: bool = False
) -> CompiledStateGraph:
    """
    에이전트 실행자를 생성하는 편의 함수
    
    LLMChainBuilder를 사용하여 에이전트를 생성하고 반환합니다.
    
    Args:
        config: Bedrock 구성 정보
        mcp_tools: MCP 도구 목록
        chat_history: 이전 대화 기록 (선택사항)
        system_prompt: 커스텀 시스템 프롬프트 (선택사항)
        verbose: 상세 로깅 활성화 여부
    
    Returns:
        CompiledStateGraph: 구성된 langgraph 에이전트
    
    Raises:
        BedrockAPIError: 에이전트 생성 실패 시
    
    Example:
        >>> from config import BedrockConfig
        >>> config = BedrockConfig(
        ...     aws_access_key_id="...",
        ...     aws_secret_access_key="...",
        ...     region="us-east-1"
        ... )
        >>> agent = create_agent_executor(config, mcp_tools)
        >>> result = await agent.ainvoke({"messages": [HumanMessage(content="CPU 사용률을 확인해주세요")]})
    
    요구사항: 4.2, 4.3, 5.3
    """
    builder = LLMChainBuilder(config, system_prompt)
    
    if chat_history:
        return builder.build_chain_with_history(
            mcp_tools=mcp_tools,
            chat_history=chat_history,
            verbose=verbose
        )
    else:
        return builder.build_chain(
            mcp_tools=mcp_tools,
            verbose=verbose
        )


def format_agent_response(result: Dict[str, Any]) -> str:
    """
    에이전트 응답을 포맷팅합니다.
    
    에이전트 실행 결과에서 출력 텍스트를 추출하고 포맷팅합니다.
    
    Args:
        result: 에이전트 실행 결과
    
    Returns:
        str: 포맷된 응답 텍스트
    """
    # output 키가 있으면 직접 반환
    output = result.get("output", "")
    
    if output:
        return output.strip()
    
    # messages에서 마지막 AI 메시지 추출
    messages = result.get("messages", [])
    if messages:
        for message in reversed(messages):
            if isinstance(message, AIMessage):
                return message.content.strip()
            elif hasattr(message, "content") and hasattr(message, "type"):
                if message.type == "ai":
                    return message.content.strip()
    
    return "응답을 생성할 수 없습니다."
