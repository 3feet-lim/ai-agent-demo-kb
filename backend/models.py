"""
API 데이터 모델 - Pydantic 모델 정의

이 모듈은 API 요청 및 응답을 위한 Pydantic 모델을 정의합니다.
모든 모델은 타입 검증 및 직렬화를 지원합니다.

주요 모델:
- MessageRequest: 사용자 메시지 입력
- MessageResponse: AI 응답 출력
- SessionCreate: 새 세션 생성 요청
- SessionResponse: 세션 정보 응답
- SessionListResponse: 세션 목록 응답
- MessageHistoryResponse: 대화 기록 응답
- HealthCheckResponse: 헬스 체크 응답

요구사항: 4.1
"""

from datetime import datetime
from typing import List, Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


# =============================================================================
# 메시지 관련 모델
# =============================================================================

class MessageRequest(BaseModel):
    """
    사용자 메시지 입력 모델
    
    사용자가 채팅 인터페이스를 통해 전송하는 메시지를 나타냅니다.
    
    Attributes:
        content: 메시지 내용 (필수, 최소 1자)
    
    Example:
        >>> request = MessageRequest(content="CPU 사용률을 확인해주세요")
    
    요구사항: 2.3, 4.3
    """
    
    content: str = Field(
        ...,
        description="메시지 내용",
        min_length=1,
        max_length=10000,
        examples=["CPU 사용률을 확인해주세요", "최근 1시간 동안의 메모리 사용량을 분석해주세요"]
    )


class MessageResponse(BaseModel):
    """
    메시지 응답 모델
    
    저장된 메시지 또는 AI 응답을 나타냅니다.
    사용자 메시지와 어시스턴트 응답 모두에 사용됩니다.
    
    Attributes:
        id: 메시지 고유 식별자 (UUID)
        session_id: 세션 식별자
        content: 메시지 내용
        role: 발신자 유형 ('user' 또는 'assistant')
        timestamp: 메시지 생성 시간 (ISO 8601 형식)
    
    Example:
        >>> response = MessageResponse(
        ...     id="123e4567-e89b-12d3-a456-426614174000",
        ...     session_id="session-123",
        ...     content="현재 CPU 사용률은 45%입니다.",
        ...     role="assistant",
        ...     timestamp="2024-01-15T10:30:00"
        ... )
    
    요구사항: 2.3, 4.3, 7.4
    """
    
    id: str = Field(
        ...,
        description="메시지 고유 식별자 (UUID)",
        examples=["123e4567-e89b-12d3-a456-426614174000"]
    )
    
    session_id: str = Field(
        ...,
        description="세션 식별자",
        examples=["session-123"]
    )
    
    content: str = Field(
        ...,
        description="메시지 내용",
        examples=["현재 CPU 사용률은 45%입니다."]
    )
    
    role: Literal["user", "assistant"] = Field(
        ...,
        description="발신자 유형 ('user' 또는 'assistant')",
        examples=["assistant"]
    )
    
    timestamp: str = Field(
        ...,
        description="메시지 생성 시간 (ISO 8601 형식)",
        examples=["2024-01-15T10:30:00"]
    )
    
    class Config:
        """Pydantic 모델 구성"""
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "session_id": "session-123",
                "content": "현재 CPU 사용률은 45%입니다.",
                "role": "assistant",
                "timestamp": "2024-01-15T10:30:00"
            }
        }


class MessageHistoryResponse(BaseModel):
    """
    대화 기록 응답 모델
    
    특정 세션의 전체 메시지 기록을 반환합니다.
    메시지는 시간순으로 정렬됩니다.
    
    Attributes:
        session_id: 세션 식별자
        messages: 메시지 목록 (시간순 정렬)
        total_count: 총 메시지 수
    
    Example:
        >>> history = MessageHistoryResponse(
        ...     session_id="session-123",
        ...     messages=[...],
        ...     total_count=10
        ... )
    
    요구사항: 3.3, 7.3
    """
    
    session_id: str = Field(
        ...,
        description="세션 식별자",
        examples=["session-123"]
    )
    
    messages: List[MessageResponse] = Field(
        default_factory=list,
        description="메시지 목록 (시간순 정렬)"
    )
    
    total_count: int = Field(
        ...,
        description="총 메시지 수",
        ge=0,
        examples=[10]
    )
    
    class Config:
        """Pydantic 모델 구성"""
        json_schema_extra = {
            "example": {
                "session_id": "session-123",
                "messages": [
                    {
                        "id": "msg-1",
                        "session_id": "session-123",
                        "content": "CPU 사용률을 확인해주세요",
                        "role": "user",
                        "timestamp": "2024-01-15T10:30:00"
                    },
                    {
                        "id": "msg-2",
                        "session_id": "session-123",
                        "content": "현재 CPU 사용률은 45%입니다.",
                        "role": "assistant",
                        "timestamp": "2024-01-15T10:30:05"
                    }
                ],
                "total_count": 2
            }
        }


# =============================================================================
# 세션 관련 모델
# =============================================================================

class SessionCreate(BaseModel):
    """
    새 세션 생성 요청 모델
    
    새로운 대화 세션을 생성할 때 사용됩니다.
    제목은 선택사항이며, 제공되지 않으면 기본값이 사용됩니다.
    
    Attributes:
        title: 세션 제목 (선택사항, 기본값: "새 대화")
    
    Example:
        >>> create_request = SessionCreate(title="인프라 분석")
        >>> create_request_default = SessionCreate()  # title="새 대화"
    
    요구사항: 3.1
    """
    
    title: Optional[str] = Field(
        default="새 대화",
        description="세션 제목 (선택사항)",
        min_length=1,
        max_length=200,
        examples=["인프라 분석", "CPU 모니터링", "새 대화"]
    )


class SessionResponse(BaseModel):
    """
    세션 정보 응답 모델
    
    세션의 상세 정보를 반환합니다.
    
    Attributes:
        id: 세션 고유 식별자 (UUID)
        title: 세션 제목
        created_at: 세션 생성 시간 (ISO 8601 형식)
        last_message_at: 마지막 메시지 시간 (ISO 8601 형식)
    
    Example:
        >>> session = SessionResponse(
        ...     id="session-123",
        ...     title="인프라 분석",
        ...     created_at="2024-01-15T10:00:00",
        ...     last_message_at="2024-01-15T10:30:00"
        ... )
    
    요구사항: 3.1, 3.5
    """
    
    id: str = Field(
        ...,
        description="세션 고유 식별자 (UUID)",
        examples=["123e4567-e89b-12d3-a456-426614174000"]
    )
    
    title: str = Field(
        ...,
        description="세션 제목",
        examples=["인프라 분석"]
    )
    
    created_at: str = Field(
        ...,
        description="세션 생성 시간 (ISO 8601 형식)",
        examples=["2024-01-15T10:00:00"]
    )
    
    last_message_at: str = Field(
        ...,
        description="마지막 메시지 시간 (ISO 8601 형식)",
        examples=["2024-01-15T10:30:00"]
    )
    
    class Config:
        """Pydantic 모델 구성"""
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "title": "인프라 분석",
                "created_at": "2024-01-15T10:00:00",
                "last_message_at": "2024-01-15T10:30:00"
            }
        }


class SessionListResponse(BaseModel):
    """
    세션 목록 응답 모델
    
    모든 세션의 목록을 반환합니다.
    세션은 마지막 메시지 시간 기준 내림차순으로 정렬됩니다.
    
    Attributes:
        sessions: 세션 목록 (최근 메시지 순 정렬)
        total_count: 총 세션 수
    
    Example:
        >>> session_list = SessionListResponse(
        ...     sessions=[...],
        ...     total_count=5
        ... )
    
    요구사항: 3.2, 3.5
    """
    
    sessions: List[SessionResponse] = Field(
        default_factory=list,
        description="세션 목록 (최근 메시지 순 정렬)"
    )
    
    total_count: int = Field(
        ...,
        description="총 세션 수",
        ge=0,
        examples=[5]
    )
    
    class Config:
        """Pydantic 모델 구성"""
        json_schema_extra = {
            "example": {
                "sessions": [
                    {
                        "id": "session-1",
                        "title": "인프라 분석",
                        "created_at": "2024-01-15T10:00:00",
                        "last_message_at": "2024-01-15T10:30:00"
                    },
                    {
                        "id": "session-2",
                        "title": "CPU 모니터링",
                        "created_at": "2024-01-14T09:00:00",
                        "last_message_at": "2024-01-14T09:45:00"
                    }
                ],
                "total_count": 2
            }
        }


# =============================================================================
# 헬스 체크 관련 모델
# =============================================================================

class ServiceStatus(BaseModel):
    """
    개별 서비스 상태 모델
    
    시스템의 개별 구성 요소 상태를 나타냅니다.
    
    Attributes:
        name: 서비스 이름
        status: 서비스 상태 ('healthy', 'unhealthy', 'unknown')
        message: 상태 메시지 (선택사항)
    """
    
    name: str = Field(
        ...,
        description="서비스 이름",
        examples=["database", "mcp_grafana", "mcp_cloudwatch", "bedrock"]
    )
    
    status: Literal["healthy", "unhealthy", "unknown"] = Field(
        ...,
        description="서비스 상태",
        examples=["healthy"]
    )
    
    message: Optional[str] = Field(
        default=None,
        description="상태 메시지 (선택사항)",
        examples=["연결 성공", "연결 실패: 타임아웃"]
    )


class HealthCheckResponse(BaseModel):
    """
    헬스 체크 응답 모델
    
    시스템 전체의 상태 정보를 반환합니다.
    각 구성 요소(데이터베이스, MCP 서버, Bedrock 등)의 상태를 포함합니다.
    
    Attributes:
        status: 전체 시스템 상태 ('healthy', 'unhealthy', 'degraded')
        service: 서비스 이름
        version: 서비스 버전
        timestamp: 헬스 체크 시간 (ISO 8601 형식)
        components: 개별 구성 요소 상태 목록 (선택사항)
    
    Example:
        >>> health = HealthCheckResponse(
        ...     status="healthy",
        ...     service="ai-chatbot-backend",
        ...     version="0.1.0",
        ...     timestamp="2024-01-15T10:30:00"
        ... )
    
    요구사항: 10.5
    """
    
    status: Literal["healthy", "unhealthy", "degraded"] = Field(
        ...,
        description="전체 시스템 상태 ('healthy', 'unhealthy', 'degraded')",
        examples=["healthy"]
    )
    
    service: str = Field(
        default="ai-chatbot-backend",
        description="서비스 이름",
        examples=["ai-chatbot-backend"]
    )
    
    version: str = Field(
        default="0.1.0",
        description="서비스 버전",
        examples=["0.1.0"]
    )
    
    timestamp: str = Field(
        ...,
        description="헬스 체크 시간 (ISO 8601 형식)",
        examples=["2024-01-15T10:30:00"]
    )
    
    components: Optional[List[ServiceStatus]] = Field(
        default=None,
        description="개별 구성 요소 상태 목록 (선택사항)"
    )
    
    class Config:
        """Pydantic 모델 구성"""
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "service": "ai-chatbot-backend",
                "version": "0.1.0",
                "timestamp": "2024-01-15T10:30:00",
                "components": [
                    {"name": "database", "status": "healthy", "message": "연결 성공"},
                    {"name": "mcp_grafana", "status": "healthy", "message": None},
                    {"name": "mcp_cloudwatch", "status": "healthy", "message": None},
                    {"name": "bedrock", "status": "healthy", "message": None}
                ]
            }
        }


# =============================================================================
# 오류 응답 모델
# =============================================================================

class ErrorDetail(BaseModel):
    """
    오류 상세 정보 모델
    
    오류에 대한 추가 정보를 제공합니다.
    
    Attributes:
        field: 오류가 발생한 필드 (선택사항)
        message: 오류 메시지
    """
    
    field: Optional[str] = Field(
        default=None,
        description="오류가 발생한 필드 (선택사항)",
        examples=["content", "session_id"]
    )
    
    message: str = Field(
        ...,
        description="오류 메시지",
        examples=["필수 필드입니다", "유효하지 않은 형식입니다"]
    )


class ErrorResponse(BaseModel):
    """
    오류 응답 모델
    
    API 오류 발생 시 반환되는 응답 형식입니다.
    일관된 오류 응답 형식을 제공합니다.
    
    Attributes:
        error: 오류 정보
            - code: 오류 코드
            - message: 사람이 읽을 수 있는 오류 설명
            - details: 추가 오류 정보 목록 (선택사항)
    
    Example:
        >>> error = ErrorResponse(
        ...     error={
        ...         "code": "VALIDATION_ERROR",
        ...         "message": "입력 검증에 실패했습니다",
        ...         "details": [{"field": "content", "message": "필수 필드입니다"}]
        ...     }
        ... )
    """
    
    error: dict = Field(
        ...,
        description="오류 정보",
        examples=[{
            "code": "VALIDATION_ERROR",
            "message": "입력 검증에 실패했습니다",
            "details": [{"field": "content", "message": "필수 필드입니다"}]
        }]
    )
    
    class Config:
        """Pydantic 모델 구성"""
        json_schema_extra = {
            "example": {
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "입력 검증에 실패했습니다",
                    "details": [
                        {"field": "content", "message": "필수 필드입니다"}
                    ]
                }
            }
        }


# =============================================================================
# 유틸리티 함수
# =============================================================================

def create_message_response(
    message_id: str,
    session_id: str,
    content: str,
    role: Literal["user", "assistant"],
    timestamp: Optional[str] = None
) -> MessageResponse:
    """
    MessageResponse 객체를 생성하는 유틸리티 함수
    
    Args:
        message_id: 메시지 ID
        session_id: 세션 ID
        content: 메시지 내용
        role: 발신자 유형
        timestamp: 타임스탬프 (선택사항, 없으면 현재 시간)
    
    Returns:
        MessageResponse: 생성된 메시지 응답 객체
    """
    if timestamp is None:
        timestamp = datetime.utcnow().isoformat()
    
    return MessageResponse(
        id=message_id,
        session_id=session_id,
        content=content,
        role=role,
        timestamp=timestamp
    )


def create_session_response(
    session_id: str,
    title: str,
    created_at: Optional[str] = None,
    last_message_at: Optional[str] = None
) -> SessionResponse:
    """
    SessionResponse 객체를 생성하는 유틸리티 함수
    
    Args:
        session_id: 세션 ID
        title: 세션 제목
        created_at: 생성 시간 (선택사항, 없으면 현재 시간)
        last_message_at: 마지막 메시지 시간 (선택사항, 없으면 현재 시간)
    
    Returns:
        SessionResponse: 생성된 세션 응답 객체
    """
    now = datetime.utcnow().isoformat()
    
    return SessionResponse(
        id=session_id,
        title=title,
        created_at=created_at or now,
        last_message_at=last_message_at or now
    )


def create_health_check_response(
    status: Literal["healthy", "unhealthy", "degraded"],
    components: Optional[List[ServiceStatus]] = None,
    version: str = "0.1.0"
) -> HealthCheckResponse:
    """
    HealthCheckResponse 객체를 생성하는 유틸리티 함수
    
    Args:
        status: 전체 시스템 상태
        components: 개별 구성 요소 상태 목록 (선택사항)
        version: 서비스 버전
    
    Returns:
        HealthCheckResponse: 생성된 헬스 체크 응답 객체
    """
    return HealthCheckResponse(
        status=status,
        service="ai-chatbot-backend",
        version=version,
        timestamp=datetime.utcnow().isoformat(),
        components=components
    )


def create_error_response(
    code: str,
    message: str,
    details: Optional[List[dict]] = None
) -> ErrorResponse:
    """
    ErrorResponse 객체를 생성하는 유틸리티 함수
    
    Args:
        code: 오류 코드
        message: 오류 메시지
        details: 추가 오류 정보 목록 (선택사항)
    
    Returns:
        ErrorResponse: 생성된 오류 응답 객체
    """
    error_data = {
        "code": code,
        "message": message
    }
    
    if details:
        error_data["details"] = details
    
    return ErrorResponse(error=error_data)
