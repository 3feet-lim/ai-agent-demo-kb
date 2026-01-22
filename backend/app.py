"""
FastAPI 애플리케이션 - 메인 애플리케이션 인스턴스 및 설정

이 모듈은 FastAPI 애플리케이션 인스턴스를 생성하고 구성합니다.
CORS 미들웨어, 헬스 체크 엔드포인트, API 라우터를 포함합니다.

주요 기능:
- FastAPI 앱 인스턴스 생성 (제목 및 설명 포함)
- CORS 미들웨어 구성 (개발 환경용 모든 오리진 허용)
- /health 엔드포인트 (서비스 상태 반환)
- /api 라우터 프리픽스 포함
- lifespan 이벤트를 통한 시작/종료 처리

요구사항: 4.1, 8.1, 10.5
"""

import logging
import os
import sqlite3
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional, TYPE_CHECKING, List, Tuple

from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware

from models import (
    HealthCheckResponse,
    ServiceStatus,
    create_health_check_response
)
from routes import sessions_router, set_conversation_service

# 로거 설정
logger = logging.getLogger(__name__)


# =============================================================================
# 애플리케이션 메타데이터
# =============================================================================

# 서비스 버전
SERVICE_VERSION = "0.1.0"

# 서비스 이름
SERVICE_NAME = "ai-chatbot-backend"

# API 설명
API_DESCRIPTION = """
## AI 챗봇 인프라 모니터링 API

폐쇄망 환경에서 인프라 모니터링을 위한 AI 기반 챗봇 백엔드 서비스입니다.

### 주요 기능

* **대화 세션 관리**: 새 세션 생성, 세션 목록 조회, 세션 전환
* **메시지 처리**: 사용자 메시지 전송, AI 응답 수신, 대화 기록 조회
* **인프라 모니터링**: Grafana 및 CloudWatch 데이터 조회 및 분석
* **헬스 체크**: 서비스 상태 확인

### 기술 스택

* **프레임워크**: FastAPI + Python
* **AI 모델**: AWS Bedrock Claude Sonnet 4.5
* **데이터 소스**: Grafana MCP, CloudWatch MCP
* **데이터베이스**: SQLite

### 인증

현재 버전에서는 인증이 구현되지 않았습니다.
향후 버전에서 JWT 기반 인증이 추가될 예정입니다.
"""

# API 태그 정의
API_TAGS = [
    {
        "name": "health",
        "description": "서비스 상태 확인을 위한 헬스 체크 엔드포인트"
    },
    {
        "name": "sessions",
        "description": "대화 세션 관리 (생성, 조회, 삭제)"
    },
    {
        "name": "messages",
        "description": "메시지 전송 및 대화 기록 조회"
    }
]


# =============================================================================
# Lifespan 컨텍스트 매니저
# =============================================================================

# 전역 리소스 참조 (main.py에서 설정됨)
_startup_callback = None
_shutdown_callback = None

# 헬스 체크를 위한 전역 리소스 참조
_database_instance = None
_mcp_manager_instance = None
_bedrock_config = None


def set_lifespan_callbacks(startup_cb, shutdown_cb):
    """
    lifespan 콜백 함수를 설정합니다.
    
    main.py에서 호출하여 startup/shutdown 함수를 등록합니다.
    
    Args:
        startup_cb: 시작 시 호출할 비동기 함수
        shutdown_cb: 종료 시 호출할 비동기 함수
    """
    global _startup_callback, _shutdown_callback
    _startup_callback = startup_cb
    _shutdown_callback = shutdown_cb


def set_health_check_resources(database=None, mcp_manager=None, bedrock_config=None):
    """
    헬스 체크에 사용할 리소스를 설정합니다.
    
    main.py에서 호출하여 데이터베이스, MCP 매니저, Bedrock 구성을 등록합니다.
    
    Args:
        database: Database 인스턴스
        mcp_manager: MCPServerManager 인스턴스
        bedrock_config: BedrockConfig 인스턴스
    
    요구사항: 10.5
    """
    global _database_instance, _mcp_manager_instance, _bedrock_config
    _database_instance = database
    _mcp_manager_instance = mcp_manager
    _bedrock_config = bedrock_config
    logger.info("헬스 체크 리소스 설정 완료")


@asynccontextmanager
async def lifespan(app):
    """
    FastAPI 애플리케이션의 수명 주기를 관리하는 컨텍스트 매니저
    
    애플리케이션 시작 시 startup 콜백을 호출하고,
    종료 시 shutdown 콜백을 호출합니다.
    
    Args:
        app: FastAPI 애플리케이션 인스턴스
    
    Yields:
        None
    
    요구사항: 8.1
    """
    # 시작 시 실행
    if _startup_callback:
        await _startup_callback()
    else:
        logger.info(f"AI 챗봇 백엔드 서비스 시작: version={SERVICE_VERSION}")
        logger.info("API 문서: /docs, /redoc")
    
    yield
    
    # 종료 시 실행
    if _shutdown_callback:
        await _shutdown_callback()
    else:
        logger.info("AI 챗봇 백엔드 서비스 종료")


# =============================================================================
# FastAPI 애플리케이션 인스턴스 생성
# =============================================================================

app = FastAPI(
    title="AI 챗봇 인프라 모니터링 API",
    description=API_DESCRIPTION,
    version=SERVICE_VERSION,
    openapi_tags=API_TAGS,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    # 연락처 정보
    contact={
        "name": "AI 챗봇 팀",
        "email": "chatbot-team@example.com"
    },
    # 라이선스 정보
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT"
    },
    # lifespan 컨텍스트 매니저 등록
    lifespan=lifespan
)


# =============================================================================
# CORS 미들웨어 구성
# =============================================================================

# CORS 설정 - 개발 환경에서는 모든 오리진 허용
# 프로덕션 환경에서는 특정 오리진만 허용하도록 수정 필요
app.add_middleware(
    CORSMiddleware,
    # 허용할 오리진 목록 (개발 환경: 모든 오리진 허용)
    allow_origins=["*"],
    # 자격 증명(쿠키, 인증 헤더 등) 허용
    allow_credentials=True,
    # 허용할 HTTP 메서드
    allow_methods=["*"],
    # 허용할 HTTP 헤더
    allow_headers=["*"],
    # 프리플라이트 요청 캐시 시간 (초)
    max_age=600
)


# =============================================================================
# API 라우터 생성
# =============================================================================

# /api 프리픽스를 사용하는 API 라우터
api_router = APIRouter(prefix="/api")


# =============================================================================
# 헬스 체크 헬퍼 함수
# =============================================================================

def _check_database_health() -> ServiceStatus:
    """
    데이터베이스 연결 상태를 확인합니다.
    
    SQLite 데이터베이스에 연결하여 간단한 쿼리를 실행하고
    연결 상태를 반환합니다.
    
    Returns:
        ServiceStatus: 데이터베이스 상태 정보
    
    요구사항: 10.5
    """
    try:
        # 데이터베이스 인스턴스가 설정되어 있는 경우
        if _database_instance is not None:
            # 스키마 검증을 통해 데이터베이스 상태 확인
            if _database_instance.verify_schema():
                return ServiceStatus(
                    name="database",
                    status="healthy",
                    message="SQLite 데이터베이스 연결 정상"
                )
            else:
                return ServiceStatus(
                    name="database",
                    status="unhealthy",
                    message="데이터베이스 스키마 검증 실패"
                )
        
        # 데이터베이스 인스턴스가 없는 경우 직접 연결 시도
        db_path = os.environ.get("DATABASE_PATH", "chatbot.db")
        conn = sqlite3.connect(db_path, timeout=5.0)
        cursor = conn.cursor()
        
        # 간단한 쿼리 실행으로 연결 확인
        cursor.execute("SELECT 1")
        cursor.fetchone()
        
        # 테이블 존재 여부 확인
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='sessions'
        """)
        sessions_exists = cursor.fetchone() is not None
        
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='messages'
        """)
        messages_exists = cursor.fetchone() is not None
        
        conn.close()
        
        if sessions_exists and messages_exists:
            return ServiceStatus(
                name="database",
                status="healthy",
                message="SQLite 데이터베이스 연결 정상"
            )
        else:
            return ServiceStatus(
                name="database",
                status="unhealthy",
                message="필수 테이블이 존재하지 않습니다"
            )
            
    except sqlite3.Error as e:
        logger.error(f"데이터베이스 헬스 체크 실패: {e}")
        return ServiceStatus(
            name="database",
            status="unhealthy",
            message=f"데이터베이스 연결 실패: {str(e)}"
        )
    except Exception as e:
        logger.error(f"데이터베이스 헬스 체크 중 예외 발생: {e}")
        return ServiceStatus(
            name="database",
            status="unhealthy",
            message=f"예기치 않은 오류: {str(e)}"
        )


def _check_mcp_grafana_health() -> ServiceStatus:
    """
    Grafana MCP 서버 상태를 확인합니다.
    
    MCP 서버 매니저를 통해 Grafana 서버의 연결 상태를 확인합니다.
    구성되지 않은 경우 'unknown' 상태를 반환합니다.
    
    Returns:
        ServiceStatus: Grafana MCP 서버 상태 정보
    
    요구사항: 10.5
    """
    try:
        # Grafana 환경 변수 확인
        grafana_url = os.environ.get("GRAFANA_URL")
        grafana_api_key = os.environ.get("GRAFANA_API_KEY")
        
        # 구성되지 않은 경우
        if not grafana_url or not grafana_api_key:
            return ServiceStatus(
                name="mcp_grafana",
                status="unknown",
                message="Grafana MCP 서버가 구성되지 않았습니다"
            )
        
        # MCP 매니저가 설정되어 있는 경우
        if _mcp_manager_instance is not None:
            server_status = _mcp_manager_instance.get_server_status()
            
            if 'grafana' in server_status:
                grafana_info = server_status['grafana']
                if grafana_info.get('is_connected', False):
                    tool_count = grafana_info.get('tool_count', 0)
                    return ServiceStatus(
                        name="mcp_grafana",
                        status="healthy",
                        message=f"Grafana MCP 서버 연결 정상 (도구 {tool_count}개)"
                    )
                else:
                    return ServiceStatus(
                        name="mcp_grafana",
                        status="unhealthy",
                        message="Grafana MCP 서버 연결 끊김"
                    )
        
        # MCP 매니저가 없지만 구성은 있는 경우
        return ServiceStatus(
            name="mcp_grafana",
            status="unknown",
            message="Grafana MCP 서버 상태를 확인할 수 없습니다"
        )
        
    except Exception as e:
        logger.error(f"Grafana MCP 헬스 체크 중 예외 발생: {e}")
        return ServiceStatus(
            name="mcp_grafana",
            status="unhealthy",
            message=f"상태 확인 실패: {str(e)}"
        )


def _check_mcp_cloudwatch_health() -> ServiceStatus:
    """
    CloudWatch MCP 서버 상태를 확인합니다.
    
    MCP 서버 매니저를 통해 CloudWatch 서버의 연결 상태를 확인합니다.
    구성되지 않은 경우 'unknown' 상태를 반환합니다.
    
    Returns:
        ServiceStatus: CloudWatch MCP 서버 상태 정보
    
    요구사항: 10.5
    """
    try:
        # CloudWatch 환경 변수 확인
        cw_access_key = os.environ.get("CLOUDWATCH_AWS_ACCESS_KEY_ID")
        cw_secret_key = os.environ.get("CLOUDWATCH_AWS_SECRET_ACCESS_KEY")
        cw_region = os.environ.get("CLOUDWATCH_REGION")
        
        # 구성되지 않은 경우
        if not cw_access_key or not cw_secret_key or not cw_region:
            return ServiceStatus(
                name="mcp_cloudwatch",
                status="unknown",
                message="CloudWatch MCP 서버가 구성되지 않았습니다"
            )
        
        # MCP 매니저가 설정되어 있는 경우
        if _mcp_manager_instance is not None:
            server_status = _mcp_manager_instance.get_server_status()
            
            if 'cloudwatch' in server_status:
                cloudwatch_info = server_status['cloudwatch']
                if cloudwatch_info.get('is_connected', False):
                    tool_count = cloudwatch_info.get('tool_count', 0)
                    return ServiceStatus(
                        name="mcp_cloudwatch",
                        status="healthy",
                        message=f"CloudWatch MCP 서버 연결 정상 (도구 {tool_count}개)"
                    )
                else:
                    return ServiceStatus(
                        name="mcp_cloudwatch",
                        status="unhealthy",
                        message="CloudWatch MCP 서버 연결 끊김"
                    )
        
        # MCP 매니저가 없지만 구성은 있는 경우
        return ServiceStatus(
            name="mcp_cloudwatch",
            status="unknown",
            message="CloudWatch MCP 서버 상태를 확인할 수 없습니다"
        )
        
    except Exception as e:
        logger.error(f"CloudWatch MCP 헬스 체크 중 예외 발생: {e}")
        return ServiceStatus(
            name="mcp_cloudwatch",
            status="unhealthy",
            message=f"상태 확인 실패: {str(e)}"
        )


def _check_bedrock_health() -> ServiceStatus:
    """
    AWS Bedrock 연결 상태를 확인합니다.
    
    Bedrock 구성이 설정되어 있는지 확인합니다.
    실제 API 호출은 비용이 발생하므로 구성 존재 여부만 확인합니다.
    
    Returns:
        ServiceStatus: Bedrock 상태 정보
    
    요구사항: 10.5
    """
    try:
        # Bedrock 환경 변수 확인
        aws_access_key = os.environ.get("AWS_ACCESS_KEY_ID")
        aws_secret_key = os.environ.get("AWS_SECRET_ACCESS_KEY")
        aws_region = os.environ.get("AWS_REGION")
        
        # 구성되지 않은 경우
        if not aws_access_key or not aws_secret_key or not aws_region:
            return ServiceStatus(
                name="bedrock",
                status="unknown",
                message="AWS Bedrock이 구성되지 않았습니다"
            )
        
        # Bedrock 구성이 설정되어 있는 경우
        if _bedrock_config is not None:
            return ServiceStatus(
                name="bedrock",
                status="healthy",
                message=f"AWS Bedrock 구성 완료 (리전: {_bedrock_config.region}, 모델: {_bedrock_config.model_id})"
            )
        
        # 환경 변수는 있지만 구성 객체가 없는 경우
        model_id = os.environ.get("BEDROCK_MODEL_ID", "anthropic.claude-sonnet-4-5")
        return ServiceStatus(
            name="bedrock",
            status="healthy",
            message=f"AWS Bedrock 구성 완료 (리전: {aws_region}, 모델: {model_id})"
        )
        
    except Exception as e:
        logger.error(f"Bedrock 헬스 체크 중 예외 발생: {e}")
        return ServiceStatus(
            name="bedrock",
            status="unhealthy",
            message=f"상태 확인 실패: {str(e)}"
        )


def _determine_overall_status(components: List[ServiceStatus]) -> str:
    """
    개별 구성 요소 상태를 기반으로 전체 시스템 상태를 결정합니다.
    
    상태 결정 규칙:
    - 데이터베이스가 unhealthy이면 전체 시스템은 unhealthy
    - 모든 구성 요소가 healthy이면 전체 시스템은 healthy
    - 일부 구성 요소가 unhealthy 또는 unknown이면 전체 시스템은 degraded
    
    Args:
        components: 개별 구성 요소 상태 목록
    
    Returns:
        str: 전체 시스템 상태 ('healthy', 'unhealthy', 'degraded')
    
    요구사항: 10.5
    """
    # 데이터베이스 상태 확인 (필수 구성 요소)
    db_status = next(
        (c for c in components if c.name == "database"),
        None
    )
    
    # 데이터베이스가 unhealthy이면 전체 시스템은 unhealthy
    if db_status and db_status.status == "unhealthy":
        return "unhealthy"
    
    # 모든 구성 요소 상태 확인
    all_healthy = all(c.status == "healthy" for c in components)
    any_unhealthy = any(c.status == "unhealthy" for c in components)
    
    if all_healthy:
        return "healthy"
    elif any_unhealthy:
        return "degraded"
    else:
        # unknown 상태만 있는 경우 (선택적 구성 요소가 구성되지 않음)
        # 데이터베이스가 healthy이면 전체 시스템은 healthy
        if db_status and db_status.status == "healthy":
            return "healthy"
        return "degraded"


# =============================================================================
# 헬스 체크 엔드포인트
# =============================================================================

@app.get(
    "/health",
    response_model=HealthCheckResponse,
    tags=["health"],
    summary="서비스 상태 확인",
    description="서비스의 전체 상태와 각 구성 요소의 상태를 반환합니다.",
    responses={
        200: {
            "description": "서비스 상태 정보",
            "content": {
                "application/json": {
                    "example": {
                        "status": "healthy",
                        "service": "ai-chatbot-backend",
                        "version": "0.1.0",
                        "timestamp": "2024-01-15T10:30:00",
                        "components": [
                            {"name": "database", "status": "healthy", "message": "SQLite 데이터베이스 연결 정상"},
                            {"name": "mcp_grafana", "status": "healthy", "message": "Grafana MCP 서버 연결 정상 (도구 5개)"},
                            {"name": "mcp_cloudwatch", "status": "healthy", "message": "CloudWatch MCP 서버 연결 정상 (도구 3개)"},
                            {"name": "bedrock", "status": "healthy", "message": "AWS Bedrock 구성 완료 (리전: us-east-1, 모델: anthropic.claude-sonnet-4-5)"}
                        ]
                    }
                }
            }
        }
    }
)
async def health_check() -> HealthCheckResponse:
    """
    헬스 체크 엔드포인트
    
    서비스의 전체 상태와 각 구성 요소(데이터베이스, MCP 서버, Bedrock 등)의
    상태를 확인하고 반환합니다.
    
    구성 요소별 상태 확인:
    - database: SQLite 데이터베이스 연결 및 스키마 확인
    - mcp_grafana: Grafana MCP 서버 연결 상태 확인
    - mcp_cloudwatch: CloudWatch MCP 서버 연결 상태 확인
    - bedrock: AWS Bedrock 구성 상태 확인
    
    전체 상태 결정 규칙:
    - healthy: 모든 구성 요소가 정상
    - degraded: 일부 비필수 구성 요소에 문제가 있음
    - unhealthy: 필수 구성 요소(데이터베이스)에 문제가 있음
    
    Returns:
        HealthCheckResponse: 서비스 상태 정보
            - status: 전체 시스템 상태 ('healthy', 'unhealthy', 'degraded')
            - service: 서비스 이름
            - version: 서비스 버전
            - timestamp: 헬스 체크 시간
            - components: 개별 구성 요소 상태 목록
    
    요구사항: 10.5
    """
    # 각 구성 요소 상태 확인
    components: List[ServiceStatus] = []
    
    # API 서버 상태 (항상 healthy - 이 엔드포인트가 응답하면 API는 작동 중)
    components.append(ServiceStatus(
        name="api",
        status="healthy",
        message="API 서버 정상 작동 중"
    ))
    
    # 데이터베이스 상태 확인 (필수 구성 요소)
    db_status = _check_database_health()
    components.append(db_status)
    
    # MCP Grafana 서버 상태 확인 (선택적 구성 요소)
    grafana_status = _check_mcp_grafana_health()
    components.append(grafana_status)
    
    # MCP CloudWatch 서버 상태 확인 (선택적 구성 요소)
    cloudwatch_status = _check_mcp_cloudwatch_health()
    components.append(cloudwatch_status)
    
    # Bedrock 상태 확인 (선택적 구성 요소)
    bedrock_status = _check_bedrock_health()
    components.append(bedrock_status)
    
    # 전체 시스템 상태 결정
    overall_status = _determine_overall_status(components)
    
    # 상태 로깅
    logger.info(
        f"헬스 체크 완료: status={overall_status}, "
        f"components={[(c.name, c.status) for c in components]}"
    )
    
    return create_health_check_response(
        status=overall_status,
        components=components,
        version=SERVICE_VERSION
    )


@app.get(
    "/",
    tags=["health"],
    summary="루트 엔드포인트",
    description="API 환영 메시지와 문서 링크를 반환합니다."
)
async def root():
    """
    루트 엔드포인트
    
    API 환영 메시지와 문서 링크를 반환합니다.
    
    Returns:
        dict: 환영 메시지 및 문서 링크
    """
    return {
        "message": "AI 챗봇 인프라 모니터링 API",
        "version": SERVICE_VERSION,
        "docs": "/docs",
        "redoc": "/redoc",
        "health": "/health"
    }


# =============================================================================
# API 라우터 등록
# =============================================================================

# API 라우터를 앱에 등록
# 세션 및 메시지 엔드포인트 (Task 7.3에서 구현됨)
app.include_router(api_router)
app.include_router(sessions_router, prefix="/api")


# =============================================================================
# 개발 서버 실행
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    
    # 개발 서버 실행
    # 프로덕션 환경에서는 gunicorn 또는 다른 ASGI 서버 사용 권장
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # 개발 환경에서 자동 리로드 활성화
        log_level="info"
    )
