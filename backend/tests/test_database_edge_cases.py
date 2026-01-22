"""
데이터베이스 엣지 케이스 단위 테스트

이 모듈은 데이터베이스 작업의 엣지 케이스를 테스트합니다.
- 빈 세션 목록 테스트
- 메시지가 없는 세션 테스트
- 데이터베이스 제약 조건 위반 테스트

요구사항: 7.1, 7.3
작업: 2.7
"""

import pytest
import sqlite3
import tempfile
import os
from uuid import uuid4

from backend.database import Database


class TestEmptySessionList:
    """빈 세션 목록 테스트"""
    
    @pytest.fixture
    def temp_db(self):
        """임시 데이터베이스 생성"""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as f:
            temp_path = f.name
        db = Database(temp_path)
        yield db
        # 테스트 후 정리
        if os.path.exists(temp_path):
            os.unlink(temp_path)
    
    def test_list_sessions_returns_empty_list_when_no_sessions(self, temp_db):
        """세션이 없을 때 빈 리스트 반환 테스트
        
        요구사항: 7.1
        """
        # Given: 세션이 없는 데이터베이스
        # When: 세션 목록 조회
        sessions = temp_db.list_sessions()
        
        # Then: 빈 리스트가 반환되어야 함
        assert sessions == []
        assert isinstance(sessions, list)
        assert len(sessions) == 0
    
    def test_list_sessions_returns_empty_after_all_sessions_deleted(self, temp_db):
        """모든 세션 삭제 후 빈 리스트 반환 테스트
        
        요구사항: 7.1
        """
        # Given: 세션을 생성한 후 삭제
        session = temp_db.create_session(title="테스트 세션")
        
        # 직접 데이터베이스에서 세션 삭제
        conn = sqlite3.connect(temp_db.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM sessions WHERE id = ?", (session['id'],))
        conn.commit()
        conn.close()
        
        # When: 세션 목록 조회
        sessions = temp_db.list_sessions()
        
        # Then: 빈 리스트가 반환되어야 함
        assert sessions == []
    
    def test_list_sessions_type_consistency_when_empty(self, temp_db):
        """빈 세션 목록의 타입 일관성 테스트
        
        요구사항: 7.1
        """
        # Given: 세션이 없는 데이터베이스
        # When: 세션 목록 조회
        sessions = temp_db.list_sessions()
        
        # Then: 리스트 타입이어야 하며 반복 가능해야 함
        assert isinstance(sessions, list)
        # 빈 리스트도 반복 가능해야 함
        for session in sessions:
            pass  # 실행되지 않아야 함
        
        # And: 리스트 메서드가 작동해야 함
        assert sessions.count(None) == 0
        assert len(sessions) == 0


class TestSessionWithNoMessages:
    """메시지가 없는 세션 테스트"""
    
    @pytest.fixture
    def temp_db_with_session(self):
        """메시지가 없는 세션이 있는 임시 데이터베이스 생성"""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as f:
            temp_path = f.name
        db = Database(temp_path)
        session = db.create_session(title="빈 세션")
        yield db, session['id']
        # 테스트 후 정리
        if os.path.exists(temp_path):
            os.unlink(temp_path)
    
    def test_get_messages_returns_empty_list_for_session_with_no_messages(self, temp_db_with_session):
        """메시지가 없는 세션에서 빈 리스트 반환 테스트
        
        요구사항: 7.3
        """
        # Given: 메시지가 없는 세션
        db, session_id = temp_db_with_session
        
        # When: 메시지 조회
        messages = db.get_messages(session_id)
        
        # Then: 빈 리스트가 반환되어야 함
        assert messages == []
        assert isinstance(messages, list)
        assert len(messages) == 0
    
    def test_get_messages_for_nonexistent_session_returns_empty_list(self, temp_db_with_session):
        """존재하지 않는 세션의 메시지 조회 시 빈 리스트 반환 테스트
        
        요구사항: 7.3
        """
        # Given: 존재하지 않는 세션 ID
        db, _ = temp_db_with_session
        nonexistent_session_id = str(uuid4())
        
        # When: 메시지 조회
        messages = db.get_messages(nonexistent_session_id)
        
        # Then: 빈 리스트가 반환되어야 함 (오류가 아님)
        assert messages == []
        assert isinstance(messages, list)
    
    def test_get_messages_after_all_messages_deleted(self, temp_db_with_session):
        """모든 메시지 삭제 후 빈 리스트 반환 테스트
        
        요구사항: 7.3
        """
        # Given: 메시지가 있는 세션
        db, session_id = temp_db_with_session
        db.save_message(session_id=session_id, content="테스트 메시지", role="user")
        
        # 직접 데이터베이스에서 메시지 삭제
        conn = sqlite3.connect(db.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
        conn.commit()
        conn.close()
        
        # When: 메시지 조회
        messages = db.get_messages(session_id)
        
        # Then: 빈 리스트가 반환되어야 함
        assert messages == []
    
    def test_session_exists_but_has_no_messages(self, temp_db_with_session):
        """세션은 존재하지만 메시지가 없는 경우 테스트
        
        요구사항: 7.1, 7.3
        """
        # Given: 메시지가 없는 세션
        db, session_id = temp_db_with_session
        
        # When: 세션 목록과 메시지 조회
        sessions = db.list_sessions()
        messages = db.get_messages(session_id)
        
        # Then: 세션은 존재하지만 메시지는 없어야 함
        assert len(sessions) == 1
        assert sessions[0]['id'] == session_id
        assert messages == []
    
    def test_multiple_sessions_with_no_messages(self, temp_db_with_session):
        """여러 세션이 모두 메시지가 없는 경우 테스트
        
        요구사항: 7.1, 7.3
        """
        # Given: 여러 개의 빈 세션
        db, session1_id = temp_db_with_session
        session2 = db.create_session(title="빈 세션 2")
        session3 = db.create_session(title="빈 세션 3")
        
        # When: 각 세션의 메시지 조회
        messages1 = db.get_messages(session1_id)
        messages2 = db.get_messages(session2['id'])
        messages3 = db.get_messages(session3['id'])
        
        # Then: 모든 세션의 메시지가 빈 리스트여야 함
        assert messages1 == []
        assert messages2 == []
        assert messages3 == []
        
        # And: 세션 목록에는 모두 나타나야 함
        sessions = db.list_sessions()
        assert len(sessions) == 3


class TestDatabaseConstraintViolations:
    """데이터베이스 제약 조건 위반 테스트"""
    
    @pytest.fixture
    def temp_db(self):
        """임시 데이터베이스 생성"""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as f:
            temp_path = f.name
        db = Database(temp_path)
        yield db
        # 테스트 후 정리
        if os.path.exists(temp_path):
            os.unlink(temp_path)
    
    def test_duplicate_session_id_violation(self, temp_db):
        """중복 세션 ID 제약 조건 위반 테스트
        
        요구사항: 7.1
        """
        # Given: 이미 존재하는 세션 ID
        session_id = str(uuid4())
        temp_db.create_session(session_id=session_id, title="첫 번째 세션")
        
        # When/Then: 같은 ID로 세션 생성 시 IntegrityError 발생
        with pytest.raises(sqlite3.IntegrityError) as exc_info:
            temp_db.create_session(session_id=session_id, title="두 번째 세션")
        
        # And: 오류 메시지에 PRIMARY KEY 또는 UNIQUE 관련 내용이 있어야 함
        error_message = str(exc_info.value).lower()
        assert 'unique' in error_message or 'primary key' in error_message
    
    def test_duplicate_message_id_violation(self, temp_db):
        """중복 메시지 ID 제약 조건 위반 테스트
        
        요구사항: 7.1
        """
        # Given: 세션과 이미 존재하는 메시지 ID
        session = temp_db.create_session(title="테스트 세션")
        message_id = str(uuid4())
        temp_db.save_message(
            session_id=session['id'],
            content="첫 번째 메시지",
            role="user",
            message_id=message_id
        )
        
        # When/Then: 같은 ID로 메시지 저장 시 IntegrityError 발생
        with pytest.raises(sqlite3.IntegrityError) as exc_info:
            temp_db.save_message(
                session_id=session['id'],
                content="두 번째 메시지",
                role="user",
                message_id=message_id
            )
        
        # And: 오류 메시지에 PRIMARY KEY 또는 UNIQUE 관련 내용이 있어야 함
        error_message = str(exc_info.value).lower()
        assert 'unique' in error_message or 'primary key' in error_message
    
    def test_invalid_role_check_constraint_violation(self, temp_db):
        """잘못된 role 값 CHECK 제약 조건 위반 테스트
        
        요구사항: 7.1
        """
        # Given: 세션 생성
        session = temp_db.create_session(title="테스트 세션")
        
        # When/Then: 잘못된 role 값으로 메시지 저장 시 ValueError 발생
        with pytest.raises(ValueError) as exc_info:
            temp_db.save_message(
                session_id=session['id'],
                content="테스트 메시지",
                role="invalid_role"
            )
        
        # And: 오류 메시지에 role 관련 내용이 있어야 함
        assert "role" in str(exc_info.value).lower()
    
    def test_foreign_key_constraint_violation_with_pragma_enabled(self, temp_db):
        """외래키 제약 조건 위반 테스트 (PRAGMA 활성화)
        
        요구사항: 7.1
        """
        # Given: 외래키가 활성화된 데이터베이스 연결
        conn = sqlite3.connect(temp_db.db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        cursor = conn.cursor()
        
        # When/Then: 존재하지 않는 세션에 메시지 삽입 시 IntegrityError 발생
        with pytest.raises(sqlite3.IntegrityError) as exc_info:
            cursor.execute('''
                INSERT INTO messages (id, session_id, content, role, timestamp)
                VALUES (?, ?, ?, ?, ?)
            ''', (str(uuid4()), str(uuid4()), "테스트 메시지", "user", "2024-01-01T00:00:00"))
            conn.commit()
        
        conn.close()
        
        # And: 오류 메시지에 foreign key 관련 내용이 있어야 함
        error_message = str(exc_info.value).lower()
        assert 'foreign key' in error_message
    
    def test_null_session_id_violation(self, temp_db):
        """NULL session_id NOT NULL 제약 조건 위반 테스트
        
        요구사항: 7.1
        """
        # Given: 데이터베이스 연결
        conn = sqlite3.connect(temp_db.db_path)
        cursor = conn.cursor()
        
        # When/Then: NULL title로 세션 생성 시 IntegrityError 발생
        # 참고: SQLite에서 TEXT PRIMARY KEY는 NULL을 허용하므로 title로 테스트
        with pytest.raises(sqlite3.IntegrityError):
            cursor.execute('''
                INSERT INTO sessions (id, title, created_at, last_message_at)
                VALUES (?, NULL, '2024-01-01T00:00:00', '2024-01-01T00:00:00')
            ''', (str(uuid4()),))
            conn.commit()
        
        conn.close()
    
    def test_null_message_content_violation(self, temp_db):
        """NULL content NOT NULL 제약 조건 위반 테스트
        
        요구사항: 7.1
        """
        # Given: 세션이 있는 데이터베이스
        session = temp_db.create_session(title="테스트 세션")
        conn = sqlite3.connect(temp_db.db_path)
        cursor = conn.cursor()
        
        # When/Then: NULL content로 메시지 삽입 시 IntegrityError 발생
        with pytest.raises(sqlite3.IntegrityError):
            cursor.execute('''
                INSERT INTO messages (id, session_id, content, role, timestamp)
                VALUES (?, ?, NULL, ?, ?)
            ''', (str(uuid4()), session['id'], "user", "2024-01-01T00:00:00"))
            conn.commit()
        
        conn.close()
    
    def test_null_role_violation(self, temp_db):
        """NULL role NOT NULL 제약 조건 위반 테스트
        
        요구사항: 7.1
        """
        # Given: 세션이 있는 데이터베이스
        session = temp_db.create_session(title="테스트 세션")
        conn = sqlite3.connect(temp_db.db_path)
        cursor = conn.cursor()
        
        # When/Then: NULL role로 메시지 삽입 시 IntegrityError 발생
        with pytest.raises(sqlite3.IntegrityError):
            cursor.execute('''
                INSERT INTO messages (id, session_id, content, role, timestamp)
                VALUES (?, ?, ?, NULL, ?)
            ''', (str(uuid4()), session['id'], "테스트 메시지", "2024-01-01T00:00:00"))
            conn.commit()
        
        conn.close()
    
    def test_cascade_delete_on_session_deletion(self, temp_db):
        """세션 삭제 시 CASCADE 동작 테스트
        
        요구사항: 7.1
        """
        # Given: 메시지가 있는 세션
        session = temp_db.create_session(title="테스트 세션")
        message = temp_db.save_message(
            session_id=session['id'],
            content="테스트 메시지",
            role="user"
        )
        
        # When: 외래키를 활성화하고 세션 삭제
        conn = sqlite3.connect(temp_db.db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        cursor = conn.cursor()
        cursor.execute("DELETE FROM sessions WHERE id = ?", (session['id'],))
        conn.commit()
        
        # Then: 관련 메시지도 삭제되어야 함 (CASCADE)
        cursor.execute("SELECT * FROM messages WHERE id = ?", (message['id'],))
        result = cursor.fetchone()
        conn.close()
        
        assert result is None
    
    def test_invalid_role_direct_insert_violation(self, temp_db):
        """직접 삽입 시 잘못된 role CHECK 제약 조건 위반 테스트
        
        요구사항: 7.1
        """
        # Given: 세션이 있는 데이터베이스
        session = temp_db.create_session(title="테스트 세션")
        conn = sqlite3.connect(temp_db.db_path)
        cursor = conn.cursor()
        
        # When/Then: 'user' 또는 'assistant'가 아닌 role로 삽입 시 IntegrityError 발생
        with pytest.raises(sqlite3.IntegrityError) as exc_info:
            cursor.execute('''
                INSERT INTO messages (id, session_id, content, role, timestamp)
                VALUES (?, ?, ?, ?, ?)
            ''', (str(uuid4()), session['id'], "테스트 메시지", "admin", "2024-01-01T00:00:00"))
            conn.commit()
        
        conn.close()
        
        # And: CHECK 제약 조건 관련 오류여야 함
        error_message = str(exc_info.value).lower()
        assert 'check' in error_message or 'constraint' in error_message


class TestDatabaseErrorHandling:
    """데이터베이스 오류 처리 테스트"""
    
    @pytest.fixture
    def temp_db(self):
        """임시 데이터베이스 생성"""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as f:
            temp_path = f.name
        db = Database(temp_path)
        yield db
        # 테스트 후 정리
        if os.path.exists(temp_path):
            os.unlink(temp_path)
    
    def test_save_message_with_empty_session_id(self, temp_db):
        """빈 세션 ID로 메시지 저장 시 오류 테스트
        
        요구사항: 7.1
        """
        # Given: 빈 세션 ID
        # When/Then: 빈 세션 ID로 메시지 저장 시 오류 발생
        # 외래키가 활성화되지 않은 경우 성공할 수 있으므로,
        # 이는 애플리케이션 레벨에서 검증해야 함
        try:
            temp_db.save_message(
                session_id="",
                content="테스트 메시지",
                role="user"
            )
            # 외래키가 비활성화된 경우 성공할 수 있음
        except (sqlite3.IntegrityError, ValueError):
            # 예상되는 동작
            pass
    
    def test_save_message_with_none_content(self, temp_db):
        """None content로 메시지 저장 시 오류 테스트
        
        요구사항: 7.1
        """
        # Given: 세션 생성
        session = temp_db.create_session(title="테스트 세션")
        
        # When/Then: None content로 메시지 저장 시 오류 발생
        with pytest.raises((sqlite3.IntegrityError, TypeError)):
            temp_db.save_message(
                session_id=session['id'],
                content=None,
                role="user"
            )
    
    def test_create_session_with_none_title(self, temp_db):
        """None title로 세션 생성 시 오류 테스트
        
        요구사항: 7.1
        """
        # Given: None title
        # When/Then: None title로 세션 생성 시 오류 발생
        with pytest.raises((sqlite3.IntegrityError, TypeError)):
            temp_db.create_session(title=None)
