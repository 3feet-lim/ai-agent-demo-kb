"""
API 라우트 - 세션 및 메시지 엔드포인트

이 모듈은 대화 세션 및 메시지 관리를 위한 REST API 엔드포인트를 정의합니다.
FastAPI의 APIRouter를 사용하여 /api 프리픽스 아래에 엔드포인트를 구성합니다.

주요 엔드포인트:
- POST /api/sessions - 새 세션 생성
- GET /api/sessions - 모든 세션 나열
- GET /api/sessions/{session_id}/messages - 세션 기록 가져오기
- POST /api/sessions/{session_id}/messages - 메시지 전송

요구사항: 2.3, 3.1, 3.2, 3.3, 4.3
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.responses import JSONResponse

from models import (
    MessageRequest,
    MessageResponse,
    SessionCreate,
    SessionResponse,
    SessionListResponse,
    MessageHistoryResponse,
    ErrorResponse,
    create_error_response
)
from conversation_service import (
    ConversationService,
    SessionNotFoundError,
    MessageProcessingError,
    AIResponseError,
    ConversationServiceError
)
from database import Database
from llm_chain import LLMChainBuilder
from mcp_manager import MCPServerManager

# 로거 설정
logger = logging.getLogger(__name__)


# =============================================================================
# API 라우터 생성
# =============================================================================

# 세션 관련 라우터
sessions_router = APIRouter(
    prefix="/sessions",
    tags=["sessions"],
    responses={
        400: {"model": ErrorResponse, "description": "잘못된 요청"},
        404: {"model": ErrorResponse, "description": "리소스를 찾을 수 없음"},
        500: {"model": ErrorResponse, "description": "서버 내부 오류"}
    }
)


# =============================================================================
# 의존성 주입을 위한 전역 변수 및 함수
# =============================================================================

# 전역 서비스 인스턴스 (애플리케이션 시작 시 초기화됨)
_conversation_service: Optional[ConversationService] = None


def set_conversation_service(service: ConversationService) -> None:
    """
    ConversationService 인스턴스를 설정합니다.
    
    애플리케이션 시작 시 호출되어 의존성 주입에 사용됩니다.
    
    Args:
        service: ConversationService 인스턴스
    """
    global _conversation_service
    _conversation_service = service
    logger.info("ConversationService 설정 완료")


def get_conversation_service() -> ConversationService:
    """
    ConversationService 인스턴스를 반환하는 의존성 함수
    
    FastAPI의 Depends를 통해 엔드포인트에 주입됩니다.
    
    Returns:
        ConversationService: 대화 서비스 인스턴스
    
    Raises:
        HTTPException: 서비스가 초기화되지 않은 경우
    """
    if _conversation_service is None:
        logger.error("ConversationService가 초기화되지 않았습니다")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": {
                    "code": "SERVICE_UNAVAILABLE",
                    "message": "서비스가 아직 초기화되지 않았습니다. 잠시 후 다시 시도해주세요."
                }
            }
        )
    return _conversation_service


# =============================================================================
# 오류 응답 헬퍼 함수
# =============================================================================

def create_http_error_response(
    status_code: int,
    code: str,
    message: str,
    details: Optional[list] = None
) -> JSONResponse:
    """
    HTTP 오류 응답을 생성합니다.
    
    Args:
        status_code: HTTP 상태 코드
        code: 오류 코드
        message: 오류 메시지
        details: 추가 오류 정보 (선택사항)
    
    Returns:
        JSONResponse: 오류 응답
    """
    error_data = {
        "error": {
            "code": code,
            "message": message
        }
    }
    
    if details:
        error_data["error"]["details"] = details
    
    return JSONResponse(
        status_code=status_code,
        content=error_data
    )


# =============================================================================
# 세션 엔드포인트
# =============================================================================

@sessions_router.post(
    "",
    response_model=SessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="새 세션 생성",
    description="새로운 대화 세션을 생성합니다. 제목은 선택사항이며, 제공되지 않으면 '새 대화'가 기본값으로 사용됩니다.",
    responses={
        201: {
            "description": "세션 생성 성공",
            "content": {
                "application/json": {
                    "example": {
                        "id": "123e4567-e89b-12d3-a456-426614174000",
                        "title": "인프라 분석",
                        "created_at": "2024-01-15T10:00:00",
                        "last_message_at": "2024-01-15T10:00:00"
                    }
                }
            }
        },
        500: {
            "description": "서버 내부 오류",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "INTERNAL_ERROR",
                            "message": "세션 생성 중 오류가 발생했습니다."
                        }
                    }
                }
            }
        }
    }
)
async def create_session(
    request: SessionCreate = SessionCreate(),
    service: ConversationService = Depends(get_conversation_service)
) -> SessionResponse:
    """
    새 대화 세션을 생성합니다.
    
    Args:
        request: 세션 생성 요청 (제목 포함)
        service: ConversationService 인스턴스 (의존성 주입)
    
    Returns:
        SessionResponse: 생성된 세션 정보
    
    Raises:
        HTTPException: 세션 생성 실패 시
    
    요구사항: 3.1
    """
    logger.info(f"세션 생성 요청: title={request.title}")
    
    try:
        session = service.create_session(title=request.title or "새 대화")
        logger.info(f"세션 생성 완료: session_id={session.id}")
        return session
        
    except ConversationServiceError as e:
        logger.error(f"세션 생성 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "세션 생성 중 오류가 발생했습니다."
                }
            }
        )
    except Exception as e:
        logger.error(f"세션 생성 중 예기치 않은 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "세션 생성 중 예기치 않은 오류가 발생했습니다."
                }
            }
        )


@sessions_router.get(
    "",
    response_model=SessionListResponse,
    summary="모든 세션 나열",
    description="모든 대화 세션 목록을 반환합니다. 세션은 마지막 메시지 시간 기준 내림차순으로 정렬됩니다.",
    responses={
        200: {
            "description": "세션 목록 조회 성공",
            "content": {
                "application/json": {
                    "example": {
                        "sessions": [
                            {
                                "id": "session-1",
                                "title": "인프라 분석",
                                "created_at": "2024-01-15T10:00:00",
                                "last_message_at": "2024-01-15T10:30:00"
                            }
                        ],
                        "total_count": 1
                    }
                }
            }
        },
        500: {
            "description": "서버 내부 오류"
        }
    }
)
async def list_sessions(
    service: ConversationService = Depends(get_conversation_service)
) -> SessionListResponse:
    """
    모든 대화 세션 목록을 조회합니다.
    
    Args:
        service: ConversationService 인스턴스 (의존성 주입)
    
    Returns:
        SessionListResponse: 세션 목록 및 총 개수
    
    Raises:
        HTTPException: 세션 목록 조회 실패 시
    
    요구사항: 3.2
    """
    logger.info("세션 목록 조회 요청")
    
    try:
        sessions = service.list_sessions()
        
        response = SessionListResponse(
            sessions=sessions,
            total_count=len(sessions)
        )
        
        logger.info(f"세션 목록 조회 완료: {len(sessions)}개 세션")
        return response
        
    except ConversationServiceError as e:
        logger.error(f"세션 목록 조회 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "세션 목록 조회 중 오류가 발생했습니다."
                }
            }
        )
    except Exception as e:
        logger.error(f"세션 목록 조회 중 예기치 않은 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "세션 목록 조회 중 예기치 않은 오류가 발생했습니다."
                }
            }
        )


# =============================================================================
# 메시지 엔드포인트
# =============================================================================

@sessions_router.get(
    "/{session_id}/messages",
    response_model=MessageHistoryResponse,
    summary="세션 기록 가져오기",
    description="특정 세션의 전체 메시지 기록을 반환합니다. 메시지는 시간순으로 정렬됩니다.",
    responses={
        200: {
            "description": "메시지 기록 조회 성공",
            "content": {
                "application/json": {
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
            }
        },
        404: {
            "description": "세션을 찾을 수 없음",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "SESSION_NOT_FOUND",
                            "message": "세션을 찾을 수 없습니다: session-123"
                        }
                    }
                }
            }
        },
        500: {
            "description": "서버 내부 오류"
        }
    }
)
async def get_message_history(
    session_id: str,
    service: ConversationService = Depends(get_conversation_service)
) -> MessageHistoryResponse:
    """
    특정 세션의 메시지 기록을 조회합니다.
    
    Args:
        session_id: 세션 ID
        service: ConversationService 인스턴스 (의존성 주입)
    
    Returns:
        MessageHistoryResponse: 메시지 목록 및 총 개수
    
    Raises:
        HTTPException: 세션을 찾을 수 없거나 조회 실패 시
    
    요구사항: 3.3, 7.3
    """
    logger.info(f"메시지 기록 조회 요청: session_id={session_id}")
    
    try:
        messages = service.get_history(session_id)
        
        response = MessageHistoryResponse(
            session_id=session_id,
            messages=messages,
            total_count=len(messages)
        )
        
        logger.info(f"메시지 기록 조회 완료: {len(messages)}개 메시지")
        return response
        
    except SessionNotFoundError as e:
        logger.warning(f"세션을 찾을 수 없음: {session_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "SESSION_NOT_FOUND",
                    "message": f"세션을 찾을 수 없습니다: {session_id}"
                }
            }
        )
    except ConversationServiceError as e:
        logger.error(f"메시지 기록 조회 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "메시지 기록 조회 중 오류가 발생했습니다."
                }
            }
        )
    except Exception as e:
        logger.error(f"메시지 기록 조회 중 예기치 않은 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "메시지 기록 조회 중 예기치 않은 오류가 발생했습니다."
                }
            }
        )


@sessions_router.post(
    "/{session_id}/messages",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="메시지 전송",
    description="특정 세션에 메시지를 전송하고 AI 응답을 받습니다.",
    responses={
        201: {
            "description": "메시지 전송 및 AI 응답 성공",
            "content": {
                "application/json": {
                    "example": {
                        "id": "msg-2",
                        "session_id": "session-123",
                        "content": "현재 CPU 사용률은 45%입니다.",
                        "role": "assistant",
                        "timestamp": "2024-01-15T10:30:05"
                    }
                }
            }
        },
        400: {
            "description": "잘못된 요청 (빈 메시지 등)",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "VALIDATION_ERROR",
                            "message": "메시지 내용이 비어있습니다.",
                            "details": [
                                {"field": "content", "message": "필수 필드입니다"}
                            ]
                        }
                    }
                }
            }
        },
        404: {
            "description": "세션을 찾을 수 없음"
        },
        500: {
            "description": "서버 내부 오류 (AI 응답 생성 실패 등)"
        }
    }
)
async def send_message(
    session_id: str,
    request: MessageRequest,
    service: ConversationService = Depends(get_conversation_service)
) -> MessageResponse:
    """
    특정 세션에 메시지를 전송하고 AI 응답을 받습니다.
    
    이 엔드포인트는 다음 단계를 수행합니다:
    1. 사용자 메시지를 데이터베이스에 저장
    2. LLM 에이전트를 호출하여 AI 응답 생성
    3. AI 응답을 데이터베이스에 저장
    4. AI 응답 반환
    
    Args:
        session_id: 세션 ID
        request: 메시지 요청 (내용 포함)
        service: ConversationService 인스턴스 (의존성 주입)
    
    Returns:
        MessageResponse: AI 응답 메시지
    
    Raises:
        HTTPException: 세션을 찾을 수 없거나 메시지 처리 실패 시
    
    요구사항: 2.3, 4.3
    """
    logger.info(f"메시지 전송 요청: session_id={session_id}, content_length={len(request.content)}")
    
    # 메시지 내용 검증 (Pydantic에서 기본 검증하지만 추가 검증)
    if not request.content or not request.content.strip():
        logger.warning("빈 메시지 전송 시도")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "메시지 내용이 비어있습니다.",
                    "details": [
                        {"field": "content", "message": "메시지 내용은 필수입니다."}
                    ]
                }
            }
        )
    
    try:
        # 메시지 전송 및 AI 응답 생성
        response = await service.send_message(
            session_id=session_id,
            content=request.content.strip()
        )
        
        logger.info(f"메시지 전송 완료: message_id={response.id}")
        return response
        
    except SessionNotFoundError as e:
        logger.warning(f"세션을 찾을 수 없음: {session_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "SESSION_NOT_FOUND",
                    "message": f"세션을 찾을 수 없습니다: {session_id}"
                }
            }
        )
    except AIResponseError as e:
        logger.error(f"AI 응답 생성 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "AI_RESPONSE_ERROR",
                    "message": "AI 응답 생성 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요."
                }
            }
        )
    except MessageProcessingError as e:
        logger.error(f"메시지 처리 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "MESSAGE_PROCESSING_ERROR",
                    "message": "메시지 처리 중 오류가 발생했습니다."
                }
            }
        )
    except ConversationServiceError as e:
        logger.error(f"대화 서비스 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "메시지 처리 중 오류가 발생했습니다."
                }
            }
        )
    except Exception as e:
        logger.error(f"메시지 전송 중 예기치 않은 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "메시지 처리 중 예기치 않은 오류가 발생했습니다."
                }
            }
        )


# =============================================================================
# 라우터 등록 함수
# =============================================================================

def register_routes(app) -> None:
    """
    모든 API 라우트를 FastAPI 앱에 등록합니다.
    
    Args:
        app: FastAPI 애플리케이션 인스턴스
    """
    # /api/sessions 라우터 등록
    app.include_router(sessions_router, prefix="/api")
    logger.info("API 라우트 등록 완료: /api/sessions")
