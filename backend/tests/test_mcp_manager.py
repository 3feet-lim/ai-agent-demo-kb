"""
MCP 서버 관리자 단위 테스트

이 모듈은 MCPServerManager 클래스의 단위 테스트를 포함합니다.

테스트 항목:
- 유효한 구성으로 서버 초기화 테스트
- 잘못된 자격 증명으로 서버 초기화 테스트
- 여러 서버에서 도구 집계 테스트
- MCP 도구 실행 래퍼 테스트
- 도구 호출 오류 처리 테스트
- 도구 호출 로깅 테스트

요구사항: 5.3, 5.4, 5.5
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import List, Any

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp_manager import (
    MCPServerManager, 
    MCPServerInfo, 
    MCPToolWrapper,
    MCPToolResult,
    MCPToolResultStatus,
    MCPToolError,
    MCPToolExecutionError,
    MCPToolTimeoutError,
    MCPToolConnectionError,
    MCPToolValidationError,
    execute_mcp_tool,
    _process_mcp_result,
    _sanitize_arguments_for_logging,
    _format_error_details,
    create_user_friendly_error_message,
)
from config import GrafanaConfig, CloudWatchConfig


# =============================================================================
# 테스트 픽스처
# =============================================================================

@pytest.fixture
def valid_grafana_config():
    """유효한 Grafana 구성 픽스처"""
    return GrafanaConfig(
        url="https://grafana.example.com",
        api_key="test-api-key-12345678901234567890"
    )


@pytest.fixture
def valid_cloudwatch_config():
    """유효한 CloudWatch 구성 픽스처"""
    return CloudWatchConfig(
        aws_access_key_id="AKIAIOSFODNN7EXAMPLE",
        aws_secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        region="us-east-1"
    )


@pytest.fixture
def mock_mcp_tool():
    """모의 MCP 도구 픽스처"""
    tool = Mock()
    tool.name = "test_tool"
    tool.description = "테스트 도구 설명"
    tool.inputSchema = {"type": "object", "properties": {}}
    return tool


@pytest.fixture
def mock_mcp_session():
    """모의 MCP 세션 픽스처"""
    session = AsyncMock()
    session.initialize = AsyncMock()
    session.list_tools = AsyncMock()
    session.call_tool = AsyncMock()
    return session


# =============================================================================
# MCPServerManager 초기화 테스트
# =============================================================================

class TestMCPServerManagerInit:
    """MCPServerManager 초기화 테스트 클래스"""
    
    def test_init_without_config(self):
        """구성 없이 초기화 테스트"""
        manager = MCPServerManager()
        
        assert manager.grafana_config is None
        assert manager.cloudwatch_config is None
        assert manager.servers == {}
        assert manager._initialized is False
    
    def test_init_with_grafana_config(self, valid_grafana_config):
        """Grafana 구성으로 초기화 테스트"""
        manager = MCPServerManager(grafana_config=valid_grafana_config)
        
        assert manager.grafana_config == valid_grafana_config
        assert manager.cloudwatch_config is None
        assert manager._initialized is False
    
    def test_init_with_cloudwatch_config(self, valid_cloudwatch_config):
        """CloudWatch 구성으로 초기화 테스트"""
        manager = MCPServerManager(cloudwatch_config=valid_cloudwatch_config)
        
        assert manager.grafana_config is None
        assert manager.cloudwatch_config == valid_cloudwatch_config
        assert manager._initialized is False
    
    def test_init_with_both_configs(self, valid_grafana_config, valid_cloudwatch_config):
        """양쪽 구성으로 초기화 테스트"""
        manager = MCPServerManager(
            grafana_config=valid_grafana_config,
            cloudwatch_config=valid_cloudwatch_config
        )
        
        assert manager.grafana_config == valid_grafana_config
        assert manager.cloudwatch_config == valid_cloudwatch_config
        assert manager._initialized is False


# =============================================================================
# MCPServerInfo 테스트
# =============================================================================

class TestMCPServerInfo:
    """MCPServerInfo 데이터 클래스 테스트"""
    
    def test_default_values(self):
        """기본값 테스트"""
        info = MCPServerInfo(name="test")
        
        assert info.name == "test"
        assert info.session is None
        assert info.tools == []
        assert info.is_connected is False
    
    def test_with_all_values(self, mock_mcp_session, mock_mcp_tool):
        """모든 값 설정 테스트"""
        info = MCPServerInfo(
            name="grafana",
            session=mock_mcp_session,
            tools=[mock_mcp_tool],
            is_connected=True
        )
        
        assert info.name == "grafana"
        assert info.session == mock_mcp_session
        assert len(info.tools) == 1
        assert info.is_connected is True


# =============================================================================
# get_all_tools 테스트
# =============================================================================

class TestGetAllTools:
    """get_all_tools 메서드 테스트 클래스"""
    
    def test_get_all_tools_empty_servers(self):
        """서버가 없을 때 빈 목록 반환 테스트"""
        manager = MCPServerManager()
        
        tools = manager.get_all_tools()
        
        assert tools == []
    
    def test_get_all_tools_disconnected_server(self, mock_mcp_tool):
        """연결되지 않은 서버에서 도구 가져오기 테스트"""
        manager = MCPServerManager()
        manager.servers['test'] = MCPServerInfo(
            name='test',
            tools=[mock_mcp_tool],
            is_connected=False
        )
        
        tools = manager.get_all_tools()
        
        assert tools == []
    
    def test_get_all_tools_connected_server(self, mock_mcp_session, mock_mcp_tool):
        """연결된 서버에서 도구 가져오기 테스트"""
        manager = MCPServerManager()
        manager.servers['grafana'] = MCPServerInfo(
            name='grafana',
            session=mock_mcp_session,
            tools=[mock_mcp_tool],
            is_connected=True
        )
        
        tools = manager.get_all_tools()
        
        assert len(tools) == 1
        assert tools[0].name == "grafana_test_tool"
        assert "[GRAFANA]" in tools[0].description
    
    def test_get_all_tools_multiple_servers(self, mock_mcp_session, mock_mcp_tool):
        """여러 서버에서 도구 집계 테스트"""
        manager = MCPServerManager()
        
        # Grafana 서버 추가
        grafana_tool = Mock()
        grafana_tool.name = "query_metrics"
        grafana_tool.description = "메트릭 쿼리"
        
        manager.servers['grafana'] = MCPServerInfo(
            name='grafana',
            session=mock_mcp_session,
            tools=[grafana_tool],
            is_connected=True
        )
        
        # CloudWatch 서버 추가
        cloudwatch_tool = Mock()
        cloudwatch_tool.name = "get_logs"
        cloudwatch_tool.description = "로그 가져오기"
        
        manager.servers['cloudwatch'] = MCPServerInfo(
            name='cloudwatch',
            session=mock_mcp_session,
            tools=[cloudwatch_tool],
            is_connected=True
        )
        
        tools = manager.get_all_tools()
        
        assert len(tools) == 2
        tool_names = [t.name for t in tools]
        assert "grafana_query_metrics" in tool_names
        assert "cloudwatch_get_logs" in tool_names
    
    def test_get_all_tools_multiple_tools_per_server(self, mock_mcp_session):
        """서버당 여러 도구 테스트"""
        manager = MCPServerManager()
        
        tools_list = []
        for i in range(3):
            tool = Mock()
            tool.name = f"tool_{i}"
            tool.description = f"도구 {i} 설명"
            tools_list.append(tool)
        
        manager.servers['grafana'] = MCPServerInfo(
            name='grafana',
            session=mock_mcp_session,
            tools=tools_list,
            is_connected=True
        )
        
        tools = manager.get_all_tools()
        
        assert len(tools) == 3


# =============================================================================
# get_server_status 테스트
# =============================================================================

class TestGetServerStatus:
    """get_server_status 메서드 테스트 클래스"""
    
    def test_empty_status(self):
        """서버가 없을 때 상태 테스트"""
        manager = MCPServerManager()
        
        status = manager.get_server_status()
        
        assert status == {}
    
    def test_single_server_status(self, mock_mcp_session, mock_mcp_tool):
        """단일 서버 상태 테스트"""
        manager = MCPServerManager()
        manager.servers['grafana'] = MCPServerInfo(
            name='grafana',
            session=mock_mcp_session,
            tools=[mock_mcp_tool],
            is_connected=True
        )
        
        status = manager.get_server_status()
        
        assert 'grafana' in status
        assert status['grafana']['is_connected'] is True
        assert status['grafana']['tool_count'] == 1
        assert 'test_tool' in status['grafana']['tools']
    
    def test_multiple_servers_status(self, mock_mcp_session, mock_mcp_tool):
        """여러 서버 상태 테스트"""
        manager = MCPServerManager()
        
        manager.servers['grafana'] = MCPServerInfo(
            name='grafana',
            session=mock_mcp_session,
            tools=[mock_mcp_tool],
            is_connected=True
        )
        
        manager.servers['cloudwatch'] = MCPServerInfo(
            name='cloudwatch',
            session=mock_mcp_session,
            tools=[],
            is_connected=False
        )
        
        status = manager.get_server_status()
        
        assert len(status) == 2
        assert status['grafana']['is_connected'] is True
        assert status['cloudwatch']['is_connected'] is False


# =============================================================================
# 속성 테스트
# =============================================================================

class TestMCPServerManagerProperties:
    """MCPServerManager 속성 테스트 클래스"""
    
    def test_is_initialized_default(self):
        """is_initialized 기본값 테스트"""
        manager = MCPServerManager()
        
        assert manager.is_initialized is False
    
    def test_connected_server_count_empty(self):
        """connected_server_count 빈 상태 테스트"""
        manager = MCPServerManager()
        
        assert manager.connected_server_count == 0
    
    def test_connected_server_count_with_servers(self, mock_mcp_session):
        """connected_server_count 서버 있을 때 테스트"""
        manager = MCPServerManager()
        
        manager.servers['grafana'] = MCPServerInfo(
            name='grafana',
            session=mock_mcp_session,
            is_connected=True
        )
        
        manager.servers['cloudwatch'] = MCPServerInfo(
            name='cloudwatch',
            session=mock_mcp_session,
            is_connected=False
        )
        
        assert manager.connected_server_count == 1


# =============================================================================
# shutdown 테스트
# =============================================================================

class TestShutdown:
    """shutdown 메서드 테스트 클래스"""
    
    @pytest.mark.asyncio
    async def test_shutdown_empty_servers(self):
        """서버가 없을 때 종료 테스트"""
        manager = MCPServerManager()
        
        await manager.shutdown()
        
        assert manager.servers == {}
        assert manager._initialized is False
    
    @pytest.mark.asyncio
    async def test_shutdown_with_servers(self, mock_mcp_session):
        """서버가 있을 때 종료 테스트"""
        manager = MCPServerManager()
        manager._initialized = True
        
        manager.servers['grafana'] = MCPServerInfo(
            name='grafana',
            session=mock_mcp_session,
            is_connected=True
        )
        
        await manager.shutdown()
        
        assert manager.servers == {}
        assert manager._initialized is False


# =============================================================================
# MCPToolWrapper 테스트
# =============================================================================

class TestMCPToolWrapper:
    """MCPToolWrapper 클래스 테스트"""
    
    def test_tool_wrapper_creation(self, mock_mcp_session):
        """도구 래퍼 생성 테스트"""
        wrapper = MCPToolWrapper(
            name="test_tool",
            description="테스트 도구",
            mcp_tool={"name": "test", "schema": {}},
            session=mock_mcp_session,
            server_name="grafana"
        )
        
        assert wrapper.name == "test_tool"
        assert wrapper.description == "테스트 도구"
        assert wrapper.server_name == "grafana"
    
    def test_tool_wrapper_creation_with_timeout(self, mock_mcp_session):
        """시간 제한이 있는 도구 래퍼 생성 테스트"""
        wrapper = MCPToolWrapper(
            name="test_tool",
            description="테스트 도구",
            mcp_tool={"name": "test", "schema": {}},
            session=mock_mcp_session,
            server_name="grafana",
            timeout_seconds=60.0
        )
        
        assert wrapper.timeout_seconds == 60.0
    
    @pytest.mark.asyncio
    async def test_tool_wrapper_arun_success(self, mock_mcp_session):
        """도구 래퍼 비동기 실행 성공 테스트"""
        # 모의 결과 설정
        mock_result = Mock()
        mock_content = Mock()
        mock_content.text = "실행 결과"
        mock_result.content = [mock_content]
        mock_mcp_session.call_tool.return_value = mock_result
        
        wrapper = MCPToolWrapper(
            name="test_tool",
            description="테스트 도구",
            mcp_tool={"name": "test", "schema": {}},
            session=mock_mcp_session,
            server_name="grafana"
        )
        
        result = await wrapper._arun(param1="value1")
        
        assert result == "실행 결과"
        mock_mcp_session.call_tool.assert_called_once_with("test_tool", {"param1": "value1"})
    
    @pytest.mark.asyncio
    async def test_tool_wrapper_arun_error(self, mock_mcp_session):
        """도구 래퍼 비동기 실행 오류 테스트 - 오류 메시지 반환"""
        mock_mcp_session.call_tool.side_effect = Exception("도구 실행 오류")
        
        wrapper = MCPToolWrapper(
            name="test_tool",
            description="테스트 도구",
            mcp_tool={"name": "test", "schema": {}},
            session=mock_mcp_session,
            server_name="grafana"
        )
        
        # 일반 오류는 메시지로 반환됨
        result = await wrapper._arun(param1="value1")
        
        assert "오류" in result or "실패" in result
    
    @pytest.mark.asyncio
    async def test_tool_wrapper_arun_connection_error(self):
        """도구 래퍼 연결 오류 테스트 - 예외 발생"""
        wrapper = MCPToolWrapper(
            name="test_tool",
            description="테스트 도구",
            mcp_tool={"name": "test", "schema": {}},
            session=None,  # None 세션으로 연결 오류 유발
            server_name="grafana"
        )
        
        with pytest.raises(MCPToolConnectionError):
            await wrapper._arun(param1="value1")


# =============================================================================
# MCP 도구 실행 래퍼 함수 테스트
# =============================================================================

class TestExecuteMCPTool:
    """execute_mcp_tool 함수 테스트 클래스 (요구사항: 5.4, 5.5)"""
    
    @pytest.mark.asyncio
    async def test_execute_success(self, mock_mcp_session):
        """도구 실행 성공 테스트"""
        mock_result = Mock()
        mock_content = Mock()
        mock_content.text = "성공 결과"
        mock_result.content = [mock_content]
        mock_mcp_session.call_tool.return_value = mock_result
        
        result = await execute_mcp_tool(
            session=mock_mcp_session,
            tool_name="test_tool",
            server_name="grafana",
            arguments={"query": "test"}
        )
        
        assert result.status == MCPToolResultStatus.SUCCESS
        assert result.result == "성공 결과"
        assert result.tool_name == "test_tool"
        assert result.server_name == "grafana"
        # 실행 시간은 0 이상이어야 함 (모의 객체는 매우 빠르게 실행됨)
        assert result.execution_time_ms >= 0
    
    @pytest.mark.asyncio
    async def test_execute_with_none_session(self):
        """None 세션으로 실행 테스트"""
        result = await execute_mcp_tool(
            session=None,
            tool_name="test_tool",
            server_name="grafana",
            arguments={}
        )
        
        assert result.status == MCPToolResultStatus.CONNECTION_ERROR
        assert result.error_message is not None
    
    @pytest.mark.asyncio
    async def test_execute_timeout(self, mock_mcp_session):
        """도구 실행 시간 초과 테스트"""
        async def slow_call(*args, **kwargs):
            await asyncio.sleep(2)
            return Mock()
        
        mock_mcp_session.call_tool = slow_call
        
        result = await execute_mcp_tool(
            session=mock_mcp_session,
            tool_name="test_tool",
            server_name="grafana",
            arguments={},
            timeout_seconds=0.1
        )
        
        assert result.status == MCPToolResultStatus.TIMEOUT
        assert "시간 초과" in result.error_message
    
    @pytest.mark.asyncio
    async def test_execute_general_error(self, mock_mcp_session):
        """일반 오류 테스트"""
        mock_mcp_session.call_tool.side_effect = ValueError("잘못된 값")
        
        result = await execute_mcp_tool(
            session=mock_mcp_session,
            tool_name="test_tool",
            server_name="grafana",
            arguments={}
        )
        
        assert result.status == MCPToolResultStatus.ERROR
        assert result.error_message is not None


# =============================================================================
# 결과 처리 함수 테스트
# =============================================================================

class TestProcessMCPResult:
    """_process_mcp_result 함수 테스트 클래스 (요구사항: 5.4)"""
    
    def test_process_none_result(self):
        """None 결과 처리 테스트"""
        result = _process_mcp_result(None)
        assert result == ""
    
    def test_process_string_result(self):
        """문자열 결과 처리 테스트"""
        result = _process_mcp_result("테스트 결과")
        assert result == "테스트 결과"
    
    def test_process_content_with_text_list(self):
        """텍스트 리스트가 있는 content 처리 테스트"""
        mock_result = Mock()
        mock_content1 = Mock()
        mock_content1.text = "첫 번째"
        mock_content2 = Mock()
        mock_content2.text = "두 번째"
        mock_result.content = [mock_content1, mock_content2]
        
        result = _process_mcp_result(mock_result)
        assert "첫 번째" in result
        assert "두 번째" in result
    
    def test_process_content_with_single_text(self):
        """단일 텍스트가 있는 content 처리 테스트"""
        mock_result = Mock()
        mock_content = Mock()
        mock_content.text = "단일 결과"
        mock_result.content = mock_content
        
        result = _process_mcp_result(mock_result)
        assert result == "단일 결과"
    
    def test_process_dict_with_text(self):
        """text 키가 있는 딕셔너리 처리 테스트"""
        result = _process_mcp_result({"text": "딕셔너리 결과"})
        assert result == "딕셔너리 결과"
    
    def test_process_dict_with_result(self):
        """result 키가 있는 딕셔너리 처리 테스트"""
        result = _process_mcp_result({"result": "결과 값"})
        assert result == "결과 값"


# =============================================================================
# 인자 정제 함수 테스트
# =============================================================================

class TestSanitizeArguments:
    """_sanitize_arguments_for_logging 함수 테스트 클래스 (요구사항: 5.4)"""
    
    def test_sanitize_normal_args(self):
        """일반 인자 정제 테스트"""
        args = {"query": "test", "limit": 10}
        result = _sanitize_arguments_for_logging(args)
        
        assert result["query"] == "test"
        assert result["limit"] == 10
    
    def test_sanitize_sensitive_args(self):
        """민감한 인자 정제 테스트"""
        args = {
            "api_key": "secret123",
            "password": "mypassword",
            "token": "bearer_token"
        }
        result = _sanitize_arguments_for_logging(args)
        
        assert result["api_key"] == "***REDACTED***"
        assert result["password"] == "***REDACTED***"
        assert result["token"] == "***REDACTED***"
    
    def test_sanitize_long_string(self):
        """긴 문자열 정제 테스트"""
        long_string = "a" * 300
        args = {"data": long_string}
        result = _sanitize_arguments_for_logging(args)
        
        assert len(result["data"]) < len(long_string)
        assert "300 chars" in result["data"]


# =============================================================================
# 오류 포맷팅 함수 테스트
# =============================================================================

class TestFormatErrorDetails:
    """_format_error_details 함수 테스트 클래스 (요구사항: 5.5)"""
    
    def test_format_connection_error(self):
        """ConnectionError 포맷팅 테스트"""
        error = ConnectionError("연결 실패")
        result = _format_error_details(error)
        
        assert "연결" in result
    
    def test_format_timeout_error(self):
        """TimeoutError 포맷팅 테스트"""
        error = TimeoutError("시간 초과")
        result = _format_error_details(error)
        
        assert "시간" in result or "초과" in result
    
    def test_format_value_error(self):
        """ValueError 포맷팅 테스트"""
        error = ValueError("잘못된 값")
        result = _format_error_details(error)
        
        assert "잘못된 값" in result
    
    def test_format_unknown_error(self):
        """알 수 없는 오류 포맷팅 테스트"""
        error = RuntimeError("런타임 오류")
        result = _format_error_details(error)
        
        assert "RuntimeError" in result
        assert "런타임 오류" in result


# =============================================================================
# 사용자 친화적 오류 메시지 테스트
# =============================================================================

class TestCreateUserFriendlyErrorMessage:
    """create_user_friendly_error_message 함수 테스트 클래스 (요구사항: 5.5)"""
    
    def test_timeout_error_message(self):
        """시간 초과 오류 메시지 테스트"""
        error = MCPToolTimeoutError(
            tool_name="test_tool",
            server_name="grafana",
            timeout_seconds=30.0
        )
        
        message = create_user_friendly_error_message("test_tool", "grafana", error)
        
        assert "시간 초과" in message
        assert "test_tool" in message
    
    def test_connection_error_message(self):
        """연결 오류 메시지 테스트"""
        error = MCPToolConnectionError(
            tool_name="test_tool",
            server_name="grafana",
            message="연결 실패"
        )
        
        message = create_user_friendly_error_message("test_tool", "grafana", error)
        
        assert "연결" in message
        assert "grafana" in message
    
    def test_validation_error_message(self):
        """검증 오류 메시지 테스트"""
        error = MCPToolValidationError(
            tool_name="test_tool",
            server_name="grafana",
            message="잘못된 인자"
        )
        
        message = create_user_friendly_error_message("test_tool", "grafana", error)
        
        assert "잘못된 인자" in message
    
    def test_generic_error_message(self):
        """일반 오류 메시지 테스트"""
        error = Exception("알 수 없는 오류")
        
        message = create_user_friendly_error_message("test_tool", "grafana", error)
        
        assert "test_tool" in message


# =============================================================================
# MCP 도구 오류 클래스 테스트
# =============================================================================

class TestMCPToolErrors:
    """MCP 도구 오류 클래스 테스트 (요구사항: 5.5)"""
    
    def test_mcp_tool_error_creation(self):
        """MCPToolError 생성 테스트"""
        error = MCPToolError(
            tool_name="test_tool",
            server_name="grafana",
            message="테스트 오류"
        )
        
        assert error.tool_name == "test_tool"
        assert error.server_name == "grafana"
        assert "테스트 오류" in str(error)
    
    def test_mcp_tool_error_with_original(self):
        """원본 예외가 있는 MCPToolError 테스트"""
        original = ValueError("원본 오류")
        error = MCPToolError(
            tool_name="test_tool",
            server_name="grafana",
            message="래핑된 오류",
            original_error=original
        )
        
        assert error.original_error == original
        assert "ValueError" in str(error)
    
    def test_mcp_tool_timeout_error(self):
        """MCPToolTimeoutError 테스트"""
        error = MCPToolTimeoutError(
            tool_name="test_tool",
            server_name="grafana",
            timeout_seconds=30.0
        )
        
        assert error.timeout_seconds == 30.0
        assert "30" in str(error)
    
    def test_mcp_tool_connection_error(self):
        """MCPToolConnectionError 테스트"""
        error = MCPToolConnectionError(
            tool_name="test_tool",
            server_name="grafana",
            message="연결 끊김"
        )
        
        assert "연결 끊김" in str(error)
    
    def test_mcp_tool_validation_error(self):
        """MCPToolValidationError 테스트"""
        error = MCPToolValidationError(
            tool_name="test_tool",
            server_name="grafana",
            message="잘못된 인자",
            invalid_args={"param1": "invalid"}
        )
        
        assert error.invalid_args == {"param1": "invalid"}


# =============================================================================
# MCPToolResult 테스트
# =============================================================================

class TestMCPToolResult:
    """MCPToolResult 데이터 클래스 테스트 (요구사항: 5.4, 5.5)"""
    
    def test_success_result(self):
        """성공 결과 테스트"""
        result = MCPToolResult(
            tool_name="test_tool",
            server_name="grafana",
            status=MCPToolResultStatus.SUCCESS,
            result="성공 결과",
            execution_time_ms=100.5
        )
        
        assert result.status == MCPToolResultStatus.SUCCESS
        assert result.result == "성공 결과"
        assert result.error_message is None
    
    def test_error_result(self):
        """오류 결과 테스트"""
        result = MCPToolResult(
            tool_name="test_tool",
            server_name="grafana",
            status=MCPToolResultStatus.ERROR,
            error_message="오류 발생",
            execution_time_ms=50.0
        )
        
        assert result.status == MCPToolResultStatus.ERROR
        assert result.result is None
        assert result.error_message == "오류 발생"
    
    def test_result_with_arguments(self):
        """인자가 있는 결과 테스트"""
        result = MCPToolResult(
            tool_name="test_tool",
            server_name="grafana",
            status=MCPToolResultStatus.SUCCESS,
            arguments={"query": "test", "limit": 10}
        )
        
        assert result.arguments == {"query": "test", "limit": 10}


# =============================================================================
# 서버 초기화 테스트 (모의 객체 사용)
# =============================================================================

class TestServerInitialization:
    """서버 초기화 테스트 클래스 (모의 객체 사용)"""
    
    @pytest.mark.asyncio
    async def test_initialize_servers_no_config(self):
        """구성 없이 서버 초기화 테스트"""
        manager = MCPServerManager()
        
        await manager.initialize_servers()
        
        assert manager._initialized is True
        assert len(manager.servers) == 0
    
    @pytest.mark.asyncio
    async def test_start_grafana_mcp_no_config(self):
        """Grafana 구성 없이 시작 테스트"""
        manager = MCPServerManager()
        
        result = await manager._start_grafana_mcp()
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_start_cloudwatch_mcp_no_config(self):
        """CloudWatch 구성 없이 시작 테스트"""
        manager = MCPServerManager()
        
        result = await manager._start_cloudwatch_mcp()
        
        assert result is None


# =============================================================================
# 통합 시나리오 테스트
# =============================================================================

class TestIntegrationScenarios:
    """통합 시나리오 테스트 클래스"""
    
    def test_full_workflow_mock(self, mock_mcp_session, valid_grafana_config, valid_cloudwatch_config):
        """전체 워크플로우 모의 테스트"""
        manager = MCPServerManager(
            grafana_config=valid_grafana_config,
            cloudwatch_config=valid_cloudwatch_config
        )
        
        # 수동으로 서버 정보 설정 (실제 MCP 서버 없이 테스트)
        grafana_tool = Mock()
        grafana_tool.name = "query_dashboard"
        grafana_tool.description = "대시보드 쿼리"
        
        cloudwatch_tool = Mock()
        cloudwatch_tool.name = "get_metrics"
        cloudwatch_tool.description = "메트릭 가져오기"
        
        manager.servers['grafana'] = MCPServerInfo(
            name='grafana',
            session=mock_mcp_session,
            tools=[grafana_tool],
            is_connected=True
        )
        
        manager.servers['cloudwatch'] = MCPServerInfo(
            name='cloudwatch',
            session=mock_mcp_session,
            tools=[cloudwatch_tool],
            is_connected=True
        )
        
        manager._initialized = True
        
        # 도구 집계 테스트
        tools = manager.get_all_tools()
        assert len(tools) == 2
        
        # 상태 확인 테스트
        status = manager.get_server_status()
        assert status['grafana']['is_connected'] is True
        assert status['cloudwatch']['is_connected'] is True
        
        # 속성 테스트
        assert manager.is_initialized is True
        assert manager.connected_server_count == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
