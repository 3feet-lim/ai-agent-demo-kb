"""
데이터베이스 스키마 및 초기화 테스트

이 모듈은 데이터베이스 스키마 생성 및 초기화 기능을 테스트합니다.

요구사항: 7.1, 7.4
"""

import pytest
import sqlite3
import tempfile
import os
from pathlib import Path

from backend.database import Database, initialize_database


class TestDatabaseSchema:
    """데이터베이스 스키마 생성 테스트"""
    
    @pytest.fixture
    def temp_db_path(self):
        """임시 데이터베이스 파일 경로 생성"""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as f:
            temp_path = f.name
        yield temp_path
        # 테스트 후 정리
        if os.path.exists(temp_path):
            os.unlink(temp_path)
    
    def test_database_initialization(self, temp_db_path):
        """데이터베이스 초기화 테스트"""
        # Given: 임시 데이터베이스 경로
        # When: 데이터베이스 초기화
        db = Database(temp_db_path)
        
        # Then: 데이터베이스 파일이 생성되어야 함
        assert os.path.exists(temp_db_path)
        
        # And: 스키마 검증이 성공해야 함
        assert db.verify_schema() is True
    
    def test_sessions_table_created(self, temp_db_path):
        """sessions 테이블 생성 테스트"""
        # Given: 초기화된 데이터베이스
        db = Database(temp_db_path)
        
        # When: 테이블 존재 확인
        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='sessions'
        ''')
        result = cursor.fetchone()
        conn.close()
        
        # Then: sessions 테이블이 존재해야 함
        assert result is not None
        assert result[0] == 'sessions'
    
    def test_messages_table_created(self, temp_db_path):
        """messages 테이블 생성 테스트"""
        # Given: 초기화된 데이터베이스
        db = Database(temp_db_path)
        
        # When: 테이블 존재 확인
        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='messages'
        ''')
        result = cursor.fetchone()
        conn.close()
        
        # Then: messages 테이블이 존재해야 함
        assert result is not None
        assert result[0] == 'messages'
    
    def test_sessions_table_schema(self, temp_db_path):
        """sessions 테이블 스키마 검증"""
        # Given: 초기화된 데이터베이스
        db = Database(temp_db_path)
        
        # When: 테이블 스키마 조회
        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(sessions)")
        columns = cursor.fetchall()
        conn.close()
        
        # Then: 필수 컬럼이 존재해야 함
        column_names = [col[1] for col in columns]
        assert 'id' in column_names
        assert 'title' in column_names
        assert 'created_at' in column_names
        assert 'last_message_at' in column_names
    
    def test_messages_table_schema(self, temp_db_path):
        """messages 테이블 스키마 검증"""
        # Given: 초기화된 데이터베이스
        db = Database(temp_db_path)
        
        # When: 테이블 스키마 조회
        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(messages)")
        columns = cursor.fetchall()
        conn.close()
        
        # Then: 필수 컬럼이 존재해야 함
        column_names = [col[1] for col in columns]
        assert 'id' in column_names
        assert 'session_id' in column_names
        assert 'content' in column_names
        assert 'role' in column_names
        assert 'timestamp' in column_names
    
    def test_indexes_created(self, temp_db_path):
        """인덱스 생성 테스트"""
        # Given: 초기화된 데이터베이스
        db = Database(temp_db_path)
        
        # When: 인덱스 목록 조회
        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT name FROM sqlite_master 
            WHERE type='index'
        ''')
        indexes = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        # Then: 필수 인덱스가 존재해야 함
        assert 'idx_messages_session_id' in indexes
        assert 'idx_messages_timestamp' in indexes
        assert 'idx_sessions_last_message' in indexes
    
    def test_messages_role_constraint(self, temp_db_path):
        """messages 테이블 role 제약조건 테스트"""
        # Given: 초기화된 데이터베이스
        db = Database(temp_db_path)
        
        # When: 잘못된 role 값으로 메시지 삽입 시도
        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()
        
        # Then: CHECK 제약조건 위반으로 실패해야 함
        with pytest.raises(sqlite3.IntegrityError):
            cursor.execute('''
                INSERT INTO messages (id, session_id, content, role, timestamp)
                VALUES ('test-id', 'session-id', 'test content', 'invalid_role', '2024-01-01 00:00:00')
            ''')
        
        conn.close()
    
    def test_foreign_key_constraint(self, temp_db_path):
        """messages 테이블 외래키 제약조건 테스트"""
        # Given: 초기화된 데이터베이스
        db = Database(temp_db_path)
        
        # When: 외래키 활성화 및 존재하지 않는 세션에 메시지 삽입 시도
        conn = sqlite3.connect(temp_db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        cursor = conn.cursor()
        
        # Then: 외래키 제약조건 위반으로 실패해야 함
        with pytest.raises(sqlite3.IntegrityError):
            cursor.execute('''
                INSERT INTO messages (id, session_id, content, role, timestamp)
                VALUES ('test-id', 'nonexistent-session', 'test content', 'user', '2024-01-01 00:00:00')
            ''')
        
        conn.close()
    
    def test_initialize_database_function(self, temp_db_path):
        """initialize_database 함수 테스트"""
        # Given: 임시 데이터베이스 경로
        # When: initialize_database 함수 호출
        db = initialize_database(temp_db_path)
        
        # Then: 데이터베이스가 초기화되어야 함
        assert db is not None
        assert os.path.exists(temp_db_path)
        assert db.verify_schema() is True
    
    def test_initialize_database_creates_directory(self):
        """initialize_database가 디렉토리를 생성하는지 테스트"""
        # Given: 존재하지 않는 디렉토리 경로
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, 'subdir', 'test.db')
            
            # When: initialize_database 함수 호출
            db = initialize_database(db_path)
            
            # Then: 디렉토리와 데이터베이스 파일이 생성되어야 함
            assert os.path.exists(db_path)
            assert db.verify_schema() is True
    
    def test_database_reinitialization(self, temp_db_path):
        """데이터베이스 재초기화 테스트 (멱등성)"""
        # Given: 이미 초기화된 데이터베이스
        db1 = Database(temp_db_path)
        
        # When: 같은 경로로 다시 초기화
        db2 = Database(temp_db_path)
        
        # Then: 오류 없이 재초기화되어야 함
        assert db2.verify_schema() is True
    
    def test_empty_database_verification(self, temp_db_path):
        """빈 데이터베이스 검증 테스트"""
        # Given: 빈 데이터베이스 파일
        conn = sqlite3.connect(temp_db_path)
        conn.close()
        
        # When: 스키마 없이 검증 시도
        db = Database.__new__(Database)
        db.db_path = temp_db_path
        
        # Then: 검증이 실패해야 함
        assert db.verify_schema() is False


class TestDatabaseConnection:
    """데이터베이스 연결 관리 테스트"""
    
    @pytest.fixture
    def temp_db_path(self):
        """임시 데이터베이스 파일 경로 생성"""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as f:
            temp_path = f.name
        yield temp_path
        if os.path.exists(temp_path):
            os.unlink(temp_path)
    
    def test_get_connection(self, temp_db_path):
        """데이터베이스 연결 생성 테스트"""
        # Given: 초기화된 데이터베이스
        db = Database(temp_db_path)
        
        # When: 연결 생성
        conn = db._get_connection()
        
        # Then: 연결이 유효해야 함
        assert conn is not None
        assert isinstance(conn, sqlite3.Connection)
        
        # And: Row 팩토리가 설정되어야 함
        assert conn.row_factory == sqlite3.Row
        
        conn.close()
    
    def test_connection_row_factory(self, temp_db_path):
        """Row 팩토리 설정 테스트"""
        # Given: 초기화된 데이터베이스
        db = Database(temp_db_path)
        
        # When: 데이터 조회
        conn = db._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' LIMIT 1")
        row = cursor.fetchone()
        conn.close()
        
        # Then: Row 객체로 반환되어야 함
        assert row is not None
        assert hasattr(row, 'keys')
