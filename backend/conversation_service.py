"""
대화 서비스 - 대화 세션 및 메시지 관리

이 모듈은 사용자와 AI 간의 대화를 관리하는 서비스 클래스를 제공합니다.
데이터베이스, LLM 체인, MCP 관리자를 통합하여 완전한 대화 흐름을 처리합니다.

주요 기능:
- 대화 세션 생성 및 관리
- 사용자 메시지 처리 및 AI 응답 생성
- 대화 기록 저장 및 조회
- 오류 처리 및 로깅

요구사항: 3.1, 3.2, 4.3, 7.1, 7.2
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from uuid import uuid4

from database import Database
from llm_chain import (
    LLMChainBuilder,
    BedrockAPIError,
    BedrockConnectionError,
    BedrockAuthenticationError,
    BedrockRateLimitError,
    BedrockModelError,
    format_agent_response
)
from mcp_manager import MCPServerManager, MCPToolError
from models import (
    MessageResponse,
    SessionResponse,
    create_message_response,
    create_session_response
)
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage

# 로거 설정
logger = logging.getLogger(__name__)


# =============================================================================
# 대화 서비스 예외 클래스
# =============================================================================

class ConversationServiceError(Exception):
    """
    대화 서비스 오류 기본 예외 클래스
    
    대화 서비스에서 발생하는 모든 오류의 기본 클래스입니다.
    
    Attributes:
        message: 오류 메시지
        original_error: 원본 예외 (있는 경우)
    """
    
    def __init__(
        self,
        message: str,
        original_error: Optional[Exception] = None
    ):
        self.message = message
        self.original_error = original_error
        super().__init__(self._format_message())
    
    def _format_message(self) -> str:
        """오류 메시지 포맷팅"""
        base_msg = f"대화 서비스 오류: {self.message}"
        if self.original_error:
            base_msg += f" (원인: {type(self.original_error).__name__}: {str(self.original_error)})"
        return base_msg


class SessionNotFoundError(ConversationServiceError):
    """
    세션을 찾을 수 없는 경우 발생하는 예외
    
    Attributes:
        session_id: 찾을 수 없는 세션 ID
    """
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        super().__init__(f"세션을 찾을 수 없습니다: {session_id}")


class MessageProcessingError(ConversationServiceError):
    """
    메시지 처리 중 발생하는 예외
    
    사용자 메시지를 처리하거나 AI 응답을 생성하는 중 발생하는 오류입니다.
    """
    pass


class AIResponseError(ConversationServiceError):
    """
    AI 응답 생성 중 발생하는 예외
    
    LLM 호출 또는 응답 처리 중 발생하는 오류입니다.
    """
    pass


# =============================================================================
# 대화 서비스 클래스
# =============================================================================

class ConversationService:
    """
    대화 서비스 클래스
    
    사용자와 AI 간의 대화를 관리하는 핵심 서비스입니다.
    데이터베이스, LLM 체인, MCP 관리자를 통합하여 완전한 대화 흐름을 처리합니다.
    
    주요 기능:
    - 대화 세션 생성 및 관리 (create_session, list_sessions)
    - 사용자 메시지 처리 및 AI 응답 생성 (send_message)
    - 대화 기록 조회 (get_history)
    
    Attributes:
        db: 데이터베이스 인스턴스
        llm_chain_builder: LLM 체인 빌더 인스턴스
        mcp_manager: MCP 서버 관리자 인스턴스
    
    요구사항: 3.1, 3.2, 4.3, 7.1, 7.2
    """
    
    def __init__(
        self,
        db: Database,
        llm_chain_builder: LLMChainBuilder,
        mcp_manager: MCPServerManager
    ):
        """
        ConversationService 초기화
        
        Args:
            db: 데이터베이스 인스턴스 (대화 기록 저장용)
            llm_chain_builder: LLM 체인 빌더 인스턴스 (AI 응답 생성용)
            mcp_manager: MCP 서버 관리자 인스턴스 (도구 호출용)
        
        요구사항: 3.1, 4.3, 7.1
        """
        self.db = db
        self.llm_chain_builder = llm_chain_builder
        self.mcp_manager = mcp_manager
        
        logger.info("ConversationService 초기화 완료")
    
    async def send_message(
        self,
        session_id: str,
        content: str
    ) -> MessageResponse:
        """
        사용자 메시지를 처리하고 AI 응답을 생성합니다.
        
        이 메서드는 다음 단계를 수행합니다:
        1. 사용자 메시지를 데이터베이스에 저장
        2. 대화 기록 검색
        3. LLM 에이전트 호출 (MCP 도구 포함)
        4. AI 응답을 데이터베이스에 저장
        5. AI 응답 반환
        
        Args:
            session_id: 대화 세션 ID
            content: 사용자 메시지 내용
        
        Returns:
            MessageResponse: AI 응답 메시지
        
        Raises:
            SessionNotFoundError: 세션을 찾을 수 없는 경우
            MessageProcessingError: 메시지 처리 중 오류 발생 시
            AIResponseError: AI 응답 생성 중 오류 발생 시
        
        요구사항: 3.2, 4.3, 7.1, 7.2
        """
        logger.info(f"메시지 처리 시작: session_id={session_id}, content_length={len(content)}")
        
        try:
            # 1. 세션 존재 여부 확인
            sessions = self.db.list_sessions()
            session_exists = any(s['id'] == session_id for s in sessions)
            
            if not session_exists:
                logger.error(f"세션을 찾을 수 없음: {session_id}")
                raise SessionNotFoundError(session_id)
            
            # 2. 사용자 메시지를 데이터베이스에 저장
            user_message = self._save_user_message(session_id, content)
            logger.info(f"사용자 메시지 저장 완료: message_id={user_message['id']}")
            
            # 3. 대화 기록 검색
            chat_history = self._get_chat_history_as_messages(session_id)
            logger.debug(f"대화 기록 로드: {len(chat_history)}개 메시지")
            
            # 4. LLM 에이전트 호출
            ai_response_content = await self._invoke_llm_agent(
                user_input=content,
                chat_history=chat_history
            )
            logger.info(f"AI 응답 생성 완료: response_length={len(ai_response_content)}")
            
            # 5. AI 응답을 데이터베이스에 저장
            ai_message = self._save_assistant_message(session_id, ai_response_content)
            logger.info(f"AI 응답 저장 완료: message_id={ai_message['id']}")
            
            # 6. MessageResponse 객체 생성 및 반환
            return create_message_response(
                message_id=ai_message['id'],
                session_id=ai_message['session_id'],
                content=ai_message['content'],
                role='assistant',
                timestamp=ai_message['timestamp']
            )
            
        except SessionNotFoundError:
            raise
        except BedrockAPIError as e:
            logger.error(f"Bedrock API 오류: {e}")
            raise AIResponseError(
                message="AI 응답 생성 중 오류가 발생했습니다.",
                original_error=e
            )
        except MCPToolError as e:
            logger.error(f"MCP 도구 오류: {e}")
            raise AIResponseError(
                message="도구 실행 중 오류가 발생했습니다.",
                original_error=e
            )
        except Exception as e:
            logger.error(f"메시지 처리 중 예기치 않은 오류: {e}")
            raise MessageProcessingError(
                message="메시지 처리 중 오류가 발생했습니다.",
                original_error=e
            )
    
    def get_history(self, session_id: str) -> List[MessageResponse]:
        """
        세션의 모든 메시지 기록을 조회합니다.
        
        메시지는 타임스탬프 순으로 정렬되어 반환됩니다.
        
        Args:
            session_id: 대화 세션 ID
        
        Returns:
            List[MessageResponse]: 메시지 목록 (시간순 정렬)
        
        Raises:
            SessionNotFoundError: 세션을 찾을 수 없는 경우
            ConversationServiceError: 기록 조회 중 오류 발생 시
        
        요구사항: 3.2, 7.3
        """
        logger.info(f"대화 기록 조회: session_id={session_id}")
        
        try:
            # 세션 존재 여부 확인
            sessions = self.db.list_sessions()
            session_exists = any(s['id'] == session_id for s in sessions)
            
            if not session_exists:
                logger.error(f"세션을 찾을 수 없음: {session_id}")
                raise SessionNotFoundError(session_id)
            
            # 데이터베이스에서 메시지 조회
            messages = self.db.get_messages(session_id)
            
            # MessageResponse 객체 목록으로 변환
            response_messages = []
            for msg in messages:
                response_messages.append(
                    create_message_response(
                        message_id=msg['id'],
                        session_id=msg['session_id'],
                        content=msg['content'],
                        role=msg['role'],
                        timestamp=msg['timestamp']
                    )
                )
            
            logger.info(f"대화 기록 조회 완료: {len(response_messages)}개 메시지")
            return response_messages
            
        except SessionNotFoundError:
            raise
        except Exception as e:
            logger.error(f"대화 기록 조회 중 오류: {e}")
            raise ConversationServiceError(
                message="대화 기록 조회 중 오류가 발생했습니다.",
                original_error=e
            )
    
    def create_session(self, title: str = "새 대화") -> SessionResponse:
        """
        새 대화 세션을 생성합니다.
        
        Args:
            title: 세션 제목 (기본값: "새 대화")
        
        Returns:
            SessionResponse: 생성된 세션 정보
        
        Raises:
            ConversationServiceError: 세션 생성 중 오류 발생 시
        
        요구사항: 3.1
        """
        logger.info(f"새 세션 생성: title={title}")
        
        try:
            # 데이터베이스에 세션 생성
            session = self.db.create_session(title=title)
            
            # SessionResponse 객체 생성 및 반환
            response = create_session_response(
                session_id=session['id'],
                title=session['title'],
                created_at=session['created_at'],
                last_message_at=session['last_message_at']
            )
            
            logger.info(f"세션 생성 완료: session_id={session['id']}")
            return response
            
        except Exception as e:
            logger.error(f"세션 생성 중 오류: {e}")
            raise ConversationServiceError(
                message="세션 생성 중 오류가 발생했습니다.",
                original_error=e
            )
    
    def list_sessions(self) -> List[SessionResponse]:
        """
        모든 대화 세션 목록을 조회합니다.
        
        세션은 마지막 메시지 시간 기준 내림차순으로 정렬됩니다.
        
        Returns:
            List[SessionResponse]: 세션 목록 (최근 메시지 순 정렬)
        
        Raises:
            ConversationServiceError: 세션 목록 조회 중 오류 발생 시
        
        요구사항: 3.2
        """
        logger.info("세션 목록 조회")
        
        try:
            # 데이터베이스에서 세션 목록 조회
            sessions = self.db.list_sessions()
            
            # SessionResponse 객체 목록으로 변환
            response_sessions = []
            for session in sessions:
                response_sessions.append(
                    create_session_response(
                        session_id=session['id'],
                        title=session['title'],
                        created_at=session['created_at'],
                        last_message_at=session['last_message_at']
                    )
                )
            
            logger.info(f"세션 목록 조회 완료: {len(response_sessions)}개 세션")
            return response_sessions
            
        except Exception as e:
            logger.error(f"세션 목록 조회 중 오류: {e}")
            raise ConversationServiceError(
                message="세션 목록 조회 중 오류가 발생했습니다.",
                original_error=e
            )
    
    # =========================================================================
    # 내부 헬퍼 메서드
    # =========================================================================
    
    def _save_user_message(
        self,
        session_id: str,
        content: str
    ) -> Dict[str, Any]:
        """
        사용자 메시지를 데이터베이스에 저장합니다.
        
        Args:
            session_id: 세션 ID
            content: 메시지 내용
        
        Returns:
            Dict[str, Any]: 저장된 메시지 정보
        
        요구사항: 7.1, 7.2
        """
        return self.db.save_message(
            session_id=session_id,
            content=content,
            role='user'
        )
    
    def _save_assistant_message(
        self,
        session_id: str,
        content: str
    ) -> Dict[str, Any]:
        """
        AI 응답 메시지를 데이터베이스에 저장합니다.
        
        Args:
            session_id: 세션 ID
            content: 메시지 내용
        
        Returns:
            Dict[str, Any]: 저장된 메시지 정보
        
        요구사항: 7.1, 7.2
        """
        return self.db.save_message(
            session_id=session_id,
            content=content,
            role='assistant'
        )
    
    def _get_chat_history_as_messages(
        self,
        session_id: str
    ) -> List[BaseMessage]:
        """
        세션의 대화 기록을 LangChain 메시지 형식으로 변환합니다.
        
        Args:
            session_id: 세션 ID
        
        Returns:
            List[BaseMessage]: LangChain 메시지 목록
        """
        messages = self.db.get_messages(session_id)
        
        langchain_messages: List[BaseMessage] = []
        for msg in messages:
            if msg['role'] == 'user':
                langchain_messages.append(HumanMessage(content=msg['content']))
            elif msg['role'] == 'assistant':
                langchain_messages.append(AIMessage(content=msg['content']))
        
        return langchain_messages
    
    async def _invoke_llm_agent(
        self,
        user_input: str,
        chat_history: List[BaseMessage]
    ) -> str:
        """
        LLM 에이전트를 호출하여 AI 응답을 생성합니다.
        
        MCP 도구를 포함한 에이전트를 구성하고 사용자 입력을 처리합니다.
        
        Args:
            user_input: 사용자 입력 메시지
            chat_history: 이전 대화 기록 (LangChain 메시지 형식)
        
        Returns:
            str: AI 응답 텍스트
        
        Raises:
            BedrockAPIError: Bedrock API 호출 실패 시
            MCPToolError: MCP 도구 실행 실패 시
        
        요구사항: 4.3, 5.4
        """
        # MCP 도구 가져오기
        mcp_tools = self.mcp_manager.get_all_tools()
        logger.debug(f"MCP 도구 로드: {len(mcp_tools)}개")
        
        # 에이전트 빌드
        agent = self.llm_chain_builder.build_chain(
            mcp_tools=mcp_tools,
            chat_history=chat_history
        )
        
        # 에이전트 호출
        result = await self.llm_chain_builder.invoke_agent(
            agent=agent,
            user_input=user_input,
            chat_history=chat_history
        )
        
        # 응답 포맷팅
        response_text = format_agent_response(result)
        
        return response_text
    
    def get_session_info(self, session_id: str) -> Optional[SessionResponse]:
        """
        특정 세션의 정보를 조회합니다.
        
        Args:
            session_id: 세션 ID
        
        Returns:
            Optional[SessionResponse]: 세션 정보 또는 None (세션이 없는 경우)
        """
        try:
            sessions = self.db.list_sessions()
            for session in sessions:
                if session['id'] == session_id:
                    return create_session_response(
                        session_id=session['id'],
                        title=session['title'],
                        created_at=session['created_at'],
                        last_message_at=session['last_message_at']
                    )
            return None
        except Exception as e:
            logger.error(f"세션 정보 조회 중 오류: {e}")
            return None


# =============================================================================
# 편의 함수
# =============================================================================

def create_conversation_service(
    db: Database,
    llm_chain_builder: LLMChainBuilder,
    mcp_manager: MCPServerManager
) -> ConversationService:
    """
    ConversationService 인스턴스를 생성하는 편의 함수
    
    Args:
        db: 데이터베이스 인스턴스
        llm_chain_builder: LLM 체인 빌더 인스턴스
        mcp_manager: MCP 서버 관리자 인스턴스
    
    Returns:
        ConversationService: 생성된 대화 서비스 인스턴스
    
    Example:
        >>> from database import Database
        >>> from llm_chain import LLMChainBuilder
        >>> from mcp_manager import MCPServerManager
        >>> from config import BedrockConfig
        >>> 
        >>> db = Database("chatbot.db")
        >>> llm_builder = LLMChainBuilder(bedrock_config)
        >>> mcp_manager = MCPServerManager(grafana_config, cloudwatch_config)
        >>> 
        >>> service = create_conversation_service(db, llm_builder, mcp_manager)
        >>> session = service.create_session("인프라 분석")
        >>> response = await service.send_message(session.id, "CPU 사용률을 확인해주세요")
    
    요구사항: 3.1, 3.2, 4.3, 7.1, 7.2
    """
    return ConversationService(
        db=db,
        llm_chain_builder=llm_chain_builder,
        mcp_manager=mcp_manager
    )
