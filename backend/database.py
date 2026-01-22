"""
데이터베이스 계층 - SQLite 연결 및 스키마 관리

이 모듈은 대화 세션 및 메시지를 저장하기 위한 SQLite 데이터베이스 연결과
스키마 초기화를 관리합니다.

요구사항: 7.1, 7.4
"""

import sqlite3
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import uuid4
import logging

# 로거 설정
logger = logging.getLogger(__name__)


class Database:
    """
    SQLite 데이터베이스 연결 및 스키마 관리 클래스
    
    이 클래스는 다음을 담당합니다:
    - 데이터베이스 연결 관리
    - 스키마 초기화 (sessions 및 messages 테이블)
    - 인덱스 생성
    """
    
    def __init__(self, db_path: str = "chatbot.db"):
        """
        데이터베이스 인스턴스 초기화
        
        Args:
            db_path: SQLite 데이터베이스 파일 경로
        """
        self.db_path = db_path
        logger.info(f"데이터베이스 초기화: {db_path}")
        self._init_schema()
    
    def _get_connection(self) -> sqlite3.Connection:
        """
        데이터베이스 연결 생성
        
        Returns:
            sqlite3.Connection: 데이터베이스 연결 객체
        """
        conn = sqlite3.connect(self.db_path)
        # Row 팩토리 설정으로 딕셔너리 형태로 결과 반환
        conn.row_factory = sqlite3.Row
        return conn
    
    def _init_schema(self) -> None:
        """
        데이터베이스 스키마 초기화
        
        존재하지 않는 경우 다음 테이블을 생성합니다:
        - sessions: 대화 세션 정보
        - messages: 대화 메시지 내용
        
        또한 성능을 위한 인덱스를 생성합니다:
        - idx_messages_session_id: 세션별 메시지 조회
        - idx_messages_timestamp: 시간순 메시지 정렬
        - idx_sessions_last_message: 최근 세션 조회
        
        요구사항: 7.1, 7.4
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # sessions 테이블 생성
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    last_message_at TIMESTAMP NOT NULL
                )
            ''')
            logger.info("sessions 테이블 생성 완료")
            
            # messages 테이블 생성
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    content TEXT NOT NULL,
                    role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
                    timestamp TIMESTAMP NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
                )
            ''')
            logger.info("messages 테이블 생성 완료")
            
            # 인덱스 생성 - 성능 최적화
            # 세션별 메시지 조회를 위한 인덱스
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_messages_session_id 
                ON messages(session_id)
            ''')
            logger.info("idx_messages_session_id 인덱스 생성 완료")
            
            # 시간순 메시지 정렬을 위한 인덱스
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_messages_timestamp 
                ON messages(timestamp)
            ''')
            logger.info("idx_messages_timestamp 인덱스 생성 완료")
            
            # 최근 세션 조회를 위한 인덱스
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_sessions_last_message 
                ON sessions(last_message_at DESC)
            ''')
            logger.info("idx_sessions_last_message 인덱스 생성 완료")
            
            conn.commit()
            logger.info("데이터베이스 스키마 초기화 완료")
            
        except sqlite3.Error as e:
            logger.error(f"데이터베이스 스키마 초기화 실패: {e}")
            raise
        finally:
            conn.close()
    
    def verify_schema(self) -> bool:
        """
        데이터베이스 스키마가 올바르게 생성되었는지 검증
        
        Returns:
            bool: 스키마가 올바르게 생성되었으면 True, 아니면 False
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # sessions 테이블 존재 확인
            cursor.execute('''
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='sessions'
            ''')
            if not cursor.fetchone():
                logger.error("sessions 테이블이 존재하지 않습니다")
                return False
            
            # messages 테이블 존재 확인
            cursor.execute('''
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='messages'
            ''')
            if not cursor.fetchone():
                logger.error("messages 테이블이 존재하지 않습니다")
                return False
            
            # 인덱스 존재 확인
            expected_indexes = [
                'idx_messages_session_id',
                'idx_messages_timestamp',
                'idx_sessions_last_message'
            ]
            
            for index_name in expected_indexes:
                cursor.execute('''
                    SELECT name FROM sqlite_master 
                    WHERE type='index' AND name=?
                ''', (index_name,))
                if not cursor.fetchone():
                    logger.error(f"인덱스 {index_name}이 존재하지 않습니다")
                    return False
            
            logger.info("데이터베이스 스키마 검증 완료")
            return True
            
        except sqlite3.Error as e:
            logger.error(f"데이터베이스 스키마 검증 실패: {e}")
            return False
        finally:
            conn.close()
    
    def close(self) -> None:
        """
        데이터베이스 연결 종료
        
        참고: 이 클래스는 각 작업마다 연결을 열고 닫으므로
        이 메서드는 주로 정리 목적으로 사용됩니다.
        """
        logger.info("데이터베이스 연결 종료")
    
    def create_session(self, session_id: Optional[str] = None, title: str = "새 대화") -> Dict[str, Any]:
        """
        새 대화 세션 생성
        
        Args:
            session_id: 세션 ID (선택사항, 없으면 자동 생성)
            title: 세션 제목
        
        Returns:
            Dict[str, Any]: 생성된 세션 정보
                - id: 세션 ID
                - title: 세션 제목
                - created_at: 생성 시간
                - last_message_at: 마지막 메시지 시간
        
        Raises:
            sqlite3.Error: 데이터베이스 작업 실패 시
        
        요구사항: 3.1, 3.5
        """
        if session_id is None:
            session_id = str(uuid4())
        
        now = datetime.utcnow().isoformat()
        
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO sessions (id, title, created_at, last_message_at)
                VALUES (?, ?, ?, ?)
            ''', (session_id, title, now, now))
            
            conn.commit()
            logger.info(f"세션 생성 완료: {session_id}")
            
            session = {
                'id': session_id,
                'title': title,
                'created_at': now,
                'last_message_at': now
            }
            
            return session
            
        except sqlite3.Error as e:
            logger.error(f"세션 생성 실패: {e}")
            raise
        finally:
            conn.close()
    
    def save_message(self, session_id: str, content: str, role: str, 
                    message_id: Optional[str] = None, 
                    timestamp: Optional[str] = None) -> Dict[str, Any]:
        """
        메시지 저장
        
        Args:
            session_id: 세션 ID
            content: 메시지 내용
            role: 발신자 유형 ('user' 또는 'assistant')
            message_id: 메시지 ID (선택사항, 없으면 자동 생성)
            timestamp: 타임스탬프 (선택사항, 없으면 현재 시간)
        
        Returns:
            Dict[str, Any]: 저장된 메시지 정보
                - id: 메시지 ID
                - session_id: 세션 ID
                - content: 메시지 내용
                - role: 발신자 유형
                - timestamp: 타임스탬프
        
        Raises:
            sqlite3.Error: 데이터베이스 작업 실패 시
            ValueError: 잘못된 role 값
        
        요구사항: 7.1, 7.2
        """
        if role not in ('user', 'assistant'):
            raise ValueError(f"잘못된 role 값: {role}. 'user' 또는 'assistant'여야 합니다.")
        
        if message_id is None:
            message_id = str(uuid4())
        
        if timestamp is None:
            timestamp = datetime.utcnow().isoformat()
        
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # 메시지 저장
            cursor.execute('''
                INSERT INTO messages (id, session_id, content, role, timestamp)
                VALUES (?, ?, ?, ?, ?)
            ''', (message_id, session_id, content, role, timestamp))
            
            # 세션의 last_message_at 업데이트
            cursor.execute('''
                UPDATE sessions
                SET last_message_at = ?
                WHERE id = ?
            ''', (timestamp, session_id))
            
            conn.commit()
            logger.info(f"메시지 저장 완료: {message_id} (세션: {session_id})")
            
            message = {
                'id': message_id,
                'session_id': session_id,
                'content': content,
                'role': role,
                'timestamp': timestamp
            }
            
            return message
            
        except sqlite3.Error as e:
            logger.error(f"메시지 저장 실패: {e}")
            raise
        finally:
            conn.close()
    
    def get_messages(self, session_id: str) -> List[Dict[str, Any]]:
        """
        세션의 모든 메시지 조회 (타임스탬프 순으로 정렬)
        
        Args:
            session_id: 세션 ID
        
        Returns:
            List[Dict[str, Any]]: 메시지 목록 (시간순 정렬)
                각 메시지는 다음 필드를 포함:
                - id: 메시지 ID
                - session_id: 세션 ID
                - content: 메시지 내용
                - role: 발신자 유형
                - timestamp: 타임스탬프
        
        Raises:
            sqlite3.Error: 데이터베이스 작업 실패 시
        
        요구사항: 7.3
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, session_id, content, role, timestamp
                FROM messages
                WHERE session_id = ?
                ORDER BY timestamp ASC
            ''', (session_id,))
            
            rows = cursor.fetchall()
            
            messages = []
            for row in rows:
                messages.append({
                    'id': row['id'],
                    'session_id': row['session_id'],
                    'content': row['content'],
                    'role': row['role'],
                    'timestamp': row['timestamp']
                })
            
            logger.info(f"메시지 조회 완료: {len(messages)}개 (세션: {session_id})")
            return messages
            
        except sqlite3.Error as e:
            logger.error(f"메시지 조회 실패: {e}")
            raise
        finally:
            conn.close()
    
    def list_sessions(self) -> List[Dict[str, Any]]:
        """
        모든 세션 조회 (last_message_at 내림차순으로 정렬)
        
        Returns:
            List[Dict[str, Any]]: 세션 목록 (최근 메시지 순 정렬)
                각 세션은 다음 필드를 포함:
                - id: 세션 ID
                - title: 세션 제목
                - created_at: 생성 시간
                - last_message_at: 마지막 메시지 시간
        
        Raises:
            sqlite3.Error: 데이터베이스 작업 실패 시
        
        요구사항: 3.5
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, title, created_at, last_message_at
                FROM sessions
                ORDER BY last_message_at DESC
            ''')
            
            rows = cursor.fetchall()
            
            sessions = []
            for row in rows:
                sessions.append({
                    'id': row['id'],
                    'title': row['title'],
                    'created_at': row['created_at'],
                    'last_message_at': row['last_message_at']
                })
            
            logger.info(f"세션 목록 조회 완료: {len(sessions)}개")
            return sessions
            
        except sqlite3.Error as e:
            logger.error(f"세션 목록 조회 실패: {e}")
            raise
        finally:
            conn.close()


def initialize_database(db_path: str = "chatbot.db") -> Database:
    """
    데이터베이스 초기화 함수
    
    존재하지 않는 경우 데이터베이스 파일을 생성하고
    필요한 테이블과 인덱스를 설정합니다.
    
    Args:
        db_path: SQLite 데이터베이스 파일 경로
    
    Returns:
        Database: 초기화된 데이터베이스 인스턴스
    
    Raises:
        sqlite3.Error: 데이터베이스 초기화 실패 시
    
    요구사항: 7.1, 7.4
    """
    logger.info(f"데이터베이스 초기화 시작: {db_path}")
    
    # 데이터베이스 디렉토리가 존재하는지 확인
    db_file = Path(db_path)
    db_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Database 인스턴스 생성 (자동으로 스키마 초기화)
    db = Database(db_path)
    
    # 스키마 검증
    if not db.verify_schema():
        raise RuntimeError("데이터베이스 스키마 검증 실패")
    
    logger.info("데이터베이스 초기화 완료")
    return db
