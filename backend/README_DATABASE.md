# 데이터베이스 모듈 사용 가이드

## 개요

이 모듈은 AI 챗봇 인프라 모니터링 시스템의 대화 세션 및 메시지를 저장하기 위한 SQLite 데이터베이스 계층을 제공합니다.

## 주요 기능

- **자동 스키마 초기화**: 데이터베이스 파일이 없거나 테이블이 없는 경우 자동으로 생성
- **세션 관리**: 대화 세션 정보 저장 (ID, 제목, 생성 시간, 마지막 메시지 시간)
- **메시지 저장**: 사용자 및 AI 메시지 저장 (ID, 세션 ID, 내용, 역할, 타임스탬프)
- **성능 최적화**: 자주 사용되는 쿼리를 위한 인덱스 자동 생성
- **데이터 무결성**: 외래키 제약조건 및 CHECK 제약조건 지원

## 데이터베이스 스키마

### sessions 테이블

대화 세션 정보를 저장합니다.

| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | TEXT | 세션 고유 식별자 (PRIMARY KEY) |
| title | TEXT | 세션 제목 (NOT NULL) |
| created_at | TIMESTAMP | 세션 생성 시간 (NOT NULL) |
| last_message_at | TIMESTAMP | 마지막 메시지 시간 (NOT NULL) |

### messages 테이블

대화 메시지를 저장합니다.

| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | TEXT | 메시지 고유 식별자 (PRIMARY KEY) |
| session_id | TEXT | 세션 ID (FOREIGN KEY → sessions.id) |
| content | TEXT | 메시지 내용 (NOT NULL) |
| role | TEXT | 발신자 역할: 'user' 또는 'assistant' (NOT NULL, CHECK) |
| timestamp | TIMESTAMP | 메시지 생성 시간 (NOT NULL) |

### 인덱스

성능 최적화를 위해 다음 인덱스가 자동으로 생성됩니다:

- `idx_messages_session_id`: 세션별 메시지 조회 최적화
- `idx_messages_timestamp`: 시간순 메시지 정렬 최적화
- `idx_sessions_last_message`: 최근 세션 조회 최적화

## 사용 방법

### 기본 사용

```python
from backend.database import initialize_database

# 데이터베이스 초기화
db = initialize_database("chatbot.db")

# 스키마 검증
if db.verify_schema():
    print("데이터베이스가 올바르게 초기화되었습니다")
```

### 커스텀 경로 사용

```python
from backend.database import Database

# 특정 경로에 데이터베이스 생성
db = Database("/path/to/custom/database.db")
```

### 연결 관리

```python
# 데이터베이스 연결 가져오기
conn = db._get_connection()

try:
    cursor = conn.cursor()
    # 쿼리 실행
    cursor.execute("SELECT * FROM sessions")
    results = cursor.fetchall()
    
    # Row 팩토리로 딕셔너리처럼 접근 가능
    for row in results:
        print(f"Session ID: {row['id']}, Title: {row['title']}")
finally:
    conn.close()
```

## 제약조건

### role 제약조건

messages 테이블의 `role` 컬럼은 'user' 또는 'assistant' 값만 허용합니다.

```python
# 올바른 사용
cursor.execute("""
    INSERT INTO messages (id, session_id, content, role, timestamp)
    VALUES (?, ?, ?, ?, ?)
""", ('msg-1', 'session-1', 'Hello', 'user', '2024-01-01 00:00:00'))

# 잘못된 사용 - IntegrityError 발생
cursor.execute("""
    INSERT INTO messages (id, session_id, content, role, timestamp)
    VALUES (?, ?, ?, ?, ?)
""", ('msg-2', 'session-1', 'Hi', 'invalid_role', '2024-01-01 00:00:00'))
```

### 외래키 제약조건

messages 테이블의 `session_id`는 sessions 테이블의 `id`를 참조해야 합니다.

```python
# 외래키 활성화 (SQLite는 기본적으로 비활성화)
conn.execute("PRAGMA foreign_keys = ON")

# 세션이 존재하지 않으면 IntegrityError 발생
cursor.execute("""
    INSERT INTO messages (id, session_id, content, role, timestamp)
    VALUES (?, ?, ?, ?, ?)
""", ('msg-1', 'nonexistent-session', 'Hello', 'user', '2024-01-01 00:00:00'))
```

## 오류 처리

```python
import sqlite3
from backend.database import initialize_database

try:
    db = initialize_database("chatbot.db")
except sqlite3.Error as e:
    print(f"데이터베이스 초기화 실패: {e}")
except RuntimeError as e:
    print(f"스키마 검증 실패: {e}")
```

## 로깅

데이터베이스 모듈은 Python의 표준 logging 모듈을 사용합니다.

```python
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)

# 데이터베이스 초기화 시 로그 출력
db = initialize_database("chatbot.db")
# INFO:backend.database:데이터베이스 초기화: chatbot.db
# INFO:backend.database:sessions 테이블 생성 완료
# INFO:backend.database:messages 테이블 생성 완료
# ...
```

## 테스트

데이터베이스 모듈은 포괄적인 단위 테스트를 포함합니다:

```bash
# 모든 데이터베이스 테스트 실행
python -m pytest backend/tests/test_database_schema.py -v

# 특정 테스트 클래스 실행
python -m pytest backend/tests/test_database_schema.py::TestDatabaseSchema -v

# 특정 테스트 실행
python -m pytest backend/tests/test_database_schema.py::TestDatabaseSchema::test_database_initialization -v
```

## 요구사항 매핑

이 모듈은 다음 요구사항을 충족합니다:

- **요구사항 7.1**: 모든 대화 메시지를 SQLite 데이터베이스에 저장
- **요구사항 7.4**: 메시지 내용, 타임스탬프, 발신자 유형 및 세션 식별자 저장

## 다음 단계

데이터베이스 스키마가 준비되었으므로 다음 작업을 진행할 수 있습니다:

1. **Task 2.2**: 데이터베이스 CRUD 작업 구현
   - `create_session()`: 새 세션 생성
   - `save_message()`: 메시지 저장
   - `get_messages()`: 세션의 메시지 조회
   - `list_sessions()`: 모든 세션 목록 조회

2. **Task 2.3-2.6**: 속성 기반 테스트 작성
   - 세션 지속성 왕복 테스트
   - 메시지 지속성 테스트
   - 메시지 기록 왕복 테스트
   - 재시작 후 지속성 테스트
