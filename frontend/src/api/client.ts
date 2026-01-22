/**
 * API 클라이언트 모듈
 *
 * 백엔드 서버와 통신하기 위한 HTTP 클라이언트 클래스를 제공합니다.
 * 모든 API 호출에 대한 오류 처리 및 재시도 로직을 포함합니다.
 *
 * 주요 기능:
 * - 메시지 전송 및 수신
 * - 세션 생성 및 관리
 * - 대화 기록 조회
 * - 헬스 체크
 *
 * 요구사항: 2.3, 3.1, 3.2, 3.3
 */

import {
  Message,
  MessageRequest,
  MessageResponse,
  MessageHistoryResponse,
  Session,
  SessionCreateRequest,
  SessionResponse,
  SessionListResponse,
  HealthCheckResponse,
  ErrorResponse,
  isErrorResponse,
} from '../types';

// 타입 재내보내기 (사용되지 않는 import 경고 방지)
export type { Message, Session };

// =============================================================================
// 상수 정의
// =============================================================================

/** 기본 API 서버 URL */
const DEFAULT_BASE_URL = 'http://localhost:8000';

/** 최대 재시도 횟수 */
const MAX_RETRIES = 3;

/** 기본 재시도 지연 시간 (밀리초) */
const BASE_RETRY_DELAY_MS = 1000;

/** 요청 타임아웃 (밀리초) */
const REQUEST_TIMEOUT_MS = 30000;

// =============================================================================
// 오류 클래스 정의
// =============================================================================

/**
 * API 오류 클래스
 *
 * API 호출 중 발생하는 오류를 나타냅니다.
 * HTTP 상태 코드와 오류 응답 정보를 포함합니다.
 */
export class ApiError extends Error {
  /** HTTP 상태 코드 */
  public readonly statusCode: number;

  /** 오류 코드 */
  public readonly errorCode: string;

  /** 원본 오류 응답 */
  public readonly errorResponse?: ErrorResponse;

  constructor(
    message: string,
    statusCode: number,
    errorCode: string = 'UNKNOWN_ERROR',
    errorResponse?: ErrorResponse
  ) {
    super(message);
    this.name = 'ApiError';
    this.statusCode = statusCode;
    this.errorCode = errorCode;
    this.errorResponse = errorResponse;
  }
}

/**
 * 네트워크 오류 클래스
 *
 * 네트워크 연결 실패 시 발생하는 오류를 나타냅니다.
 */
export class NetworkError extends Error {
  /** 원본 오류 */
  public readonly originalError?: Error;

  constructor(message: string, originalError?: Error) {
    super(message);
    this.name = 'NetworkError';
    this.originalError = originalError;
  }
}

/**
 * 타임아웃 오류 클래스
 *
 * 요청 타임아웃 시 발생하는 오류를 나타냅니다.
 */
export class TimeoutError extends Error {
  /** 타임아웃 시간 (밀리초) */
  public readonly timeoutMs: number;

  constructor(message: string, timeoutMs: number) {
    super(message);
    this.name = 'TimeoutError';
    this.timeoutMs = timeoutMs;
  }
}

// =============================================================================
// 유틸리티 함수
// =============================================================================

/**
 * 지정된 시간만큼 대기합니다.
 *
 * @param ms - 대기 시간 (밀리초)
 * @returns Promise
 */
function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * 지수 백오프 지연 시간을 계산합니다.
 *
 * @param attempt - 현재 시도 횟수 (0부터 시작)
 * @param baseDelay - 기본 지연 시간 (밀리초)
 * @returns 지연 시간 (밀리초)
 */
function calculateBackoffDelay(attempt: number, baseDelay: number): number {
  // 지수 백오프: baseDelay * 2^attempt + 랜덤 지터
  const exponentialDelay = baseDelay * Math.pow(2, attempt);
  const jitter = Math.random() * baseDelay * 0.5;
  return exponentialDelay + jitter;
}

/**
 * 재시도 가능한 HTTP 상태 코드인지 확인합니다.
 *
 * @param statusCode - HTTP 상태 코드
 * @returns 재시도 가능하면 true
 */
function isRetryableStatusCode(statusCode: number): boolean {
  // 5xx 서버 오류 및 429 (Too Many Requests)는 재시도 가능
  return statusCode >= 500 || statusCode === 429;
}

// =============================================================================
// ChatAPIClient 클래스
// =============================================================================

/**
 * 채팅 API 클라이언트 클래스
 *
 * 백엔드 서버와 통신하기 위한 HTTP 클라이언트입니다.
 * 모든 API 호출에 대한 오류 처리 및 재시도 로직을 포함합니다.
 *
 * @example
 * const client = new ChatAPIClient('http://localhost:8000');
 *
 * // 세션 생성
 * const session = await client.createSession('새 대화');
 *
 * // 메시지 전송
 * const response = await client.sendMessage(session.id, 'CPU 사용률을 확인해주세요');
 *
 * // 대화 기록 조회
 * const history = await client.getSessionHistory(session.id);
 */
export class ChatAPIClient {
  /** API 서버 기본 URL */
  private readonly baseUrl: string;

  /** 최대 재시도 횟수 */
  private readonly maxRetries: number;

  /** 기본 재시도 지연 시간 (밀리초) */
  private readonly baseRetryDelay: number;

  /** 요청 타임아웃 (밀리초) */
  private readonly timeout: number;

  /**
   * ChatAPIClient 생성자
   *
   * @param baseUrl - API 서버 기본 URL (기본값: 'http://localhost:8000')
   * @param options - 추가 옵션
   * @param options.maxRetries - 최대 재시도 횟수 (기본값: 3)
   * @param options.baseRetryDelay - 기본 재시도 지연 시간 (기본값: 1000ms)
   * @param options.timeout - 요청 타임아웃 (기본값: 30000ms)
   */
  constructor(
    baseUrl: string = DEFAULT_BASE_URL,
    options: {
      maxRetries?: number;
      baseRetryDelay?: number;
      timeout?: number;
    } = {}
  ) {
    // URL 끝의 슬래시 제거
    this.baseUrl = baseUrl.replace(/\/+$/, '');
    this.maxRetries = options.maxRetries ?? MAX_RETRIES;
    this.baseRetryDelay = options.baseRetryDelay ?? BASE_RETRY_DELAY_MS;
    this.timeout = options.timeout ?? REQUEST_TIMEOUT_MS;
  }

  // ===========================================================================
  // 공개 API 메서드
  // ===========================================================================

  /**
   * 메시지를 전송하고 AI 응답을 받습니다.
   *
   * @param sessionId - 세션 ID
   * @param content - 메시지 내용
   * @returns AI 응답 메시지
   * @throws {ApiError} API 오류 발생 시
   * @throws {NetworkError} 네트워크 오류 발생 시
   * @throws {TimeoutError} 요청 타임아웃 시
   *
   * @example
   * const response = await client.sendMessage('session-123', 'CPU 사용률을 확인해주세요');
   * console.log(response.content); // AI 응답 내용
   */
  async sendMessage(sessionId: string, content: string): Promise<MessageResponse> {
    const url = `${this.baseUrl}/api/sessions/${encodeURIComponent(sessionId)}/messages`;
    const body: MessageRequest = { content };

    const response = await this.requestWithRetry<MessageResponse>(url, {
      method: 'POST',
      body: JSON.stringify(body),
    });

    return response;
  }

  /**
   * 세션의 대화 기록을 조회합니다.
   *
   * @param sessionId - 세션 ID
   * @returns 메시지 기록 응답
   * @throws {ApiError} API 오류 발생 시
   * @throws {NetworkError} 네트워크 오류 발생 시
   * @throws {TimeoutError} 요청 타임아웃 시
   *
   * @example
   * const history = await client.getSessionHistory('session-123');
   * history.messages.forEach(msg => console.log(`${msg.role}: ${msg.content}`));
   */
  async getSessionHistory(sessionId: string): Promise<MessageHistoryResponse> {
    const url = `${this.baseUrl}/api/sessions/${encodeURIComponent(sessionId)}/messages`;

    const response = await this.requestWithRetry<MessageHistoryResponse>(url, {
      method: 'GET',
    });

    return response;
  }

  /**
   * 새로운 대화 세션을 생성합니다.
   *
   * @param title - 세션 제목 (선택사항, 기본값: "새 대화")
   * @returns 생성된 세션 정보
   * @throws {ApiError} API 오류 발생 시
   * @throws {NetworkError} 네트워크 오류 발생 시
   * @throws {TimeoutError} 요청 타임아웃 시
   *
   * @example
   * const session = await client.createSession('인프라 분석');
   * console.log(session.id); // 새 세션 ID
   */
  async createSession(title?: string): Promise<SessionResponse> {
    const url = `${this.baseUrl}/api/sessions`;
    const body: SessionCreateRequest = title ? { title } : {};

    const response = await this.requestWithRetry<SessionResponse>(url, {
      method: 'POST',
      body: JSON.stringify(body),
    });

    return response;
  }

  /**
   * 모든 세션 목록을 조회합니다.
   *
   * @returns 세션 목록 응답
   * @throws {ApiError} API 오류 발생 시
   * @throws {NetworkError} 네트워크 오류 발생 시
   * @throws {TimeoutError} 요청 타임아웃 시
   *
   * @example
   * const { sessions, total_count } = await client.listSessions();
   * sessions.forEach(session => console.log(session.title));
   */
  async listSessions(): Promise<SessionListResponse> {
    const url = `${this.baseUrl}/api/sessions`;

    const response = await this.requestWithRetry<SessionListResponse>(url, {
      method: 'GET',
    });

    return response;
  }

  /**
   * 서버 헬스 체크를 수행합니다.
   *
   * @returns 헬스 체크 응답
   * @throws {ApiError} API 오류 발생 시
   * @throws {NetworkError} 네트워크 오류 발생 시
   * @throws {TimeoutError} 요청 타임아웃 시
   *
   * @example
   * const health = await client.healthCheck();
   * if (health.status === 'healthy') {
   *   console.log('서버가 정상입니다');
   * }
   */
  async healthCheck(): Promise<HealthCheckResponse> {
    const url = `${this.baseUrl}/health`;

    const response = await this.requestWithRetry<HealthCheckResponse>(url, {
      method: 'GET',
    });

    return response;
  }

  // ===========================================================================
  // 비공개 헬퍼 메서드
  // ===========================================================================

  /**
   * 재시도 로직이 포함된 HTTP 요청을 수행합니다.
   *
   * @param url - 요청 URL
   * @param options - fetch 옵션
   * @returns 응답 데이터
   * @throws {ApiError} API 오류 발생 시
   * @throws {NetworkError} 네트워크 오류 발생 시
   * @throws {TimeoutError} 요청 타임아웃 시
   */
  private async requestWithRetry<T>(
    url: string,
    options: RequestInit
  ): Promise<T> {
    let lastError: Error | null = null;

    for (let attempt = 0; attempt <= this.maxRetries; attempt++) {
      try {
        const response = await this.request<T>(url, options);
        return response;
      } catch (error) {
        lastError = error as Error;

        // 재시도 가능한 오류인지 확인
        const shouldRetry = this.shouldRetry(error as Error, attempt);

        if (!shouldRetry) {
          throw error;
        }

        // 지수 백오프 대기
        const delay = calculateBackoffDelay(attempt, this.baseRetryDelay);
        console.warn(
          `API 요청 실패 (시도 ${attempt + 1}/${this.maxRetries + 1}), ` +
            `${Math.round(delay)}ms 후 재시도...`
        );
        await sleep(delay);
      }
    }

    // 모든 재시도 실패
    throw lastError;
  }

  /**
   * HTTP 요청을 수행합니다.
   *
   * @param url - 요청 URL
   * @param options - fetch 옵션
   * @returns 응답 데이터
   * @throws {ApiError} API 오류 발생 시
   * @throws {NetworkError} 네트워크 오류 발생 시
   * @throws {TimeoutError} 요청 타임아웃 시
   */
  private async request<T>(url: string, options: RequestInit): Promise<T> {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.timeout);

    try {
      const response = await fetch(url, {
        ...options,
        headers: {
          'Content-Type': 'application/json',
          Accept: 'application/json',
          ...options.headers,
        },
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      // 응답 본문 파싱
      const data = await this.parseResponse(response);

      // HTTP 오류 처리
      if (!response.ok) {
        throw this.createApiError(response.status, data);
      }

      return data as T;
    } catch (error) {
      clearTimeout(timeoutId);

      // AbortError는 타임아웃으로 처리
      if (error instanceof Error && error.name === 'AbortError') {
        throw new TimeoutError(
          `요청 타임아웃: ${this.timeout}ms 초과`,
          this.timeout
        );
      }

      // TypeError는 네트워크 오류로 처리 (fetch 실패)
      if (error instanceof TypeError) {
        throw new NetworkError(
          `네트워크 오류: ${error.message}`,
          error
        );
      }

      // 이미 처리된 오류는 그대로 전달
      throw error;
    }
  }

  /**
   * 응답 본문을 파싱합니다.
   *
   * @param response - fetch Response 객체
   * @returns 파싱된 JSON 데이터
   */
  private async parseResponse(response: Response): Promise<unknown> {
    const contentType = response.headers.get('content-type');

    if (contentType && contentType.includes('application/json')) {
      try {
        return await response.json();
      } catch {
        // JSON 파싱 실패 시 빈 객체 반환
        return {};
      }
    }

    // JSON이 아닌 경우 텍스트로 처리
    const text = await response.text();
    return { message: text };
  }

  /**
   * API 오류 객체를 생성합니다.
   *
   * @param statusCode - HTTP 상태 코드
   * @param data - 응답 데이터
   * @returns ApiError 객체
   */
  private createApiError(statusCode: number, data: unknown): ApiError {
    // ErrorResponse 형식인 경우
    if (isErrorResponse(data)) {
      return new ApiError(
        data.error.message,
        statusCode,
        data.error.code,
        data
      );
    }

    // 일반 오류 메시지
    const message = this.getErrorMessage(statusCode);
    return new ApiError(message, statusCode);
  }

  /**
   * HTTP 상태 코드에 따른 오류 메시지를 반환합니다.
   *
   * @param statusCode - HTTP 상태 코드
   * @returns 오류 메시지
   */
  private getErrorMessage(statusCode: number): string {
    switch (statusCode) {
      case 400:
        return '잘못된 요청입니다';
      case 401:
        return '인증이 필요합니다';
      case 403:
        return '접근이 거부되었습니다';
      case 404:
        return '리소스를 찾을 수 없습니다';
      case 409:
        return '리소스 충돌이 발생했습니다';
      case 422:
        return '요청 데이터 검증에 실패했습니다';
      case 429:
        return '요청이 너무 많습니다. 잠시 후 다시 시도해주세요';
      case 500:
        return '서버 내부 오류가 발생했습니다';
      case 502:
        return '게이트웨이 오류가 발생했습니다';
      case 503:
        return '서비스를 사용할 수 없습니다';
      case 504:
        return '게이트웨이 타임아웃이 발생했습니다';
      default:
        return `HTTP 오류 ${statusCode}`;
    }
  }

  /**
   * 재시도 여부를 결정합니다.
   *
   * @param error - 발생한 오류
   * @param attempt - 현재 시도 횟수
   * @returns 재시도 가능하면 true
   */
  private shouldRetry(error: Error, attempt: number): boolean {
    // 최대 재시도 횟수 초과
    if (attempt >= this.maxRetries) {
      return false;
    }

    // 네트워크 오류는 재시도
    if (error instanceof NetworkError) {
      return true;
    }

    // 타임아웃 오류는 재시도
    if (error instanceof TimeoutError) {
      return true;
    }

    // API 오류 중 재시도 가능한 상태 코드만 재시도
    if (error instanceof ApiError) {
      return isRetryableStatusCode(error.statusCode);
    }

    // 기타 오류는 재시도하지 않음
    return false;
  }
}

// =============================================================================
// 기본 클라이언트 인스턴스
// =============================================================================

/**
 * 기본 API 클라이언트 인스턴스
 *
 * 환경 변수 REACT_APP_API_URL이 설정되어 있으면 해당 URL을 사용하고,
 * 그렇지 않으면 기본 URL (http://localhost:8000)을 사용합니다.
 *
 * @example
 * import { defaultClient } from './api/client';
 *
 * const session = await defaultClient.createSession();
 */
export const defaultClient = new ChatAPIClient(
  process.env.REACT_APP_API_URL || DEFAULT_BASE_URL
);

// =============================================================================
// 내보내기
// =============================================================================

export default ChatAPIClient;
