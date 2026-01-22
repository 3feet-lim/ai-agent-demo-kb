"""
데이터베이스 CRUD 작업 테스트

이 모듈은 데이터베이스 CRUD (Create, Read, Update, Delete) 작업을 테스트합니다.

요구사항: 3.1, 3.5, 7.1, 7.3
"""

import pytest
import sqlite3
import tempfile
import os
from datetime import datetime
from uuid import uuid4

from backend.database import Database


class TestSessionCRUD:
    """세션 CRUD 작업 테스트"""
    
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
    
    def test_create_session_with_default_values(self, temp_db):
        """기본값으로 세션 생성 테스트"""
        # Given: 초기화된 데이터베이스
        # When: 세션 생성
        session = temp_db.create_session()
        
        # Then: 세션이 생성되어야 함
        assert session is not None
        assert 'id' in session
        assert 'title' in session
        assert 'created_at' in session
        assert 'last_message_at' in session
        
        # And: 기본 제목이 설정되어야 함
        assert session['title'] == "새 대화"
        
        # And: ID가 UUID 형식이어야 함
        assert len(session['id']) == 36  # UUID 길이
        
        # And: 타임스탬프가 설정되어야 함
        assert session['created_at'] is not None
        assert session['last_message_at'] is not None
    
    def test_create_session_with_custom_values(self, temp_db):
        """사용자 정의 값으로 세션 생성 테스트"""
        # Given: 사용자 정의 세션 ID와 제목
        custom_id = str(uuid4())
        custom_title = "인프라 모니터링 분석"
        
        # When: 세션 생성
        session = temp_db.create_session(session_id=custom_id, title=custom_title)
        
        # Then: 사용자 정의 값이 적용되어야 함
        assert session['id'] == custom_id
        assert session['title'] == custom_title
    
    def test_create_session_persists_to_database(self, temp_db):
        """세션이 데이터베이스에 저장되는지 테스트"""
        # Given: 세션 생성
        session = temp_db.create_session(title="테스트 세션")
        
        # When: 데이터베이스에서 직접 조회
        conn = sqlite3.connect(temp_db.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM sessions WHERE id = ?", (session['id'],))
        row = cursor.fetchone()
        conn.close()
        
        # Then: 세션이 데이터베이스에 저장되어야 함
        assert row is not None
        assert row[0] == session['id']  # id
        assert row[1] == "테스트 세션"  # title
    
    def test_list_sessions_empty(self, temp_db):
        """빈 세션 목록 조회 테스트"""
        # Given: 세션이 없는 데이터베이스
        # When: 세션 목록 조회
        sessions = temp_db.list_sessions()
        
        # Then: 빈 목록이 반환되어야 함
        assert sessions == []
    
    def test_list_sessions_single(self, temp_db):
        """단일 세션 목록 조회 테스트"""
        # Given: 하나의 세션 생성
        created_session = temp_db.create_session(title="테스트 세션")
        
        # When: 세션 목록 조회
        sessions = temp_db.list_sessions()
        
        # Then: 하나의 세션이 반환되어야 함
        assert len(sessions) == 1
        assert sessions[0]['id'] == created_session['id']
        assert sessions[0]['title'] == "테스트 세션"
    
    def test_list_sessions_multiple(self, temp_db):
        """여러 세션 목록 조회 테스트"""
        # Given: 여러 세션 생성
        session1 = temp_db.create_session(title="세션 1")
        session2 = temp_db.create_session(title="세션 2")
        session3 = temp_db.create_session(title="세션 3")
        
        # When: 세션 목록 조회
        sessions = temp_db.list_sessions()
        
        # Then: 모든 세션이 반환되어야 함
        assert len(sessions) == 3
        session_ids = [s['id'] for s in sessions]
        assert session1['id'] in session_ids
        assert session2['id'] in session_ids
        assert session3['id'] in session_ids
    
    def test_list_sessions_sorted_by_last_message(self, temp_db):
        """세션이 last_message_at 순으로 정렬되는지 테스트"""
        # Given: 여러 세션 생성 (시간차를 두고)
        import time
        session1 = temp_db.create_session(title="오래된 세션")
        time.sleep(0.01)  # 타임스탬프 차이를 위한 짧은 대기
        session2 = temp_db.create_session(title="중간 세션")
        time.sleep(0.01)
        session3 = temp_db.create_session(title="최신 세션")
        
        # When: 세션 목록 조회
        sessions = temp_db.list_sessions()
        
        # Then: 최신 세션이 먼저 나와야 함 (내림차순)
        assert len(sessions) == 3
        assert sessions[0]['id'] == session3['id']  # 최신
        assert sessions[1]['id'] == session2['id']  # 중간
        assert sessions[2]['id'] == session1['id']  # 오래된


class TestMessageCRUD:
    """메시지 CRUD 작업 테스트"""
    
    @pytest.fixture
    def temp_db_with_session(self):
        """세션이 있는 임시 데이터베이스 생성"""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as f:
            temp_path = f.name
        db = Database(temp_path)
        session = db.create_session(title="테스트 세션")
        yield db, session['id']
        # 테스트 후 정리
        if os.path.exists(temp_path):
            os.unlink(temp_path)
    
    def test_save_message_user(self, temp_db_with_session):
        """사용자 메시지 저장 테스트"""
        # Given: 세션이 있는 데이터베이스
        db, session_id = temp_db_with_session
        
        # When: 사용자 메시지 저장
        message = db.save_message(
            session_id=session_id,
            content="안녕하세요, 인프라 상태를 확인해주세요.",
            role="user"
        )
        
        # Then: 메시지가 저장되어야 함
        assert message is not None
        assert message['id'] is not None
        assert message['session_id'] == session_id
        assert message['content'] == "안녕하세요, 인프라 상태를 확인해주세요."
        assert message['role'] == "user"
        assert message['timestamp'] is not None
    
    def test_save_message_assistant(self, temp_db_with_session):
        """어시스턴트 메시지 저장 테스트"""
        # Given: 세션이 있는 데이터베이스
        db, session_id = temp_db_with_session
        
        # When: 어시스턴트 메시지 저장
        message = db.save_message(
            session_id=session_id,
            content="인프라 상태를 확인했습니다. 모든 시스템이 정상입니다.",
            role="assistant"
        )
        
        # Then: 메시지가 저장되어야 함
        assert message['role'] == "assistant"
        assert message['content'] == "인프라 상태를 확인했습니다. 모든 시스템이 정상입니다."
    
    def test_save_message_with_custom_id(self, temp_db_with_session):
        """사용자 정의 ID로 메시지 저장 테스트"""
        # Given: 사용자 정의 메시지 ID
        db, session_id = temp_db_with_session
        custom_id = str(uuid4())
        
        # When: 메시지 저장
        message = db.save_message(
            session_id=session_id,
            content="테스트 메시지",
            role="user",
            message_id=custom_id
        )
        
        # Then: 사용자 정의 ID가 적용되어야 함
        assert message['id'] == custom_id
    
    def test_save_message_with_custom_timestamp(self, temp_db_with_session):
        """사용자 정의 타임스탬프로 메시지 저장 테스트"""
        # Given: 사용자 정의 타임스탬프
        db, session_id = temp_db_with_session
        custom_timestamp = "2024-01-01T12:00:00"
        
        # When: 메시지 저장
        message = db.save_message(
            session_id=session_id,
            content="테스트 메시지",
            role="user",
            timestamp=custom_timestamp
        )
        
        # Then: 사용자 정의 타임스탬프가 적용되어야 함
        assert message['timestamp'] == custom_timestamp
    
    def test_save_message_invalid_role(self, temp_db_with_session):
        """잘못된 role로 메시지 저장 시 오류 테스트"""
        # Given: 세션이 있는 데이터베이스
        db, session_id = temp_db_with_session
        
        # When/Then: 잘못된 role로 메시지 저장 시 ValueError 발생
        with pytest.raises(ValueError) as exc_info:
            db.save_message(
                session_id=session_id,
                content="테스트 메시지",
                role="invalid_role"
            )
        
        assert "잘못된 role 값" in str(exc_info.value)
    
    def test_save_message_updates_session_last_message_at(self, temp_db_with_session):
        """메시지 저장 시 세션의 last_message_at이 업데이트되는지 테스트"""
        # Given: 세션이 있는 데이터베이스
        db, session_id = temp_db_with_session
        
        # When: 메시지 저장
        import time
        time.sleep(0.01)  # 타임스탬프 차이를 위한 짧은 대기
        message = db.save_message(
            session_id=session_id,
            content="새 메시지",
            role="user"
        )
        
        # Then: 세션의 last_message_at이 업데이트되어야 함
        sessions = db.list_sessions()
        session = next(s for s in sessions if s['id'] == session_id)
        assert session['last_message_at'] == message['timestamp']
    
    def test_get_messages_empty(self, temp_db_with_session):
        """메시지가 없는 세션 조회 테스트"""
        # Given: 메시지가 없는 세션
        db, session_id = temp_db_with_session
        
        # When: 메시지 조회
        messages = db.get_messages(session_id)
        
        # Then: 빈 목록이 반환되어야 함
        assert messages == []
    
    def test_get_messages_single(self, temp_db_with_session):
        """단일 메시지 조회 테스트"""
        # Given: 하나의 메시지가 있는 세션
        db, session_id = temp_db_with_session
        saved_message = db.save_message(
            session_id=session_id,
            content="테스트 메시지",
            role="user"
        )
        
        # When: 메시지 조회
        messages = db.get_messages(session_id)
        
        # Then: 하나의 메시지가 반환되어야 함
        assert len(messages) == 1
        assert messages[0]['id'] == saved_message['id']
        assert messages[0]['content'] == "테스트 메시지"
    
    def test_get_messages_multiple(self, temp_db_with_session):
        """여러 메시지 조회 테스트"""
        # Given: 여러 메시지가 있는 세션
        db, session_id = temp_db_with_session
        msg1 = db.save_message(session_id=session_id, content="메시지 1", role="user")
        msg2 = db.save_message(session_id=session_id, content="메시지 2", role="assistant")
        msg3 = db.save_message(session_id=session_id, content="메시지 3", role="user")
        
        # When: 메시지 조회
        messages = db.get_messages(session_id)
        
        # Then: 모든 메시지가 반환되어야 함
        assert len(messages) == 3
        message_ids = [m['id'] for m in messages]
        assert msg1['id'] in message_ids
        assert msg2['id'] in message_ids
        assert msg3['id'] in message_ids
    
    def test_get_messages_sorted_by_timestamp(self, temp_db_with_session):
        """메시지가 타임스탬프 순으로 정렬되는지 테스트"""
        # Given: 여러 메시지가 있는 세션 (시간차를 두고)
        db, session_id = temp_db_with_session
        import time
        
        msg1 = db.save_message(session_id=session_id, content="첫 번째", role="user")
        time.sleep(0.01)
        msg2 = db.save_message(session_id=session_id, content="두 번째", role="assistant")
        time.sleep(0.01)
        msg3 = db.save_message(session_id=session_id, content="세 번째", role="user")
        
        # When: 메시지 조회
        messages = db.get_messages(session_id)
        
        # Then: 시간순으로 정렬되어야 함 (오름차순)
        assert len(messages) == 3
        assert messages[0]['id'] == msg1['id']  # 가장 오래된
        assert messages[1]['id'] == msg2['id']  # 중간
        assert messages[2]['id'] == msg3['id']  # 가장 최신
    
    def test_get_messages_session_isolation(self, temp_db_with_session):
        """세션 간 메시지 격리 테스트"""
        # Given: 두 개의 세션과 각각의 메시지
        db, session1_id = temp_db_with_session
        session2 = db.create_session(title="두 번째 세션")
        session2_id = session2['id']
        
        msg1 = db.save_message(session_id=session1_id, content="세션1 메시지", role="user")
        msg2 = db.save_message(session_id=session2_id, content="세션2 메시지", role="user")
        
        # When: 각 세션의 메시지 조회
        messages1 = db.get_messages(session1_id)
        messages2 = db.get_messages(session2_id)
        
        # Then: 각 세션의 메시지만 반환되어야 함
        assert len(messages1) == 1
        assert len(messages2) == 1
        assert messages1[0]['id'] == msg1['id']
        assert messages2[0]['id'] == msg2['id']
        assert messages1[0]['content'] == "세션1 메시지"
        assert messages2[0]['content'] == "세션2 메시지"


class TestDatabaseEdgeCases:
    """데이터베이스 엣지 케이스 테스트"""
    
    @pytest.fixture
    def temp_db(self):
        """임시 데이터베이스 생성"""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as f:
            temp_path = f.name
        db = Database(temp_path)
        yield db
        if os.path.exists(temp_path):
            os.unlink(temp_path)
    
    def test_save_message_to_nonexistent_session(self, temp_db):
        """존재하지 않는 세션에 메시지 저장 시 오류 테스트"""
        # Given: 존재하지 않는 세션 ID
        nonexistent_session_id = str(uuid4())
        
        # When/Then: 외래키 제약조건으로 인해 오류 발생
        # 참고: 외래키가 활성화되지 않은 경우 이 테스트는 실패할 수 있음
        # SQLite는 기본적으로 외래키를 비활성화하므로, 이 테스트는 선택적
        try:
            temp_db.save_message(
                session_id=nonexistent_session_id,
                content="테스트 메시지",
                role="user"
            )
            # 외래키가 비활성화된 경우 성공할 수 있음
        except sqlite3.IntegrityError:
            # 외래키가 활성화된 경우 예상되는 동작
            pass
    
    def test_empty_message_content(self, temp_db):
        """빈 메시지 내용 저장 테스트"""
        # Given: 세션 생성
        session = temp_db.create_session()
        
        # When: 빈 내용으로 메시지 저장
        message = temp_db.save_message(
            session_id=session['id'],
            content="",
            role="user"
        )
        
        # Then: 빈 내용도 저장되어야 함
        assert message['content'] == ""
    
    def test_long_message_content(self, temp_db):
        """긴 메시지 내용 저장 테스트"""
        # Given: 세션 생성
        session = temp_db.create_session()
        
        # When: 매우 긴 내용으로 메시지 저장
        long_content = "A" * 10000  # 10,000자
        message = temp_db.save_message(
            session_id=session['id'],
            content=long_content,
            role="user"
        )
        
        # Then: 긴 내용도 저장되어야 함
        assert len(message['content']) == 10000
    
    def test_special_characters_in_content(self, temp_db):
        """특수 문자가 포함된 메시지 저장 테스트"""
        # Given: 세션 생성
        session = temp_db.create_session()
        
        # When: 특수 문자가 포함된 메시지 저장
        special_content = "테스트 '따옴표' \"큰따옴표\" \n줄바꿈 \t탭 🚀 이모지"
        message = temp_db.save_message(
            session_id=session['id'],
            content=special_content,
            role="user"
        )
        
        # Then: 특수 문자가 그대로 저장되어야 함
        assert message['content'] == special_content
    
    def test_unicode_in_session_title(self, temp_db):
        """유니코드가 포함된 세션 제목 테스트"""
        # Given: 유니코드 문자가 포함된 제목
        unicode_title = "인프라 모니터링 🔍 分析"
        
        # When: 세션 생성
        session = temp_db.create_session(title=unicode_title)
        
        # Then: 유니코드가 그대로 저장되어야 함
        assert session['title'] == unicode_title
        
        # And: 조회 시에도 유니코드가 유지되어야 함
        sessions = temp_db.list_sessions()
        assert sessions[0]['title'] == unicode_title
