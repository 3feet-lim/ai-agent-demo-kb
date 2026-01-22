"""
AI 챗봇 인프라 모니터링 - 백엔드 메인 진입점

이 모듈은 백엔드 애플리케이션의 메인 진입점입니다.
애플리케이션 시작 시 모든 구성 요소를 초기화하고,
종료 시 리소스를 정리합니다.

주요 기능:
- 환경 변수에서 구성 로드
- 데이터베이스 연결 초기화
- MCP 서버 관리자 초기화
- LangChain 에이전트 빌드
- FastAPI 서버 시작
- 우아한 종료 처리

요구사항: 4.1, 4.4, 8.1, 8.5
"""

import asyncio
import logging
import signal
import sys
from typing import Optional

import uvicorn

# 애플리케이션 모듈 임포트
from app import app, SERVICE_VERSION, set_lifespan_callbacks, set_health_check_resources
from config import (
    load_config_from_env,
    ConfigurationError,
    AppConfig
)
from database import Database, initialize_database
from mcp_manager import MCPServerManager
from llm_chain import LLMChainBuilder, BedrockAPIError
from conversation_service import ConversationService, create_conversation_service
from routes import set_conversation_service, sessions_router


# =============================================================================
# 로깅 설정
# =============================================================================

def setup_logging(log_level: str = "INFO") -> logging.Logger:
    """
    애플리케이션 로깅을 설정합니다.
    
    Args:
        log_level: 로그 레벨 (기본값: INFO)
    
    Returns:
        logging.Logger: 설정된 로거 인스턴스
    """
    # 로그 포맷 설정
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # 기본 로깅 설정
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format=log_format,
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # 루트 로거 가져오기
    logger = logging.getLogger("ai-chatbot-backend")
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    
    return logger


# 로거 초기화
logger = setup_logging()


# =============================================================================
# 전역 리소스 관리
# =============================================================================

# 전역 리소스 인스턴스
_database: Optional[Database] = None
_mcp_manager: Optional[MCPServerManager] = None
_llm_chain_builder: Optional[LLMChainBuilder] = None
_conversation_service: Optional[ConversationService] = None
_config: Optional[AppConfig] = None


# =============================================================================
# 시작 함수
# =============================================================================

async def startup() -> None:
    """
    애플리케이션 시작 시 모든 구성 요소를 초기화합니다.
    
    이 함수는 다음 단계를 수행합니다:
    1. 환경 변수에서 구성 로드
    2. 데이터베이스 연결 초기화
    3. MCP 서버 관리자 초기화
    4. LangChain 에이전트 빌더 생성
    5. ConversationService 생성 및 설정
    
    Raises:
        ConfigurationError: 필수 환경 변수가 누락된 경우
        BedrockAPIError: Bedrock 클라이언트 초기화 실패 시
        Exception: 기타 초기화 오류 발생 시
    
    요구사항: 4.1, 4.4, 8.1, 8.5
    """
    global _database, _mcp_manager, _llm_chain_builder, _conversation_service, _config
    
    logger.info("=" * 60)
    logger.info("AI 챗봇 백엔드 서비스 시작")
    logger.info(f"버전: {SERVICE_VERSION}")
    logger.info("=" * 60)
    
    try:
        # 1. 환경 변수에서 구성 로드
        logger.info("1단계: 구성 로드 중...")
        _config = load_config_from_env()
        logger.info("구성 로드 완료")
        logger.info(f"  - Bedrock 리전: {_config.bedrock.region}")
        logger.info(f"  - Bedrock 모델: {_config.bedrock.model_id}")
        logger.info(f"  - Grafana URL: {_config.grafana.url}")
        logger.info(f"  - CloudWatch 리전: {_config.cloudwatch.region}")
        logger.info(f"  - 데이터베이스 경로: {_config.database.path}")
        
        # 2. 데이터베이스 연결 초기화
        logger.info("2단계: 데이터베이스 초기화 중...")
        _database = initialize_database(_config.database.path)
        logger.info(f"데이터베이스 초기화 완료: {_config.database.path}")
        
        # 3. MCP 서버 관리자 초기화
        logger.info("3단계: MCP 서버 관리자 초기화 중...")
        _mcp_manager = MCPServerManager(
            grafana_config=_config.grafana,
            cloudwatch_config=_config.cloudwatch
        )
        
        # MCP 서버 초기화 (비동기)
        try:
            await _mcp_manager.initialize_servers()
            logger.info(f"MCP 서버 초기화 완료: {_mcp_manager.connected_server_count}개 서버 연결됨")
            
            # 서버 상태 로깅
            server_status = _mcp_manager.get_server_status()
            for server_name, status in server_status.items():
                logger.info(f"  - {server_name}: 연결={status['is_connected']}, 도구={status['tool_count']}개")
        except Exception as e:
            # MCP 서버 초기화 실패는 경고로 처리 (서비스는 계속 실행)
            logger.warning(f"MCP 서버 초기화 중 오류 발생 (서비스는 계속 실행됨): {e}")
        
        # 4. LangChain 에이전트 빌더 생성
        logger.info("4단계: LangChain 에이전트 빌더 생성 중...")
        _llm_chain_builder = LLMChainBuilder(config=_config.bedrock)
        logger.info("LangChain 에이전트 빌더 생성 완료")
        logger.info(f"  - 모델: {_config.bedrock.model_id}")
        logger.info(f"  - Temperature: {_config.bedrock.temperature}")
        logger.info(f"  - Max Tokens: {_config.bedrock.max_tokens}")
        
        # 5. ConversationService 생성 및 설정
        logger.info("5단계: ConversationService 생성 중...")
        _conversation_service = create_conversation_service(
            db=_database,
            llm_chain_builder=_llm_chain_builder,
            mcp_manager=_mcp_manager
        )
        
        # 라우트에 서비스 설정
        set_conversation_service(_conversation_service)
        logger.info("ConversationService 생성 및 설정 완료")
        
        # 6. 헬스 체크 리소스 설정
        logger.info("6단계: 헬스 체크 리소스 설정 중...")
        set_health_check_resources(
            database=_database,
            mcp_manager=_mcp_manager,
            bedrock_config=_config.bedrock
        )
        logger.info("헬스 체크 리소스 설정 완료")
        
        logger.info("=" * 60)
        logger.info("AI 챗봇 백엔드 서비스 시작 완료")
        logger.info("API 문서: http://localhost:8000/docs")
        logger.info("ReDoc: http://localhost:8000/redoc")
        logger.info("헬스 체크: http://localhost:8000/health")
        logger.info("=" * 60)
        
    except ConfigurationError as e:
        logger.error("=" * 60)
        logger.error("구성 오류로 인해 애플리케이션을 시작할 수 없습니다.")
        logger.error(str(e))
        logger.error("=" * 60)
        raise
    
    except BedrockAPIError as e:
        logger.error("=" * 60)
        logger.error("Bedrock API 오류로 인해 애플리케이션을 시작할 수 없습니다.")
        logger.error(str(e))
        logger.error("=" * 60)
        raise
    
    except Exception as e:
        logger.error("=" * 60)
        logger.error(f"애플리케이션 시작 중 예기치 않은 오류 발생: {e}")
        logger.error("=" * 60)
        raise


# =============================================================================
# 종료 함수
# =============================================================================

async def shutdown() -> None:
    """
    애플리케이션 종료 시 모든 리소스를 정리합니다.
    
    이 함수는 다음 단계를 수행합니다:
    1. MCP 서버 종료
    2. 데이터베이스 연결 종료
    3. 기타 리소스 정리
    
    요구사항: 8.1
    """
    global _database, _mcp_manager, _llm_chain_builder, _conversation_service
    
    logger.info("=" * 60)
    logger.info("AI 챗봇 백엔드 서비스 종료 시작")
    logger.info("=" * 60)
    
    # 1. MCP 서버 종료
    if _mcp_manager is not None:
        logger.info("MCP 서버 종료 중...")
        try:
            await _mcp_manager.shutdown()
            logger.info("MCP 서버 종료 완료")
        except Exception as e:
            logger.error(f"MCP 서버 종료 중 오류: {e}")
    
    # 2. 데이터베이스 연결 종료
    if _database is not None:
        logger.info("데이터베이스 연결 종료 중...")
        try:
            _database.close()
            logger.info("데이터베이스 연결 종료 완료")
        except Exception as e:
            logger.error(f"데이터베이스 연결 종료 중 오류: {e}")
    
    # 3. 전역 변수 정리
    _database = None
    _mcp_manager = None
    _llm_chain_builder = None
    _conversation_service = None
    
    logger.info("=" * 60)
    logger.info("AI 챗봇 백엔드 서비스 종료 완료")
    logger.info("=" * 60)


# =============================================================================
# 시그널 핸들러
# =============================================================================

def handle_signal(signum: int, frame) -> None:
    """
    시그널 핸들러 - 우아한 종료를 위한 시그널 처리
    
    SIGINT (Ctrl+C) 또는 SIGTERM 시그널을 받으면
    애플리케이션을 우아하게 종료합니다.
    
    Args:
        signum: 시그널 번호
        frame: 현재 스택 프레임
    """
    signal_name = signal.Signals(signum).name
    logger.info(f"시그널 수신: {signal_name}")
    
    # 비동기 종료 함수 실행
    loop = asyncio.get_event_loop()
    if loop.is_running():
        loop.create_task(shutdown())
    else:
        asyncio.run(shutdown())
    
    sys.exit(0)


# =============================================================================
# 메인 실행
# =============================================================================

def main() -> None:
    """
    메인 함수 - 애플리케이션 진입점
    
    시그널 핸들러를 등록하고 uvicorn 서버를 시작합니다.
    
    요구사항: 4.1, 8.1
    """
    # lifespan 콜백 등록
    set_lifespan_callbacks(startup, shutdown)
    
    # 시그널 핸들러 등록 (우아한 종료)
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)
    
    logger.info("uvicorn 서버 시작 중...")
    
    # uvicorn 서버 실행
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=False,  # 프로덕션 환경에서는 reload 비활성화
        log_level="info",
        access_log=True
    )


# =============================================================================
# 스크립트 직접 실행 시
# =============================================================================

if __name__ == "__main__":
    main()
