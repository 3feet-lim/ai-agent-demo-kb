/**
 * 프론트엔드 데이터 모델 - TypeScript 인터페이스 정의
 *
 * 이 모듈은 백엔드 API와 통신하기 위한 TypeScript 인터페이스를 정의합니다.
 * 모든 인터페이스는 백엔드 Pydantic 모델과 일치합니다.
 *
 * 주요 인터페이스:
 * - Message: 채팅 메시지 엔티티
 * - Session: 대화 세션 엔티티
 * - API 요청/응답 타입
 *
 * 요구사항: 2.2
 */

// =============================================================================
// 기본 엔티티 인터페이스
// =============================================================================

/**
 * 메시지 인터페이스
 *
 * 채팅 대화에서 사용자 또는 AI 어시스턴트의 메시지를 나타냅니다.
 *
 * @property id - 메시지 고유 식별자 (UUID)
 * @property session_id - 세션 식별자
 * @property content - 메시지 내용
 * @property role - 발신자 유형 ('user' 또는 'assistant')
 * @property timestamp - 메시지 생성 시간 (ISO 8601 형식)
 *
 * @example
 * const message: Message = {
 *   id: "123e4567-e89b-12d3-a456-426614174000",
 *   session_id: "session-123",
 *   content: "현재 CPU 사용률은 45%입니다.",
 *   role: "assistant",
 *   timestamp: "2024-01-15T10:30:00"
 * };
 */
export interface Message {
  /** 메시지 고유 식별자 (UUID) */
  id: string;

  /** 세션 식별자 */
  session_id: string;

  /** 메시지 내용 */
  content: string;

  /** 발신자 유형 ('user' 또는 'assistant') */
  role: 'user' | 'assistant';

  /** 메시지 생성 시간 (ISO 8601 형식) */
  timestamp: string;
}

/**
 * 세션 인터페이스
 *
 * 대화 세션을 나타냅니다. 각 세션은 여러 메시지를 포함할 수 있습니다.
 *
 * @property id - 세션 고유 식별자 (UUID)
 * @property title - 세션 제목 (예: "인프라 분석")
 * @property created_at - 세션 생성 시간 (ISO 8601 형식)
 * @property last_message_at - 마지막 메시지 시간 (ISO 8601 형식)
 *
 * @example
 * const session: Session = {
 *   id: "123e4567-e89b-12d3-a456-426614174000",
 *   title: "인프라 분석",
 *   created_at: "2024-01-15T10:00:00",
 *   last_message_at: "2024-01-15T10:30:00"
 * };
 */
export interface Session {
  /** 세션 고유 식별자 (UUID) */
  id: string;

  /** 세션 제목 */
  title: string;

  /** 세션 생성 시간 (ISO 8601 형식) */
  created_at: string;

  /** 마지막 메시지 시간 (ISO 8601 형식) */
  last_message_at: string;
}

// =============================================================================
// API 요청 타입
// =============================================================================

/**
 * 메시지 요청 인터페이스
 *
 * 사용자가 채팅 인터페이스를 통해 메시지를 전송할 때 사용됩니다.
 *
 * @property content - 메시지 내용 (필수)
 *
 * @example
 * const request: MessageRequest = {
 *   content: "CPU 사용률을 확인해주세요"
 * };
 */
export interface MessageRequest {
  /** 메시지 내용 */
  content: string;
}

/**
 * 세션 생성 요청 인터페이스
 *
 * 새로운 대화 세션을 생성할 때 사용됩니다.
 *
 * @property title - 세션 제목 (선택사항, 기본값: "새 대화")
 *
 * @example
 * const request: SessionCreateRequest = {
 *   title: "인프라 분석"
 * };
 *
 * // 또는 기본 제목 사용
 * const defaultRequest: SessionCreateRequest = {};
 */
export interface SessionCreateRequest {
  /** 세션 제목 (선택사항) */
  title?: string;
}

// =============================================================================
// API 응답 타입
// =============================================================================

/**
 * 메시지 응답 타입
 *
 * 메시지 전송 또는 조회 시 반환되는 응답입니다.
 * Message 인터페이스와 동일한 구조를 가집니다.
 */
export type MessageResponse = Message;

/**
 * 세션 응답 타입
 *
 * 세션 생성 또는 조회 시 반환되는 응답입니다.
 * Session 인터페이스와 동일한 구조를 가집니다.
 */
export type SessionResponse = Session;

/**
 * 세션 목록 응답 인터페이스
 *
 * 모든 세션의 목록을 반환합니다.
 * 세션은 마지막 메시지 시간 기준 내림차순으로 정렬됩니다.
 *
 * @property sessions - 세션 목록 (최근 메시지 순 정렬)
 * @property total_count - 총 세션 수
 *
 * @example
 * const response: SessionListResponse = {
 *   sessions: [
 *     { id: "session-1", title: "인프라 분석", ... },
 *     { id: "session-2", title: "CPU 모니터링", ... }
 *   ],
 *   total_count: 2
 * };
 */
export interface SessionListResponse {
  /** 세션 목록 (최근 메시지 순 정렬) */
  sessions: Session[];

  /** 총 세션 수 */
  total_count: number;
}

/**
 * 메시지 기록 응답 인터페이스
 *
 * 특정 세션의 전체 메시지 기록을 반환합니다.
 * 메시지는 시간순으로 정렬됩니다.
 *
 * @property session_id - 세션 식별자
 * @property messages - 메시지 목록 (시간순 정렬)
 * @property total_count - 총 메시지 수
 *
 * @example
 * const response: MessageHistoryResponse = {
 *   session_id: "session-123",
 *   messages: [
 *     { id: "msg-1", content: "CPU 사용률을 확인해주세요", role: "user", ... },
 *     { id: "msg-2", content: "현재 CPU 사용률은 45%입니다.", role: "assistant", ... }
 *   ],
 *   total_count: 2
 * };
 */
export interface MessageHistoryResponse {
  /** 세션 식별자 */
  session_id: string;

  /** 메시지 목록 (시간순 정렬) */
  messages: Message[];

  /** 총 메시지 수 */
  total_count: number;
}

// =============================================================================
// 오류 응답 타입
// =============================================================================

/**
 * 오류 상세 정보 인터페이스
 *
 * 오류에 대한 추가 정보를 제공합니다.
 *
 * @property field - 오류가 발생한 필드 (선택사항)
 * @property message - 오류 메시지
 */
export interface ErrorDetail {
  /** 오류가 발생한 필드 (선택사항) */
  field?: string;

  /** 오류 메시지 */
  message: string;
}

/**
 * 오류 정보 인터페이스
 *
 * API 오류의 상세 정보를 포함합니다.
 *
 * @property code - 오류 코드
 * @property message - 사람이 읽을 수 있는 오류 설명
 * @property details - 추가 오류 정보 목록 (선택사항)
 */
export interface ErrorInfo {
  /** 오류 코드 */
  code: string;

  /** 사람이 읽을 수 있는 오류 설명 */
  message: string;

  /** 추가 오류 정보 목록 (선택사항) */
  details?: ErrorDetail[];
}

/**
 * 오류 응답 인터페이스
 *
 * API 오류 발생 시 반환되는 응답 형식입니다.
 * 일관된 오류 응답 형식을 제공합니다.
 *
 * @property error - 오류 정보
 *
 * @example
 * const errorResponse: ErrorResponse = {
 *   error: {
 *     code: "VALIDATION_ERROR",
 *     message: "입력 검증에 실패했습니다",
 *     details: [{ field: "content", message: "필수 필드입니다" }]
 *   }
 * };
 */
export interface ErrorResponse {
  /** 오류 정보 */
  error: ErrorInfo;
}

// =============================================================================
// 헬스 체크 응답 타입
// =============================================================================

/**
 * 서비스 상태 타입
 *
 * 개별 서비스의 상태를 나타냅니다.
 */
export type ServiceStatusType = 'healthy' | 'unhealthy' | 'unknown';

/**
 * 시스템 상태 타입
 *
 * 전체 시스템의 상태를 나타냅니다.
 */
export type SystemStatusType = 'healthy' | 'unhealthy' | 'degraded';

/**
 * 서비스 상태 인터페이스
 *
 * 시스템의 개별 구성 요소 상태를 나타냅니다.
 *
 * @property name - 서비스 이름
 * @property status - 서비스 상태 ('healthy', 'unhealthy', 'unknown')
 * @property message - 상태 메시지 (선택사항)
 */
export interface ServiceStatus {
  /** 서비스 이름 */
  name: string;

  /** 서비스 상태 */
  status: ServiceStatusType;

  /** 상태 메시지 (선택사항) */
  message?: string;
}

/**
 * 헬스 체크 응답 인터페이스
 *
 * 시스템 전체의 상태 정보를 반환합니다.
 * 각 구성 요소(데이터베이스, MCP 서버, Bedrock 등)의 상태를 포함합니다.
 *
 * @property status - 전체 시스템 상태 ('healthy', 'unhealthy', 'degraded')
 * @property service - 서비스 이름
 * @property version - 서비스 버전
 * @property timestamp - 헬스 체크 시간 (ISO 8601 형식)
 * @property components - 개별 구성 요소 상태 목록 (선택사항)
 *
 * @example
 * const healthResponse: HealthCheckResponse = {
 *   status: "healthy",
 *   service: "ai-chatbot-backend",
 *   version: "0.1.0",
 *   timestamp: "2024-01-15T10:30:00",
 *   components: [
 *     { name: "database", status: "healthy", message: "연결 성공" },
 *     { name: "mcp_grafana", status: "healthy" },
 *     { name: "mcp_cloudwatch", status: "healthy" },
 *     { name: "bedrock", status: "healthy" }
 *   ]
 * };
 */
export interface HealthCheckResponse {
  /** 전체 시스템 상태 */
  status: SystemStatusType;

  /** 서비스 이름 */
  service: string;

  /** 서비스 버전 */
  version: string;

  /** 헬스 체크 시간 (ISO 8601 형식) */
  timestamp: string;

  /** 개별 구성 요소 상태 목록 (선택사항) */
  components?: ServiceStatus[];
}

// =============================================================================
// 유틸리티 타입
// =============================================================================

/**
 * 메시지 역할 타입
 *
 * 메시지 발신자의 유형을 나타냅니다.
 */
export type MessageRole = 'user' | 'assistant';

/**
 * API 응답 래퍼 타입
 *
 * 성공 또는 오류 응답을 나타내는 유니온 타입입니다.
 *
 * @template T - 성공 시 반환되는 데이터 타입
 */
export type ApiResponse<T> = T | ErrorResponse;

/**
 * 타입 가드: ErrorResponse 여부 확인
 *
 * 응답이 오류 응답인지 확인합니다.
 *
 * @param response - 확인할 응답 객체
 * @returns 오류 응답이면 true, 아니면 false
 *
 * @example
 * const response = await api.sendMessage(request);
 * if (isErrorResponse(response)) {
 *   console.error(response.error.message);
 * } else {
 *   console.log(response.content);
 * }
 */
export function isErrorResponse(response: unknown): response is ErrorResponse {
  return (
    typeof response === 'object' &&
    response !== null &&
    'error' in response &&
    typeof (response as ErrorResponse).error === 'object' &&
    (response as ErrorResponse).error !== null &&
    'code' in (response as ErrorResponse).error &&
    'message' in (response as ErrorResponse).error
  );
}
