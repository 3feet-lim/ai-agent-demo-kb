"""
대화 서비스 단위 테스트

이 모듈은 ConversationService 클래스의 단위 테스트를 포함합니다.
데이터베이스, LLM 체인, MCP 관리자를 모의(mock)하여 서비스 로직을 테스트합니다.

테스트 범위:
- 세션 생성 (create_session)
- 세션 목록 조회 (list_sessions)
- 대화 기록 조회 (get_history)
- 메시지 전송 (send_message)
- 오류 처리

요구사항: 3.1, 3.2, 4.3, 7.1, 7.2
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
from uuid import uuid4

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from conversation_service import (
    ConversationService,
    ConversationServiceError,
    SessionNotFoundError,
    MessageProcessingError,
    AIResponseError,
    create_conversation_service
)
from models import MessageResponse, SessionResponse
from llm_chain import BedrockAPIError, BedrockConnectionError


# =============================================================================
# 테스트 픽스처
# =============================================================================

@pytest.fixture
def mock_db():
    """모의 데이터베이스 인스턴스"""
    db = Mock()
    db.create_session = Mock()
    db.list_sessions = Mock()
    db.get_messages = Mock()
    db.save_message = Mock()
    return db


@pytest.fixture
def mock_llm_chain_builder():
    """모의 LLM 체인 빌더 인스턴스"""
    builder = Mock()
    builder.build_chain = Mock()
    builder.invoke_agent = AsyncMock()
    return builder


@pytest.fixture
def mock_mcp_manager():
    """모의 MCP 서버 관리자 인스턴스"""
    manager = Mock()
    manager.get_all_tools = Mock(return_value=[])
    return manager


@pytest.fixture
def conversation_service(mock_db, mock_llm_chain_builder, mock_mcp_manager):
    """ConversationService 인스턴스"""
    return ConversationService(
        db=mock_db,
        llm_chain_builder=mock_llm_chain_builder,
        mcp_manager=mock_mcp_manager
    )


@pytest.fixture
def sample_session():
    """샘플 세션 데이터"""
    return {
        'id': str(uuid4()),
        'title': '테스트 세션',
        'created_at': datetime.utcnow().isoformat(),
        'last_message_at': datetime.utcnow().isoformat()
    }


@pytest.fixture
def sample_message():
    """샘플 메시지 데이터"""
    return {
        'id': str(uuid4()),
        'session_id': str(uuid4()),
        'content': '테스트 메시지',
        'role': 'user',
        'timestamp': datetime.utcnow().isoformat()
    }


# =============================================================================
# 세션 생성 테스트
# =============================================================================

class TestCreateSession:
    """create_session 메서드 테스트"""
    
    def test_create_session_with_default_title(
        self,
        conversation_service,
        mock_db,
        sample_session
    ):
        """기본 제목으로 세션 생성 테스트"""
        # Given
        sample_session['title'] = '새 대화'
        mock_db.create_session.return_value = sample_session
        
        # When
        result = conversation_service.create_session()
        
        # Then
        assert isinstance(result, SessionResponse)
        assert result.title == '새 대화'
        mock_db.create_session.assert_called_once_with(title='새 대화')
    
    def test_create_session_with_custom_title(
        self,
        conversation_service,
        mock_db,
        sample_session
    ):
        """사용자 지정 제목으로 세션 생성 테스트"""
        # Given
        custom_title = '인프라 분석'
        sample_session['title'] = custom_title
        mock_db.create_session.return_value = sample_session
        
        # When
        result = conversation_service.create_session(title=custom_title)
        
        # Then
        assert isinstance(result, SessionResponse)
        assert result.title == custom_title
        mock_db.create_session.assert_called_once_with(title=custom_title)
    
    def test_create_session_returns_valid_session_response(
        self,
        conversation_service,
        mock_db,
        sample_session
    ):
        """세션 생성 시 유효한 SessionResponse 반환 테스트"""
        # Given
        mock_db.create_session.return_value = sample_session
        
        # When
        result = conversation_service.create_session()
        
        # Then
        assert result.id == sample_session['id']
        assert result.created_at == sample_session['created_at']
        assert result.last_message_at == sample_session['last_message_at']
    
    def test_create_session_database_error(
        self,
        conversation_service,
        mock_db
    ):
        """데이터베이스 오류 시 예외 발생 테스트"""
        # Given
        mock_db.create_session.side_effect = Exception("데이터베이스 연결 실패")
        
        # When/Then
        with pytest.raises(ConversationServiceError) as exc_info:
            conversation_service.create_session()
        
        assert "세션 생성 중 오류" in str(exc_info.value)


# =============================================================================
# 세션 목록 조회 테스트
# =============================================================================

class TestListSessions:
    """list_sessions 메서드 테스트"""
    
    def test_list_sessions_empty(
        self,
        conversation_service,
        mock_db
    ):
        """빈 세션 목록 조회 테스트"""
        # Given
        mock_db.list_sessions.return_value = []
        
        # When
        result = conversation_service.list_sessions()
        
        # Then
        assert isinstance(result, list)
        assert len(result) == 0
    
    def test_list_sessions_multiple(
        self,
        conversation_service,
        mock_db
    ):
        """여러 세션 목록 조회 테스트"""
        # Given
        sessions = [
            {
                'id': str(uuid4()),
                'title': '세션 1',
                'created_at': datetime.utcnow().isoformat(),
                'last_message_at': datetime.utcnow().isoformat()
            },
            {
                'id': str(uuid4()),
                'title': '세션 2',
                'created_at': datetime.utcnow().isoformat(),
                'last_message_at': datetime.utcnow().isoformat()
            }
        ]
        mock_db.list_sessions.return_value = sessions
        
        # When
        result = conversation_service.list_sessions()
        
        # Then
        assert len(result) == 2
        assert all(isinstance(s, SessionResponse) for s in result)
        assert result[0].title == '세션 1'
        assert result[1].title == '세션 2'
    
    def test_list_sessions_database_error(
        self,
        conversation_service,
        mock_db
    ):
        """데이터베이스 오류 시 예외 발생 테스트"""
        # Given
        mock_db.list_sessions.side_effect = Exception("데이터베이스 오류")
        
        # When/Then
        with pytest.raises(ConversationServiceError) as exc_info:
            conversation_service.list_sessions()
        
        assert "세션 목록 조회 중 오류" in str(exc_info.value)


# =============================================================================
# 대화 기록 조회 테스트
# =============================================================================

class TestGetHistory:
    """get_history 메서드 테스트"""
    
    def test_get_history_empty(
        self,
        conversation_service,
        mock_db,
        sample_session
    ):
        """빈 대화 기록 조회 테스트"""
        # Given
        mock_db.list_sessions.return_value = [sample_session]
        mock_db.get_messages.return_value = []
        
        # When
        result = conversation_service.get_history(sample_session['id'])
        
        # Then
        assert isinstance(result, list)
        assert len(result) == 0
    
    def test_get_history_with_messages(
        self,
        conversation_service,
        mock_db,
        sample_session
    ):
        """메시지가 있는 대화 기록 조회 테스트"""
        # Given
        session_id = sample_session['id']
        messages = [
            {
                'id': str(uuid4()),
                'session_id': session_id,
                'content': '안녕하세요',
                'role': 'user',
                'timestamp': datetime.utcnow().isoformat()
            },
            {
                'id': str(uuid4()),
                'session_id': session_id,
                'content': '안녕하세요! 무엇을 도와드릴까요?',
                'role': 'assistant',
                'timestamp': datetime.utcnow().isoformat()
            }
        ]
        mock_db.list_sessions.return_value = [sample_session]
        mock_db.get_messages.return_value = messages
        
        # When
        result = conversation_service.get_history(session_id)
        
        # Then
        assert len(result) == 2
        assert all(isinstance(m, MessageResponse) for m in result)
        assert result[0].role == 'user'
        assert result[1].role == 'assistant'
    
    def test_get_history_session_not_found(
        self,
        conversation_service,
        mock_db
    ):
        """존재하지 않는 세션 조회 시 예외 발생 테스트"""
        # Given
        mock_db.list_sessions.return_value = []
        non_existent_session_id = str(uuid4())
        
        # When/Then
        with pytest.raises(SessionNotFoundError) as exc_info:
            conversation_service.get_history(non_existent_session_id)
        
        assert non_existent_session_id in str(exc_info.value)
    
    def test_get_history_database_error(
        self,
        conversation_service,
        mock_db,
        sample_session
    ):
        """데이터베이스 오류 시 예외 발생 테스트"""
        # Given
        mock_db.list_sessions.return_value = [sample_session]
        mock_db.get_messages.side_effect = Exception("데이터베이스 오류")
        
        # When/Then
        with pytest.raises(ConversationServiceError) as exc_info:
            conversation_service.get_history(sample_session['id'])
        
        assert "대화 기록 조회 중 오류" in str(exc_info.value)


# =============================================================================
# 메시지 전송 테스트
# =============================================================================

class TestSendMessage:
    """send_message 메서드 테스트"""
    
    @pytest.mark.asyncio
    async def test_send_message_success(
        self,
        conversation_service,
        mock_db,
        mock_llm_chain_builder,
        mock_mcp_manager,
        sample_session
    ):
        """메시지 전송 성공 테스트"""
        # Given
        session_id = sample_session['id']
        user_content = "CPU 사용률을 확인해주세요"
        ai_response = "현재 CPU 사용률은 45%입니다."
        
        mock_db.list_sessions.return_value = [sample_session]
        mock_db.get_messages.return_value = []
        mock_db.save_message.side_effect = [
            # 사용자 메시지 저장
            {
                'id': str(uuid4()),
                'session_id': session_id,
                'content': user_content,
                'role': 'user',
                'timestamp': datetime.utcnow().isoformat()
            },
            # AI 응답 저장
            {
                'id': str(uuid4()),
                'session_id': session_id,
                'content': ai_response,
                'role': 'assistant',
                'timestamp': datetime.utcnow().isoformat()
            }
        ]
        
        mock_agent = Mock()
        mock_llm_chain_builder.build_chain.return_value = mock_agent
        mock_llm_chain_builder.invoke_agent.return_value = {
            'output': ai_response,
            'messages': []
        }
        
        # When
        result = await conversation_service.send_message(session_id, user_content)
        
        # Then
        assert isinstance(result, MessageResponse)
        assert result.role == 'assistant'
        assert result.content == ai_response
        assert mock_db.save_message.call_count == 2
    
    @pytest.mark.asyncio
    async def test_send_message_session_not_found(
        self,
        conversation_service,
        mock_db
    ):
        """존재하지 않는 세션에 메시지 전송 시 예외 발생 테스트"""
        # Given
        mock_db.list_sessions.return_value = []
        non_existent_session_id = str(uuid4())
        
        # When/Then
        with pytest.raises(SessionNotFoundError) as exc_info:
            await conversation_service.send_message(
                non_existent_session_id,
                "테스트 메시지"
            )
        
        assert non_existent_session_id in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_send_message_ai_error(
        self,
        conversation_service,
        mock_db,
        mock_llm_chain_builder,
        mock_mcp_manager,
        sample_session
    ):
        """AI 응답 생성 오류 시 예외 발생 테스트"""
        # Given
        session_id = sample_session['id']
        
        mock_db.list_sessions.return_value = [sample_session]
        mock_db.get_messages.return_value = []
        mock_db.save_message.return_value = {
            'id': str(uuid4()),
            'session_id': session_id,
            'content': '테스트',
            'role': 'user',
            'timestamp': datetime.utcnow().isoformat()
        }
        
        mock_agent = Mock()
        mock_llm_chain_builder.build_chain.return_value = mock_agent
        mock_llm_chain_builder.invoke_agent.side_effect = BedrockAPIError(
            message="API 호출 실패"
        )
        
        # When/Then
        with pytest.raises(AIResponseError) as exc_info:
            await conversation_service.send_message(session_id, "테스트 메시지")
        
        assert "AI 응답 생성 중 오류" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_send_message_saves_user_message_first(
        self,
        conversation_service,
        mock_db,
        mock_llm_chain_builder,
        mock_mcp_manager,
        sample_session
    ):
        """사용자 메시지가 먼저 저장되는지 테스트"""
        # Given
        session_id = sample_session['id']
        user_content = "테스트 메시지"
        
        mock_db.list_sessions.return_value = [sample_session]
        mock_db.get_messages.return_value = []
        
        saved_messages = []
        def track_save_message(session_id, content, role, **kwargs):
            saved_messages.append({'role': role, 'content': content})
            return {
                'id': str(uuid4()),
                'session_id': session_id,
                'content': content,
                'role': role,
                'timestamp': datetime.utcnow().isoformat()
            }
        
        mock_db.save_message.side_effect = track_save_message
        
        mock_agent = Mock()
        mock_llm_chain_builder.build_chain.return_value = mock_agent
        mock_llm_chain_builder.invoke_agent.return_value = {
            'output': 'AI 응답',
            'messages': []
        }
        
        # When
        await conversation_service.send_message(session_id, user_content)
        
        # Then
        assert len(saved_messages) == 2
        assert saved_messages[0]['role'] == 'user'
        assert saved_messages[0]['content'] == user_content
        assert saved_messages[1]['role'] == 'assistant'


# =============================================================================
# 세션 정보 조회 테스트
# =============================================================================

class TestGetSessionInfo:
    """get_session_info 메서드 테스트"""
    
    def test_get_session_info_found(
        self,
        conversation_service,
        mock_db,
        sample_session
    ):
        """세션 정보 조회 성공 테스트"""
        # Given
        mock_db.list_sessions.return_value = [sample_session]
        
        # When
        result = conversation_service.get_session_info(sample_session['id'])
        
        # Then
        assert result is not None
        assert isinstance(result, SessionResponse)
        assert result.id == sample_session['id']
    
    def test_get_session_info_not_found(
        self,
        conversation_service,
        mock_db
    ):
        """존재하지 않는 세션 정보 조회 테스트"""
        # Given
        mock_db.list_sessions.return_value = []
        
        # When
        result = conversation_service.get_session_info(str(uuid4()))
        
        # Then
        assert result is None
    
    def test_get_session_info_database_error(
        self,
        conversation_service,
        mock_db
    ):
        """데이터베이스 오류 시 None 반환 테스트"""
        # Given
        mock_db.list_sessions.side_effect = Exception("데이터베이스 오류")
        
        # When
        result = conversation_service.get_session_info(str(uuid4()))
        
        # Then
        assert result is None


# =============================================================================
# 편의 함수 테스트
# =============================================================================

class TestCreateConversationService:
    """create_conversation_service 함수 테스트"""
    
    def test_create_conversation_service(
        self,
        mock_db,
        mock_llm_chain_builder,
        mock_mcp_manager
    ):
        """편의 함수로 서비스 생성 테스트"""
        # When
        service = create_conversation_service(
            db=mock_db,
            llm_chain_builder=mock_llm_chain_builder,
            mcp_manager=mock_mcp_manager
        )
        
        # Then
        assert isinstance(service, ConversationService)
        assert service.db == mock_db
        assert service.llm_chain_builder == mock_llm_chain_builder
        assert service.mcp_manager == mock_mcp_manager


# =============================================================================
# 예외 클래스 테스트
# =============================================================================

class TestExceptionClasses:
    """예외 클래스 테스트"""
    
    def test_conversation_service_error(self):
        """ConversationServiceError 테스트"""
        error = ConversationServiceError("테스트 오류")
        assert "대화 서비스 오류" in str(error)
        assert "테스트 오류" in str(error)
    
    def test_conversation_service_error_with_original(self):
        """원본 예외가 있는 ConversationServiceError 테스트"""
        original = ValueError("원본 오류")
        error = ConversationServiceError("테스트 오류", original_error=original)
        assert "ValueError" in str(error)
        assert "원본 오류" in str(error)
    
    def test_session_not_found_error(self):
        """SessionNotFoundError 테스트"""
        session_id = "test-session-123"
        error = SessionNotFoundError(session_id)
        assert session_id in str(error)
        assert "세션을 찾을 수 없습니다" in str(error)
    
    def test_message_processing_error(self):
        """MessageProcessingError 테스트"""
        error = MessageProcessingError("처리 오류")
        assert "처리 오류" in str(error)
    
    def test_ai_response_error(self):
        """AIResponseError 테스트"""
        error = AIResponseError("AI 오류")
        assert "AI 오류" in str(error)
