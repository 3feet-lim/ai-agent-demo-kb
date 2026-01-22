"""
LangChain 빌더 단위 테스트

이 모듈은 LLMChainBuilder 클래스의 단위 테스트를 포함합니다.

테스트 항목:
- 유효한 구성으로 에이전트 생성 테스트
- Bedrock 클라이언트 초기화 테스트
- 에이전트와 도구 등록 테스트
- build_chain 메서드 테스트
- build_chain_with_history 메서드 테스트
- _convert_chat_history 메서드 테스트
- 다양한 Bedrock API 오류 처리 테스트
- format_agent_response 함수 테스트
- get_llm_info 메서드 테스트

요구사항: 4.2, 4.3
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import List, Dict, Any

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from llm_chain import (
    LLMChainBuilder,
    BedrockAPIError,
    BedrockConnectionError,
    BedrockAuthenticationError,
    BedrockRateLimitError,
    BedrockModelError,
    create_agent_executor,
    format_agent_response,
    SYSTEM_PROMPT,
)
from config import BedrockConfig
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage


# =============================================================================
# 테스트 픽스처
# =============================================================================

@pytest.fixture
def valid_bedrock_config():
    """유효한 Bedrock 구성 픽스처"""
    return BedrockConfig(
        aws_access_key_id="AKIAIOSFODNN7EXAMPLE",
        aws_secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        region="us-east-1",
        model_id="anthropic.claude-sonnet-4-5",
        temperature=0.7,
        max_tokens=4096
    )


@pytest.fixture
def mock_chat_bedrock():
    """모의 ChatBedrock 클라이언트 픽스처"""
    mock = MagicMock()
    mock.model_id = "anthropic.claude-sonnet-4-5"
    return mock


@pytest.fixture
def mock_mcp_tool():
    """모의 MCP 도구 픽스처"""
    tool = Mock()
    tool.name = "test_tool"
    tool.description = "테스트 도구 설명"
    tool.args_schema = None
    return tool


@pytest.fixture
def mock_agent():
    """모의 에이전트 픽스처"""
    agent = AsyncMock()
    agent.ainvoke = AsyncMock(return_value={
        "messages": [
            HumanMessage(content="테스트 질문"),
            AIMessage(content="테스트 응답")
        ],
        "output": "테스트 응답"
    })
    return agent


@pytest.fixture
def sample_chat_history():
    """샘플 대화 기록 픽스처"""
    return [
        {"role": "user", "content": "안녕하세요"},
        {"role": "assistant", "content": "안녕하세요! 무엇을 도와드릴까요?"},
        {"role": "user", "content": "CPU 사용률을 확인해주세요"},
        {"role": "assistant", "content": "CPU 사용률을 확인하겠습니다."}
    ]


# =============================================================================
# BedrockAPIError 예외 클래스 테스트
# =============================================================================

class TestBedrockAPIError:
    """BedrockAPIError 예외 클래스 테스트"""
    
    def test_basic_error_creation(self):
        """기본 오류 생성 테스트"""
        error = BedrockAPIError(message="테스트 오류")
        
        assert "테스트 오류" in str(error)
        assert error.message == "테스트 오류"
        assert error.original_error is None
        assert error.error_code is None
    
    def test_error_with_original_exception(self):
        """원본 예외가 있는 오류 테스트"""
        original = ValueError("원본 오류")
        error = BedrockAPIError(
            message="래핑된 오류",
            original_error=original
        )
        
        assert error.original_error == original
        assert "ValueError" in str(error)
        assert "원본 오류" in str(error)
    
    def test_error_with_error_code(self):
        """오류 코드가 있는 오류 테스트"""
        error = BedrockAPIError(
            message="테스트 오류",
            error_code="TEST_ERROR"
        )
        
        assert error.error_code == "TEST_ERROR"
        assert "[TEST_ERROR]" in str(error)


class TestBedrockConnectionError:
    """BedrockConnectionError 예외 클래스 테스트"""
    
    def test_connection_error_creation(self):
        """연결 오류 생성 테스트"""
        error = BedrockConnectionError(message="연결 실패")
        
        assert isinstance(error, BedrockAPIError)
        assert "연결 실패" in str(error)


class TestBedrockAuthenticationError:
    """BedrockAuthenticationError 예외 클래스 테스트"""
    
    def test_authentication_error_creation(self):
        """인증 오류 생성 테스트"""
        error = BedrockAuthenticationError(message="인증 실패")
        
        assert isinstance(error, BedrockAPIError)
        assert "인증 실패" in str(error)


class TestBedrockRateLimitError:
    """BedrockRateLimitError 예외 클래스 테스트"""
    
    def test_rate_limit_error_creation(self):
        """속도 제한 오류 생성 테스트"""
        error = BedrockRateLimitError(
            message="속도 제한 초과",
            retry_after_seconds=30.0
        )
        
        assert isinstance(error, BedrockAPIError)
        assert error.retry_after_seconds == 30.0
        assert error.error_code == "ThrottlingException"
    
    def test_rate_limit_error_without_retry_time(self):
        """재시도 시간 없는 속도 제한 오류 테스트"""
        error = BedrockRateLimitError(message="속도 제한")
        
        assert error.retry_after_seconds is None


class TestBedrockModelError:
    """BedrockModelError 예외 클래스 테스트"""
    
    def test_model_error_creation(self):
        """모델 오류 생성 테스트"""
        error = BedrockModelError(message="토큰 제한 초과")
        
        assert isinstance(error, BedrockAPIError)
        assert "토큰 제한 초과" in str(error)


# =============================================================================
# LLMChainBuilder 초기화 테스트
# =============================================================================

class TestLLMChainBuilderInit:
    """LLMChainBuilder 초기화 테스트 클래스 (요구사항: 4.2)"""
    
    @patch('llm_chain.ChatBedrock')
    def test_init_with_valid_config(self, mock_chat_bedrock_class, valid_bedrock_config):
        """유효한 구성으로 초기화 테스트"""
        mock_chat_bedrock_class.return_value = MagicMock()
        
        builder = LLMChainBuilder(valid_bedrock_config)
        
        assert builder.config == valid_bedrock_config
        assert builder.system_prompt == SYSTEM_PROMPT
        assert builder.llm is not None
        
        # ChatBedrock이 올바른 파라미터로 호출되었는지 확인
        mock_chat_bedrock_class.assert_called_once()
        call_kwargs = mock_chat_bedrock_class.call_args[1]
        assert call_kwargs['model_id'] == valid_bedrock_config.model_id
        assert call_kwargs['region_name'] == valid_bedrock_config.region
    
    @patch('llm_chain.ChatBedrock')
    def test_init_with_custom_system_prompt(self, mock_chat_bedrock_class, valid_bedrock_config):
        """커스텀 시스템 프롬프트로 초기화 테스트"""
        mock_chat_bedrock_class.return_value = MagicMock()
        custom_prompt = "커스텀 시스템 프롬프트입니다."
        
        builder = LLMChainBuilder(valid_bedrock_config, system_prompt=custom_prompt)
        
        assert builder.system_prompt == custom_prompt
    
    @patch('llm_chain.ChatBedrock')
    def test_init_authentication_error(self, mock_chat_bedrock_class, valid_bedrock_config):
        """인증 오류로 초기화 실패 테스트"""
        mock_chat_bedrock_class.side_effect = Exception("Invalid security token")
        
        with pytest.raises(BedrockAuthenticationError) as exc_info:
            LLMChainBuilder(valid_bedrock_config)
        
        assert "자격 증명" in str(exc_info.value) or "권한" in str(exc_info.value)
    
    @patch('llm_chain.ChatBedrock')
    def test_init_connection_error(self, mock_chat_bedrock_class, valid_bedrock_config):
        """연결 오류로 초기화 실패 테스트"""
        mock_chat_bedrock_class.side_effect = Exception("Could not connect to endpoint")
        
        with pytest.raises(BedrockConnectionError) as exc_info:
            LLMChainBuilder(valid_bedrock_config)
        
        assert "연결" in str(exc_info.value)
    
    @patch('llm_chain.ChatBedrock')
    def test_init_generic_error(self, mock_chat_bedrock_class, valid_bedrock_config):
        """일반 오류로 초기화 실패 테스트"""
        mock_chat_bedrock_class.side_effect = Exception("Unknown error occurred")
        
        with pytest.raises(BedrockAPIError) as exc_info:
            LLMChainBuilder(valid_bedrock_config)
        
        assert "Unknown error" in str(exc_info.value)


# =============================================================================
# build_chain 메서드 테스트
# =============================================================================

class TestBuildChain:
    """build_chain 메서드 테스트 클래스 (요구사항: 4.3, 5.3)"""
    
    @patch('llm_chain.ChatBedrock')
    @patch('llm_chain.create_react_agent')
    def test_build_chain_with_tools(
        self, 
        mock_create_agent, 
        mock_chat_bedrock_class, 
        valid_bedrock_config, 
        mock_mcp_tool
    ):
        """MCP 도구로 에이전트 빌드 테스트"""
        mock_chat_bedrock_class.return_value = MagicMock()
        mock_agent = MagicMock()
        mock_create_agent.return_value = mock_agent
        
        builder = LLMChainBuilder(valid_bedrock_config)
        agent = builder.build_chain([mock_mcp_tool])
        
        assert agent == mock_agent
        mock_create_agent.assert_called_once()
        
        # create_react_agent 호출 인자 확인
        call_kwargs = mock_create_agent.call_args[1]
        assert call_kwargs['model'] == builder.llm
        assert mock_mcp_tool in call_kwargs['tools']
    
    @patch('llm_chain.ChatBedrock')
    @patch('llm_chain.create_react_agent')
    def test_build_chain_with_empty_tools(
        self, 
        mock_create_agent, 
        mock_chat_bedrock_class, 
        valid_bedrock_config
    ):
        """빈 도구 목록으로 에이전트 빌드 테스트"""
        mock_chat_bedrock_class.return_value = MagicMock()
        mock_agent = MagicMock()
        mock_create_agent.return_value = mock_agent
        
        builder = LLMChainBuilder(valid_bedrock_config)
        agent = builder.build_chain([])
        
        assert agent == mock_agent
        call_kwargs = mock_create_agent.call_args[1]
        assert call_kwargs['tools'] == []
    
    @patch('llm_chain.ChatBedrock')
    @patch('llm_chain.create_react_agent')
    def test_build_chain_with_multiple_tools(
        self, 
        mock_create_agent, 
        mock_chat_bedrock_class, 
        valid_bedrock_config
    ):
        """여러 도구로 에이전트 빌드 테스트"""
        mock_chat_bedrock_class.return_value = MagicMock()
        mock_agent = MagicMock()
        mock_create_agent.return_value = mock_agent
        
        # 여러 도구 생성
        tools = []
        for i in range(3):
            tool = Mock()
            tool.name = f"tool_{i}"
            tool.description = f"도구 {i} 설명"
            tools.append(tool)
        
        builder = LLMChainBuilder(valid_bedrock_config)
        agent = builder.build_chain(tools)
        
        call_kwargs = mock_create_agent.call_args[1]
        assert len(call_kwargs['tools']) == 3
    
    @patch('llm_chain.ChatBedrock')
    def test_build_chain_without_llm_initialization(self, mock_chat_bedrock_class, valid_bedrock_config):
        """LLM 초기화 없이 빌드 시도 테스트"""
        mock_chat_bedrock_class.return_value = MagicMock()
        
        builder = LLMChainBuilder(valid_bedrock_config)
        builder.llm = None  # LLM을 None으로 설정
        
        with pytest.raises(ValueError) as exc_info:
            builder.build_chain([])
        
        assert "초기화" in str(exc_info.value)
    
    @patch('llm_chain.ChatBedrock')
    @patch('llm_chain.create_react_agent')
    def test_build_chain_rate_limit_error(
        self, 
        mock_create_agent, 
        mock_chat_bedrock_class, 
        valid_bedrock_config
    ):
        """속도 제한 오류 테스트"""
        mock_chat_bedrock_class.return_value = MagicMock()
        mock_create_agent.side_effect = Exception("ThrottlingException: Rate limit exceeded")
        
        builder = LLMChainBuilder(valid_bedrock_config)
        
        with pytest.raises(BedrockRateLimitError):
            builder.build_chain([])
    
    @patch('llm_chain.ChatBedrock')
    @patch('llm_chain.create_react_agent')
    def test_build_chain_model_error(
        self, 
        mock_create_agent, 
        mock_chat_bedrock_class, 
        valid_bedrock_config
    ):
        """모델 오류 테스트"""
        mock_chat_bedrock_class.return_value = MagicMock()
        mock_create_agent.side_effect = Exception("Model error: context length exceeded")
        
        builder = LLMChainBuilder(valid_bedrock_config)
        
        with pytest.raises(BedrockModelError):
            builder.build_chain([])


# =============================================================================
# build_chain_with_history 메서드 테스트
# =============================================================================

class TestBuildChainWithHistory:
    """build_chain_with_history 메서드 테스트 클래스 (요구사항: 4.3)"""
    
    @patch('llm_chain.ChatBedrock')
    @patch('llm_chain.create_react_agent')
    def test_build_chain_with_history(
        self, 
        mock_create_agent, 
        mock_chat_bedrock_class, 
        valid_bedrock_config,
        sample_chat_history
    ):
        """대화 기록으로 에이전트 빌드 테스트"""
        mock_chat_bedrock_class.return_value = MagicMock()
        mock_agent = MagicMock()
        mock_create_agent.return_value = mock_agent
        
        builder = LLMChainBuilder(valid_bedrock_config)
        agent = builder.build_chain_with_history([], sample_chat_history)
        
        assert agent == mock_agent
    
    @patch('llm_chain.ChatBedrock')
    @patch('llm_chain.create_react_agent')
    def test_build_chain_with_empty_history(
        self, 
        mock_create_agent, 
        mock_chat_bedrock_class, 
        valid_bedrock_config
    ):
        """빈 대화 기록으로 에이전트 빌드 테스트"""
        mock_chat_bedrock_class.return_value = MagicMock()
        mock_agent = MagicMock()
        mock_create_agent.return_value = mock_agent
        
        builder = LLMChainBuilder(valid_bedrock_config)
        agent = builder.build_chain_with_history([], [])
        
        assert agent == mock_agent


# =============================================================================
# _convert_chat_history 메서드 테스트
# =============================================================================

class TestConvertChatHistory:
    """_convert_chat_history 메서드 테스트 클래스"""
    
    @patch('llm_chain.ChatBedrock')
    def test_convert_user_messages(self, mock_chat_bedrock_class, valid_bedrock_config):
        """사용자 메시지 변환 테스트"""
        mock_chat_bedrock_class.return_value = MagicMock()
        
        builder = LLMChainBuilder(valid_bedrock_config)
        history = [{"role": "user", "content": "안녕하세요"}]
        
        messages = builder._convert_chat_history(history)
        
        assert len(messages) == 1
        assert isinstance(messages[0], HumanMessage)
        assert messages[0].content == "안녕하세요"
    
    @patch('llm_chain.ChatBedrock')
    def test_convert_assistant_messages(self, mock_chat_bedrock_class, valid_bedrock_config):
        """어시스턴트 메시지 변환 테스트"""
        mock_chat_bedrock_class.return_value = MagicMock()
        
        builder = LLMChainBuilder(valid_bedrock_config)
        history = [{"role": "assistant", "content": "안녕하세요!"}]
        
        messages = builder._convert_chat_history(history)
        
        assert len(messages) == 1
        assert isinstance(messages[0], AIMessage)
        assert messages[0].content == "안녕하세요!"
    
    @patch('llm_chain.ChatBedrock')
    def test_convert_system_messages(self, mock_chat_bedrock_class, valid_bedrock_config):
        """시스템 메시지 변환 테스트"""
        mock_chat_bedrock_class.return_value = MagicMock()
        
        builder = LLMChainBuilder(valid_bedrock_config)
        history = [{"role": "system", "content": "시스템 프롬프트"}]
        
        messages = builder._convert_chat_history(history)
        
        assert len(messages) == 1
        assert isinstance(messages[0], SystemMessage)
        assert messages[0].content == "시스템 프롬프트"
    
    @patch('llm_chain.ChatBedrock')
    def test_convert_mixed_messages(
        self, 
        mock_chat_bedrock_class, 
        valid_bedrock_config,
        sample_chat_history
    ):
        """혼합 메시지 변환 테스트"""
        mock_chat_bedrock_class.return_value = MagicMock()
        
        builder = LLMChainBuilder(valid_bedrock_config)
        messages = builder._convert_chat_history(sample_chat_history)
        
        assert len(messages) == 4
        assert isinstance(messages[0], HumanMessage)
        assert isinstance(messages[1], AIMessage)
        assert isinstance(messages[2], HumanMessage)
        assert isinstance(messages[3], AIMessage)
    
    @patch('llm_chain.ChatBedrock')
    def test_convert_empty_history(self, mock_chat_bedrock_class, valid_bedrock_config):
        """빈 대화 기록 변환 테스트"""
        mock_chat_bedrock_class.return_value = MagicMock()
        
        builder = LLMChainBuilder(valid_bedrock_config)
        messages = builder._convert_chat_history([])
        
        assert messages == []
    
    @patch('llm_chain.ChatBedrock')
    def test_convert_unknown_role(self, mock_chat_bedrock_class, valid_bedrock_config):
        """알 수 없는 역할 변환 테스트 (무시됨)"""
        mock_chat_bedrock_class.return_value = MagicMock()
        
        builder = LLMChainBuilder(valid_bedrock_config)
        history = [{"role": "unknown", "content": "알 수 없는 메시지"}]
        
        messages = builder._convert_chat_history(history)
        
        # 알 수 없는 역할은 무시됨
        assert len(messages) == 0


# =============================================================================
# invoke_agent 메서드 테스트
# =============================================================================

class TestInvokeAgent:
    """invoke_agent 메서드 테스트 클래스 (요구사항: 4.3)"""
    
    @pytest.mark.asyncio
    @patch('llm_chain.ChatBedrock')
    async def test_invoke_agent_success(
        self, 
        mock_chat_bedrock_class, 
        valid_bedrock_config,
        mock_agent
    ):
        """에이전트 호출 성공 테스트"""
        mock_chat_bedrock_class.return_value = MagicMock()
        
        builder = LLMChainBuilder(valid_bedrock_config)
        result = await builder.invoke_agent(mock_agent, "테스트 질문")
        
        assert "messages" in result
        assert "output" in result
        assert result["output"] == "테스트 응답"
    
    @pytest.mark.asyncio
    @patch('llm_chain.ChatBedrock')
    async def test_invoke_agent_with_history(
        self, 
        mock_chat_bedrock_class, 
        valid_bedrock_config,
        mock_agent
    ):
        """대화 기록과 함께 에이전트 호출 테스트"""
        mock_chat_bedrock_class.return_value = MagicMock()
        
        builder = LLMChainBuilder(valid_bedrock_config)
        history = [HumanMessage(content="이전 질문")]
        
        result = await builder.invoke_agent(mock_agent, "새 질문", chat_history=history)
        
        assert "output" in result
    
    @pytest.mark.asyncio
    @patch('llm_chain.ChatBedrock')
    async def test_invoke_agent_rate_limit_error(
        self, 
        mock_chat_bedrock_class, 
        valid_bedrock_config
    ):
        """에이전트 호출 시 속도 제한 오류 테스트"""
        mock_chat_bedrock_class.return_value = MagicMock()
        
        mock_agent = AsyncMock()
        mock_agent.ainvoke.side_effect = Exception("ThrottlingException: Too many requests")
        
        builder = LLMChainBuilder(valid_bedrock_config)
        
        with pytest.raises(BedrockRateLimitError):
            await builder.invoke_agent(mock_agent, "테스트")
    
    @pytest.mark.asyncio
    @patch('llm_chain.ChatBedrock')
    async def test_invoke_agent_authentication_error(
        self, 
        mock_chat_bedrock_class, 
        valid_bedrock_config
    ):
        """에이전트 호출 시 인증 오류 테스트"""
        mock_chat_bedrock_class.return_value = MagicMock()
        
        mock_agent = AsyncMock()
        mock_agent.ainvoke.side_effect = Exception("Access denied: Invalid credentials")
        
        builder = LLMChainBuilder(valid_bedrock_config)
        
        with pytest.raises(BedrockAuthenticationError):
            await builder.invoke_agent(mock_agent, "테스트")
    
    @pytest.mark.asyncio
    @patch('llm_chain.ChatBedrock')
    async def test_invoke_agent_connection_error(
        self, 
        mock_chat_bedrock_class, 
        valid_bedrock_config
    ):
        """에이전트 호출 시 연결 오류 테스트"""
        mock_chat_bedrock_class.return_value = MagicMock()
        
        mock_agent = AsyncMock()
        mock_agent.ainvoke.side_effect = Exception("Connection timeout")
        
        builder = LLMChainBuilder(valid_bedrock_config)
        
        with pytest.raises(BedrockConnectionError):
            await builder.invoke_agent(mock_agent, "테스트")
    
    @pytest.mark.asyncio
    @patch('llm_chain.ChatBedrock')
    async def test_invoke_agent_model_error(
        self, 
        mock_chat_bedrock_class, 
        valid_bedrock_config
    ):
        """에이전트 호출 시 모델 오류 테스트"""
        mock_chat_bedrock_class.return_value = MagicMock()
        
        mock_agent = AsyncMock()
        mock_agent.ainvoke.side_effect = Exception("Model error: token limit exceeded")
        
        builder = LLMChainBuilder(valid_bedrock_config)
        
        with pytest.raises(BedrockModelError):
            await builder.invoke_agent(mock_agent, "테스트")
    
    @pytest.mark.asyncio
    @patch('llm_chain.ChatBedrock')
    async def test_invoke_agent_generic_error(
        self, 
        mock_chat_bedrock_class, 
        valid_bedrock_config
    ):
        """에이전트 호출 시 일반 오류 테스트"""
        mock_chat_bedrock_class.return_value = MagicMock()
        
        mock_agent = AsyncMock()
        mock_agent.ainvoke.side_effect = Exception("Unknown error")
        
        builder = LLMChainBuilder(valid_bedrock_config)
        
        with pytest.raises(BedrockAPIError):
            await builder.invoke_agent(mock_agent, "테스트")


# =============================================================================
# get_llm_info 메서드 테스트
# =============================================================================

class TestGetLLMInfo:
    """get_llm_info 메서드 테스트 클래스"""
    
    @patch('llm_chain.ChatBedrock')
    def test_get_llm_info_initialized(self, mock_chat_bedrock_class, valid_bedrock_config):
        """초기화된 LLM 정보 가져오기 테스트"""
        mock_chat_bedrock_class.return_value = MagicMock()
        
        builder = LLMChainBuilder(valid_bedrock_config)
        info = builder.get_llm_info()
        
        assert info["model_id"] == valid_bedrock_config.model_id
        assert info["region"] == valid_bedrock_config.region
        assert info["temperature"] == valid_bedrock_config.temperature
        assert info["max_tokens"] == valid_bedrock_config.max_tokens
        assert info["is_initialized"] is True
    
    @patch('llm_chain.ChatBedrock')
    def test_get_llm_info_not_initialized(self, mock_chat_bedrock_class, valid_bedrock_config):
        """초기화되지 않은 LLM 정보 가져오기 테스트"""
        mock_chat_bedrock_class.return_value = MagicMock()
        
        builder = LLMChainBuilder(valid_bedrock_config)
        builder.llm = None  # LLM을 None으로 설정
        
        info = builder.get_llm_info()
        
        assert info["is_initialized"] is False


# =============================================================================
# format_agent_response 함수 테스트
# =============================================================================

class TestFormatAgentResponse:
    """format_agent_response 함수 테스트 클래스"""
    
    def test_format_with_output_key(self):
        """output 키가 있는 결과 포맷팅 테스트"""
        result = {"output": "  테스트 응답  ", "messages": []}
        
        formatted = format_agent_response(result)
        
        assert formatted == "테스트 응답"
    
    def test_format_with_ai_message(self):
        """AIMessage가 있는 결과 포맷팅 테스트"""
        result = {
            "output": "",
            "messages": [
                HumanMessage(content="질문"),
                AIMessage(content="  AI 응답  ")
            ]
        }
        
        formatted = format_agent_response(result)
        
        assert formatted == "AI 응답"
    
    def test_format_with_multiple_ai_messages(self):
        """여러 AIMessage가 있는 결과 포맷팅 테스트 (마지막 메시지 반환)"""
        result = {
            "output": "",
            "messages": [
                AIMessage(content="첫 번째 응답"),
                HumanMessage(content="추가 질문"),
                AIMessage(content="마지막 응답")
            ]
        }
        
        formatted = format_agent_response(result)
        
        assert formatted == "마지막 응답"
    
    def test_format_empty_result(self):
        """빈 결과 포맷팅 테스트"""
        result = {"output": "", "messages": []}
        
        formatted = format_agent_response(result)
        
        assert formatted == "응답을 생성할 수 없습니다."
    
    def test_format_no_output_no_messages(self):
        """output과 messages가 없는 결과 포맷팅 테스트"""
        result = {}
        
        formatted = format_agent_response(result)
        
        assert formatted == "응답을 생성할 수 없습니다."
    
    def test_format_with_message_type_attribute(self):
        """type 속성이 있는 메시지 포맷팅 테스트"""
        mock_message = Mock()
        mock_message.content = "모의 응답"
        mock_message.type = "ai"
        
        result = {"output": "", "messages": [mock_message]}
        
        formatted = format_agent_response(result)
        
        assert formatted == "모의 응답"


# =============================================================================
# create_agent_executor 편의 함수 테스트
# =============================================================================

class TestCreateAgentExecutor:
    """create_agent_executor 편의 함수 테스트 클래스 (요구사항: 4.2, 4.3, 5.3)"""
    
    @patch('llm_chain.ChatBedrock')
    @patch('llm_chain.create_react_agent')
    def test_create_agent_executor_basic(
        self, 
        mock_create_agent, 
        mock_chat_bedrock_class, 
        valid_bedrock_config,
        mock_mcp_tool
    ):
        """기본 에이전트 실행자 생성 테스트"""
        mock_chat_bedrock_class.return_value = MagicMock()
        mock_agent = MagicMock()
        mock_create_agent.return_value = mock_agent
        
        agent = create_agent_executor(valid_bedrock_config, [mock_mcp_tool])
        
        assert agent == mock_agent
    
    @patch('llm_chain.ChatBedrock')
    @patch('llm_chain.create_react_agent')
    def test_create_agent_executor_with_history(
        self, 
        mock_create_agent, 
        mock_chat_bedrock_class, 
        valid_bedrock_config,
        sample_chat_history
    ):
        """대화 기록으로 에이전트 실행자 생성 테스트"""
        mock_chat_bedrock_class.return_value = MagicMock()
        mock_agent = MagicMock()
        mock_create_agent.return_value = mock_agent
        
        agent = create_agent_executor(
            valid_bedrock_config, 
            [], 
            chat_history=sample_chat_history
        )
        
        assert agent == mock_agent
    
    @patch('llm_chain.ChatBedrock')
    @patch('llm_chain.create_react_agent')
    def test_create_agent_executor_with_custom_prompt(
        self, 
        mock_create_agent, 
        mock_chat_bedrock_class, 
        valid_bedrock_config
    ):
        """커스텀 프롬프트로 에이전트 실행자 생성 테스트"""
        mock_chat_bedrock_class.return_value = MagicMock()
        mock_agent = MagicMock()
        mock_create_agent.return_value = mock_agent
        
        custom_prompt = "커스텀 시스템 프롬프트"
        agent = create_agent_executor(
            valid_bedrock_config, 
            [], 
            system_prompt=custom_prompt
        )
        
        assert agent == mock_agent


# =============================================================================
# 통합 시나리오 테스트
# =============================================================================

class TestIntegrationScenarios:
    """통합 시나리오 테스트 클래스"""
    
    @patch('llm_chain.ChatBedrock')
    @patch('llm_chain.create_react_agent')
    def test_full_workflow_mock(
        self, 
        mock_create_agent, 
        mock_chat_bedrock_class, 
        valid_bedrock_config,
        mock_mcp_tool
    ):
        """전체 워크플로우 모의 테스트"""
        mock_chat_bedrock_class.return_value = MagicMock()
        mock_agent = MagicMock()
        mock_create_agent.return_value = mock_agent
        
        # 1. 빌더 생성
        builder = LLMChainBuilder(valid_bedrock_config)
        assert builder.llm is not None
        
        # 2. 에이전트 빌드
        agent = builder.build_chain([mock_mcp_tool])
        assert agent is not None
        
        # 3. LLM 정보 확인
        info = builder.get_llm_info()
        assert info["is_initialized"] is True
        assert info["model_id"] == valid_bedrock_config.model_id
    
    @patch('llm_chain.ChatBedrock')
    @patch('llm_chain.create_react_agent')
    def test_workflow_with_history(
        self, 
        mock_create_agent, 
        mock_chat_bedrock_class, 
        valid_bedrock_config,
        sample_chat_history
    ):
        """대화 기록이 있는 워크플로우 테스트"""
        mock_chat_bedrock_class.return_value = MagicMock()
        mock_agent = MagicMock()
        mock_create_agent.return_value = mock_agent
        
        # 1. 빌더 생성
        builder = LLMChainBuilder(valid_bedrock_config)
        
        # 2. 대화 기록 변환
        messages = builder._convert_chat_history(sample_chat_history)
        assert len(messages) == 4
        
        # 3. 대화 기록으로 에이전트 빌드
        agent = builder.build_chain_with_history([], sample_chat_history)
        assert agent is not None


# =============================================================================
# 엣지 케이스 테스트
# =============================================================================

class TestEdgeCases:
    """엣지 케이스 테스트 클래스"""
    
    @patch('llm_chain.ChatBedrock')
    def test_empty_content_in_history(self, mock_chat_bedrock_class, valid_bedrock_config):
        """빈 내용이 있는 대화 기록 테스트"""
        mock_chat_bedrock_class.return_value = MagicMock()
        
        builder = LLMChainBuilder(valid_bedrock_config)
        history = [
            {"role": "user", "content": ""},
            {"role": "assistant", "content": ""}
        ]
        
        messages = builder._convert_chat_history(history)
        
        assert len(messages) == 2
        assert messages[0].content == ""
        assert messages[1].content == ""
    
    @patch('llm_chain.ChatBedrock')
    def test_missing_content_key(self, mock_chat_bedrock_class, valid_bedrock_config):
        """content 키가 없는 대화 기록 테스트"""
        mock_chat_bedrock_class.return_value = MagicMock()
        
        builder = LLMChainBuilder(valid_bedrock_config)
        history = [{"role": "user"}]  # content 키 없음
        
        messages = builder._convert_chat_history(history)
        
        assert len(messages) == 1
        assert messages[0].content == ""
    
    @patch('llm_chain.ChatBedrock')
    def test_missing_role_key(self, mock_chat_bedrock_class, valid_bedrock_config):
        """role 키가 없는 대화 기록 테스트"""
        mock_chat_bedrock_class.return_value = MagicMock()
        
        builder = LLMChainBuilder(valid_bedrock_config)
        history = [{"content": "메시지"}]  # role 키 없음
        
        messages = builder._convert_chat_history(history)
        
        # role이 없으면 무시됨
        assert len(messages) == 0
    
    def test_format_response_with_none_messages(self):
        """messages가 None인 결과 포맷팅 테스트"""
        result = {"output": "", "messages": None}
        
        formatted = format_agent_response(result)
        
        assert formatted == "응답을 생성할 수 없습니다."
    
    @patch('llm_chain.ChatBedrock')
    def test_unicode_content(self, mock_chat_bedrock_class, valid_bedrock_config):
        """유니코드 내용 처리 테스트"""
        mock_chat_bedrock_class.return_value = MagicMock()
        
        builder = LLMChainBuilder(valid_bedrock_config)
        history = [
            {"role": "user", "content": "안녕하세요 🎉"},
            {"role": "assistant", "content": "반갑습니다! 😊"}
        ]
        
        messages = builder._convert_chat_history(history)
        
        assert messages[0].content == "안녕하세요 🎉"
        assert messages[1].content == "반갑습니다! 😊"
    
    @patch('llm_chain.ChatBedrock')
    def test_long_content(self, mock_chat_bedrock_class, valid_bedrock_config):
        """긴 내용 처리 테스트"""
        mock_chat_bedrock_class.return_value = MagicMock()
        
        builder = LLMChainBuilder(valid_bedrock_config)
        long_content = "테스트 " * 1000
        history = [{"role": "user", "content": long_content}]
        
        messages = builder._convert_chat_history(history)
        
        assert messages[0].content == long_content
