"""
API 엔드포인트 단위 테스트

이 모듈은 세션 및 메시지 API 엔드포인트에 대한 단위 테스트를 포함합니다.
FastAPI의 TestClient를 사용하여 엔드포인트를 테스트합니다.

테스트 대상:
- POST /api/sessions - 새 세션 생성
- GET /api/sessions - 모든 세션 나열
- GET /api/sessions/{session_id}/messages - 세션 기록 가져오기
- POST /api/sessions/{session_id}/messages - 메시지 전송
- 요청 검증 및 오류 처리

요구사항: 2.3, 3.1, 3.2, 3.3
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from routes import sessions_router, set_conversation_service, get_conversation_service
from models import (
    SessionResponse,
    MessageResponse,
    SessionListResponse,
    MessageHistoryResponse
)
from conversation_service import (
    ConversationService,
    SessionNotFoundError,
    MessageProcessingError,
    AIResponseError,
    ConversationServiceError
)


# =============================================================================
# 테스트 픽스처
# =============================================================================

@pytest.fixture
def mock_conversation_service():
    """
    모의 ConversationService 인스턴스를 생성합니다.
    """
    service = Mock(spec=ConversationService)
    return service


@pytest.fixture
def test_app(mock_conversation_service):
    """
    테스트용 FastAPI 앱을 생성합니다.
    """
    app = FastAPI()
    app.include_router(sessions_router, prefix="/api")
    
    # 의존성 주입 설정
    set_conversation_service(mock_conversation_service)
    
    return app


@pytest.fixture
def client(test_app):
    """
    테스트 클라이언트를 생성합니다.
    """
    return TestClient(test_app)


@pytest.fixture
def sample_session():
    """
    샘플 세션 응답을 생성합니다.
    """
    return SessionResponse(
        id="test-session-123",
        title="테스트 세션",
        created_at="2024-01-15T10:00:00",
        last_message_at="2024-01-15T10:00:00"
    )


@pytest.fixture
def sample_message():
    """
    샘플 메시지 응답을 생성합니다.
    """
    return MessageResponse(
        id="test-message-123",
        session_id="test-session-123",
        content="테스트 응답입니다.",
        role="assistant",
        timestamp="2024-01-15T10:30:00"
    )


# =============================================================================
# POST /api/sessions 테스트 - 새 세션 생성
# =============================================================================

class TestCreateSession:
    """
    POST /api/sessions 엔드포인트 테스트
    
    요구사항: 3.1
    """
    
    def test_create_session_success(self, client, mock_conversation_service, sample_session):
        """
        세션 생성 성공 테스트
        """
        mock_conversation_service.create_session.return_value = sample_session
        
        response = client.post(
            "/api/sessions",
            json={"title": "테스트 세션"}
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["id"] == "test-session-123"
        assert data["title"] == "테스트 세션"
        mock_conversation_service.create_session.assert_called_once_with(title="테스트 세션")
    
    def test_create_session_with_default_title(self, client, mock_conversation_service, sample_session):
        """
        기본 제목으로 세션 생성 테스트
        """
        sample_session.title = "새 대화"
        mock_conversation_service.create_session.return_value = sample_session
        
        response = client.post(
            "/api/sessions",
            json={}
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "새 대화"
        mock_conversation_service.create_session.assert_called_once_with(title="새 대화")
    
    def test_create_session_empty_body(self, client, mock_conversation_service, sample_session):
        """
        빈 요청 본문으로 세션 생성 테스트 (기본값 사용)
        """
        sample_session.title = "새 대화"
        mock_conversation_service.create_session.return_value = sample_session
        
        # 빈 JSON 객체 전송
        response = client.post(
            "/api/sessions",
            json={}
        )
        
        assert response.status_code == 201
    
    def test_create_session_service_error(self, client, mock_conversation_service):
        """
        서비스 오류 시 500 응답 테스트
        """
        mock_conversation_service.create_session.side_effect = ConversationServiceError(
            message="데이터베이스 오류"
        )
        
        response = client.post(
            "/api/sessions",
            json={"title": "테스트"}
        )
        
        assert response.status_code == 500
        data = response.json()
        # HTTPException은 detail 키 아래에 오류 정보를 포함
        assert "detail" in data
        assert "error" in data["detail"]
        assert data["detail"]["error"]["code"] == "INTERNAL_ERROR"


# =============================================================================
# GET /api/sessions 테스트 - 모든 세션 나열
# =============================================================================

class TestListSessions:
    """
    GET /api/sessions 엔드포인트 테스트
    
    요구사항: 3.2
    """
    
    def test_list_sessions_success(self, client, mock_conversation_service, sample_session):
        """
        세션 목록 조회 성공 테스트
        """
        mock_conversation_service.list_sessions.return_value = [sample_session]
        
        response = client.get("/api/sessions")
        
        assert response.status_code == 200
        data = response.json()
        assert "sessions" in data
        assert "total_count" in data
        assert data["total_count"] == 1
        assert len(data["sessions"]) == 1
        assert data["sessions"][0]["id"] == "test-session-123"
    
    def test_list_sessions_empty(self, client, mock_conversation_service):
        """
        빈 세션 목록 조회 테스트
        """
        mock_conversation_service.list_sessions.return_value = []
        
        response = client.get("/api/sessions")
        
        assert response.status_code == 200
        data = response.json()
        assert data["sessions"] == []
        assert data["total_count"] == 0
    
    def test_list_sessions_multiple(self, client, mock_conversation_service):
        """
        여러 세션 목록 조회 테스트
        """
        sessions = [
            SessionResponse(
                id=f"session-{i}",
                title=f"세션 {i}",
                created_at="2024-01-15T10:00:00",
                last_message_at="2024-01-15T10:00:00"
            )
            for i in range(3)
        ]
        mock_conversation_service.list_sessions.return_value = sessions
        
        response = client.get("/api/sessions")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 3
        assert len(data["sessions"]) == 3
    
    def test_list_sessions_service_error(self, client, mock_conversation_service):
        """
        서비스 오류 시 500 응답 테스트
        """
        mock_conversation_service.list_sessions.side_effect = ConversationServiceError(
            message="데이터베이스 오류"
        )
        
        response = client.get("/api/sessions")
        
        assert response.status_code == 500
        data = response.json()
        # HTTPException은 detail 키 아래에 오류 정보를 포함
        assert "detail" in data
        assert "error" in data["detail"]
        assert data["detail"]["error"]["code"] == "INTERNAL_ERROR"


# =============================================================================
# GET /api/sessions/{session_id}/messages 테스트 - 세션 기록 가져오기
# =============================================================================

class TestGetMessageHistory:
    """
    GET /api/sessions/{session_id}/messages 엔드포인트 테스트
    
    요구사항: 3.3
    """
    
    def test_get_message_history_success(self, client, mock_conversation_service, sample_message):
        """
        메시지 기록 조회 성공 테스트
        """
        mock_conversation_service.get_history.return_value = [sample_message]
        
        response = client.get("/api/sessions/test-session-123/messages")
        
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == "test-session-123"
        assert data["total_count"] == 1
        assert len(data["messages"]) == 1
        assert data["messages"][0]["content"] == "테스트 응답입니다."
    
    def test_get_message_history_empty(self, client, mock_conversation_service):
        """
        빈 메시지 기록 조회 테스트
        """
        mock_conversation_service.get_history.return_value = []
        
        response = client.get("/api/sessions/test-session-123/messages")
        
        assert response.status_code == 200
        data = response.json()
        assert data["messages"] == []
        assert data["total_count"] == 0
    
    def test_get_message_history_session_not_found(self, client, mock_conversation_service):
        """
        존재하지 않는 세션 조회 시 404 응답 테스트
        """
        mock_conversation_service.get_history.side_effect = SessionNotFoundError(
            session_id="nonexistent-session"
        )
        
        response = client.get("/api/sessions/nonexistent-session/messages")
        
        assert response.status_code == 404
        data = response.json()
        # HTTPException은 detail 키 아래에 오류 정보를 포함
        assert "detail" in data
        assert "error" in data["detail"]
        assert data["detail"]["error"]["code"] == "SESSION_NOT_FOUND"
    
    def test_get_message_history_service_error(self, client, mock_conversation_service):
        """
        서비스 오류 시 500 응답 테스트
        """
        mock_conversation_service.get_history.side_effect = ConversationServiceError(
            message="데이터베이스 오류"
        )
        
        response = client.get("/api/sessions/test-session-123/messages")
        
        assert response.status_code == 500
        data = response.json()
        # HTTPException은 detail 키 아래에 오류 정보를 포함
        assert "detail" in data
        assert "error" in data["detail"]
        assert data["detail"]["error"]["code"] == "INTERNAL_ERROR"


# =============================================================================
# POST /api/sessions/{session_id}/messages 테스트 - 메시지 전송
# =============================================================================

class TestSendMessage:
    """
    POST /api/sessions/{session_id}/messages 엔드포인트 테스트
    
    요구사항: 2.3, 4.3
    """
    
    def test_send_message_success(self, client, mock_conversation_service, sample_message):
        """
        메시지 전송 성공 테스트
        """
        # AsyncMock 사용하여 비동기 메서드 모킹
        mock_conversation_service.send_message = AsyncMock(return_value=sample_message)
        
        response = client.post(
            "/api/sessions/test-session-123/messages",
            json={"content": "CPU 사용률을 확인해주세요"}
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["id"] == "test-message-123"
        assert data["role"] == "assistant"
        assert data["content"] == "테스트 응답입니다."
    
    def test_send_message_empty_content(self, client, mock_conversation_service):
        """
        빈 메시지 전송 시 400 응답 테스트
        """
        response = client.post(
            "/api/sessions/test-session-123/messages",
            json={"content": ""}
        )
        
        # Pydantic 검증에서 min_length=1로 인해 422 또는 400 반환
        assert response.status_code in [400, 422]
    
    def test_send_message_whitespace_only(self, client, mock_conversation_service):
        """
        공백만 있는 메시지 전송 시 400 응답 테스트
        """
        response = client.post(
            "/api/sessions/test-session-123/messages",
            json={"content": "   "}
        )
        
        assert response.status_code == 400
        data = response.json()
        # HTTPException은 detail 키 아래에 오류 정보를 포함
        assert "detail" in data
        assert "error" in data["detail"]
        assert data["detail"]["error"]["code"] == "VALIDATION_ERROR"
    
    def test_send_message_session_not_found(self, client, mock_conversation_service):
        """
        존재하지 않는 세션에 메시지 전송 시 404 응답 테스트
        """
        mock_conversation_service.send_message = AsyncMock(
            side_effect=SessionNotFoundError(session_id="nonexistent-session")
        )
        
        response = client.post(
            "/api/sessions/nonexistent-session/messages",
            json={"content": "테스트 메시지"}
        )
        
        assert response.status_code == 404
        data = response.json()
        # HTTPException은 detail 키 아래에 오류 정보를 포함
        assert "detail" in data
        assert "error" in data["detail"]
        assert data["detail"]["error"]["code"] == "SESSION_NOT_FOUND"
    
    def test_send_message_ai_response_error(self, client, mock_conversation_service):
        """
        AI 응답 생성 실패 시 500 응답 테스트
        """
        mock_conversation_service.send_message = AsyncMock(
            side_effect=AIResponseError(message="Bedrock API 오류")
        )
        
        response = client.post(
            "/api/sessions/test-session-123/messages",
            json={"content": "테스트 메시지"}
        )
        
        assert response.status_code == 500
        data = response.json()
        # HTTPException은 detail 키 아래에 오류 정보를 포함
        assert "detail" in data
        assert "error" in data["detail"]
        assert data["detail"]["error"]["code"] == "AI_RESPONSE_ERROR"
    
    def test_send_message_processing_error(self, client, mock_conversation_service):
        """
        메시지 처리 오류 시 500 응답 테스트
        """
        mock_conversation_service.send_message = AsyncMock(
            side_effect=MessageProcessingError(message="처리 오류")
        )
        
        response = client.post(
            "/api/sessions/test-session-123/messages",
            json={"content": "테스트 메시지"}
        )
        
        assert response.status_code == 500
        data = response.json()
        # HTTPException은 detail 키 아래에 오류 정보를 포함
        assert "detail" in data
        assert "error" in data["detail"]
        assert data["detail"]["error"]["code"] == "MESSAGE_PROCESSING_ERROR"
    
    def test_send_message_missing_content(self, client, mock_conversation_service):
        """
        content 필드 누락 시 422 응답 테스트
        """
        response = client.post(
            "/api/sessions/test-session-123/messages",
            json={}
        )
        
        assert response.status_code == 422  # Pydantic 검증 실패


# =============================================================================
# 오류 응답 형식 테스트
# =============================================================================

class TestErrorResponseFormat:
    """
    오류 응답 형식 테스트
    
    모든 오류 응답이 일관된 형식을 따르는지 확인합니다.
    """
    
    def test_error_response_has_error_key(self, client, mock_conversation_service):
        """
        오류 응답에 'error' 키가 있는지 테스트
        """
        mock_conversation_service.get_history.side_effect = SessionNotFoundError(
            session_id="test"
        )
        
        response = client.get("/api/sessions/test/messages")
        
        assert response.status_code == 404
        data = response.json()
        # HTTPException은 detail 키 아래에 오류 정보를 포함
        assert "detail" in data
        assert "error" in data["detail"]
        assert "code" in data["detail"]["error"]
        assert "message" in data["detail"]["error"]
    
    def test_error_response_has_code_and_message(self, client, mock_conversation_service):
        """
        오류 응답에 code와 message가 있는지 테스트
        """
        mock_conversation_service.list_sessions.side_effect = ConversationServiceError(
            message="테스트 오류"
        )
        
        response = client.get("/api/sessions")
        
        assert response.status_code == 500
        data = response.json()
        # HTTPException은 detail 키 아래에 오류 정보를 포함
        assert "detail" in data
        assert isinstance(data["detail"]["error"]["code"], str)
        assert isinstance(data["detail"]["error"]["message"], str)
        assert len(data["detail"]["error"]["code"]) > 0
        assert len(data["detail"]["error"]["message"]) > 0


# =============================================================================
# 의존성 주입 테스트
# =============================================================================

class TestDependencyInjection:
    """
    의존성 주입 테스트
    """
    
    def test_service_not_initialized(self):
        """
        서비스가 초기화되지 않은 경우 503 응답 테스트
        """
        # 새로운 앱 생성 (서비스 설정 없이)
        from routes import sessions_router
        import routes
        
        # 전역 서비스를 None으로 설정
        original_service = routes._conversation_service
        routes._conversation_service = None
        
        try:
            app = FastAPI()
            app.include_router(sessions_router, prefix="/api")
            client = TestClient(app)
            
            response = client.get("/api/sessions")
            
            assert response.status_code == 503
            data = response.json()
            assert "error" in data["detail"]
            assert data["detail"]["error"]["code"] == "SERVICE_UNAVAILABLE"
        finally:
            # 원래 서비스 복원
            routes._conversation_service = original_service


# =============================================================================
# 헬스 체크 엔드포인트 테스트
# =============================================================================

class TestHealthCheck:
    """
    GET /health 엔드포인트 테스트
    
    요구사항: 10.5
    """
    
    @pytest.fixture
    def health_check_app(self):
        """
        헬스 체크 테스트용 FastAPI 앱을 생성합니다.
        """
        from app import app
        return app
    
    @pytest.fixture
    def health_client(self, health_check_app):
        """
        헬스 체크 테스트 클라이언트를 생성합니다.
        """
        return TestClient(health_check_app)
    
    def test_health_check_returns_200(self, health_client):
        """
        헬스 체크 엔드포인트가 200 상태 코드를 반환하는지 테스트
        """
        response = health_client.get("/health")
        
        assert response.status_code == 200
    
    def test_health_check_response_structure(self, health_client):
        """
        헬스 체크 응답 구조가 올바른지 테스트
        """
        response = health_client.get("/health")
        data = response.json()
        
        # 필수 필드 확인
        assert "status" in data
        assert "service" in data
        assert "version" in data
        assert "timestamp" in data
        assert "components" in data
        
        # 상태 값 확인
        assert data["status"] in ["healthy", "unhealthy", "degraded"]
        assert data["service"] == "ai-chatbot-backend"
        assert isinstance(data["version"], str)
        assert isinstance(data["timestamp"], str)
        assert isinstance(data["components"], list)
    
    def test_health_check_has_api_component(self, health_client):
        """
        헬스 체크 응답에 API 구성 요소가 포함되어 있는지 테스트
        """
        response = health_client.get("/health")
        data = response.json()
        
        # API 구성 요소 확인
        api_component = next(
            (c for c in data["components"] if c["name"] == "api"),
            None
        )
        
        assert api_component is not None
        assert api_component["status"] == "healthy"
    
    def test_health_check_has_database_component(self, health_client):
        """
        헬스 체크 응답에 데이터베이스 구성 요소가 포함되어 있는지 테스트
        """
        response = health_client.get("/health")
        data = response.json()
        
        # 데이터베이스 구성 요소 확인
        db_component = next(
            (c for c in data["components"] if c["name"] == "database"),
            None
        )
        
        assert db_component is not None
        assert db_component["status"] in ["healthy", "unhealthy"]
        assert "message" in db_component
    
    def test_health_check_has_mcp_components(self, health_client):
        """
        헬스 체크 응답에 MCP 구성 요소가 포함되어 있는지 테스트
        """
        response = health_client.get("/health")
        data = response.json()
        
        # MCP Grafana 구성 요소 확인
        grafana_component = next(
            (c for c in data["components"] if c["name"] == "mcp_grafana"),
            None
        )
        
        assert grafana_component is not None
        assert grafana_component["status"] in ["healthy", "unhealthy", "unknown"]
        
        # MCP CloudWatch 구성 요소 확인
        cloudwatch_component = next(
            (c for c in data["components"] if c["name"] == "mcp_cloudwatch"),
            None
        )
        
        assert cloudwatch_component is not None
        assert cloudwatch_component["status"] in ["healthy", "unhealthy", "unknown"]
    
    def test_health_check_has_bedrock_component(self, health_client):
        """
        헬스 체크 응답에 Bedrock 구성 요소가 포함되어 있는지 테스트
        """
        response = health_client.get("/health")
        data = response.json()
        
        # Bedrock 구성 요소 확인
        bedrock_component = next(
            (c for c in data["components"] if c["name"] == "bedrock"),
            None
        )
        
        assert bedrock_component is not None
        assert bedrock_component["status"] in ["healthy", "unhealthy", "unknown"]
    
    def test_health_check_component_structure(self, health_client):
        """
        각 구성 요소의 구조가 올바른지 테스트
        """
        response = health_client.get("/health")
        data = response.json()
        
        for component in data["components"]:
            assert "name" in component
            assert "status" in component
            assert component["status"] in ["healthy", "unhealthy", "unknown"]
            # message는 선택적이지만 존재하면 문자열이어야 함
            if "message" in component and component["message"] is not None:
                assert isinstance(component["message"], str)
