# 데이터베이스 CRUD 작업 구현 완료

## 개요

Task 2.2 "데이터베이스 CRUD 작업 구현"이 성공적으로 완료되었습니다.

## 구현된 기능

### 1. create_session 함수
- **목적**: 새로운 대화 세션 생성
- **매개변수**:
  - `session_id` (선택사항): 세션 ID (없으면 자동 생성)
  - `title` (기본값: "새 대화"): 세션 제목
- **반환값**: 생성된 세션 정보 (id, title, created_at, last_message_at)
- **요구사항**: 3.1, 3.5

### 2. save_message 함수
- **목적**: 메시지를 데이터베이스에 저장
- **매개변수**:
  - `session_id`: 세션 ID
  - `content`: 메시지 내용
  - `role`: 발신자 유형 ('user' 또는 'assistant')
  - `message_id` (선택사항): 메시지 ID (없으면 자동 생성)
  - `timestamp` (선택사항): 타임스탬프 (없으면 현재 시간)
- **반환값**: 저장된 메시지 정보 (id, session_id, content, role, timestamp)
- **추가 기능**: 세션의 last_message_at 자동 업데이트
- **요구사항**: 7.1, 7.2

### 3. get_messages 함수
- **목적**: 세션의 모든 메시지 조회 (타임스탬프 순으로 정렬)
- **매개변수**:
  - `session_id`: 세션 ID
- **반환값**: 메시지 목록 (시간순 오름차순 정렬)
- **정렬**: timestamp ASC (가장 오래된 것부터 최신 순)
- **요구사항**: 7.3

### 4. list_sessions 함수
- **목적**: 모든 세션 조회 (last_message_at 순으로 정렬)
- **매개변수**: 없음
- **반환값**: 세션 목록 (최근 메시지 순 정렬)
- **정렬**: last_message_at DESC (최신 메시지가 있는 세션부터)
- **요구사항**: 3.5

## 테스트 커버리지

총 **23개의 단위 테스트**가 작성되어 모두 통과했습니다:

### TestSessionCRUD (7개 테스트)
- ✅ test_create_session_with_default_values
- ✅ test_create_session_with_custom_values
- ✅ test_create_session_persists_to_database
- ✅ test_list_sessions_empty
- ✅ test_list_sessions_single
- ✅ test_list_sessions_multiple
- ✅ test_list_sessions_sorted_by_last_message

### TestMessageCRUD (11개 테스트)
- ✅ test_save_message_user
- ✅ test_save_message_assistant
- ✅ test_save_message_with_custom_id
- ✅ test_save_message_with_custom_timestamp
- ✅ test_save_message_invalid_role
- ✅ test_save_message_updates_session_last_message_at
- ✅ test_get_messages_empty
- ✅ test_get_messages_single
- ✅ test_get_messages_multiple
- ✅ test_get_messages_sorted_by_timestamp
- ✅ test_get_messages_session_isolation

### TestDatabaseEdgeCases (5개 테스트)
- ✅ test_save_message_to_nonexistent_session
- ✅ test_empty_message_content
- ✅ test_long_message_content
- ✅ test_special_characters_in_content
- ✅ test_unicode_in_session_title

## 주요 특징

### 1. 자동 ID 생성
- 세션 ID와 메시지 ID는 UUID4를 사용하여 자동 생성
- 사용자가 원하는 경우 커스텀 ID 지정 가능

### 2. 타임스탬프 관리
- ISO 8601 형식의 UTC 타임스탬프 사용
- 메시지 저장 시 세션의 last_message_at 자동 업데이트

### 3. 데이터 검증
- role 필드는 'user' 또는 'assistant'만 허용
- 잘못된 role 값 입력 시 ValueError 발생

### 4. 정렬 기능
- 메시지: 타임스탬프 오름차순 (시간순)
- 세션: last_message_at 내림차순 (최신 활동 순)

### 5. 세션 격리
- 각 세션의 메시지는 완전히 격리되어 관리
- 한 세션의 메시지가 다른 세션에 영향을 주지 않음

### 6. 에러 처리
- SQLite 오류 발생 시 적절한 로깅
- 외래키 제약조건 위반 처리
- 잘못된 입력 값에 대한 검증

### 7. 유니코드 지원
- 한글, 이모지 등 모든 유니코드 문자 지원
- 특수 문자 및 긴 텍스트 처리

## 사용 예제

```python
from backend.database import Database

# 데이터베이스 초기화
db = Database("chatbot.db")

# 세션 생성
session = db.create_session(title="인프라 모니터링")
session_id = session['id']

# 사용자 메시지 저장
user_msg = db.save_message(
    session_id=session_id,
    content="서버 상태를 확인해주세요",
    role="user"
)

# AI 응답 저장
ai_msg = db.save_message(
    session_id=session_id,
    content="모든 서버가 정상 작동 중입니다",
    role="assistant"
)

# 메시지 조회
messages = db.get_messages(session_id)
for msg in messages:
    print(f"{msg['role']}: {msg['content']}")

# 세션 목록 조회
sessions = db.list_sessions()
for s in sessions:
    print(f"{s['title']} - {s['last_message_at']}")
```

## 파일 위치

- **구현**: `backend/database.py`
- **테스트**: `backend/tests/test_database_crud.py`

## 다음 단계

Task 2.2가 완료되었으므로, 다음 작업으로 진행할 수 있습니다:
- Task 2.3: 세션 지속성 왕복에 대한 속성 테스트 (선택사항)
- Task 2.4: 메시지 지속성에 대한 속성 테스트 (선택사항)
- Task 2.5: 메시지 기록 왕복에 대한 속성 테스트 (선택사항)
- Task 2.6: 재시작 후 지속성에 대한 속성 테스트 (선택사항)
- Task 2.7: 데이터베이스 엣지 케이스에 대한 단위 테스트 (이미 완료됨)

또는 Task 3 (구성 관리 구현)으로 진행할 수 있습니다.
