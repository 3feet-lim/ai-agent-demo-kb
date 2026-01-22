/**
 * API 클라이언트 단위 테스트
 *
 * ChatAPIClient 클래스의 모든 메서드에 대한 단위 테스트를 포함합니다.
 * 성공적인 API 호출, 오류 처리, 재시도 로직, 타임아웃 처리를 테스트합니다.
 *
 * 요구사항: 2.3, 3.1, 3.2
 */

import ChatAPIClient, {
  ApiError,
  NetworkError,
  TimeoutError,
} from '../src/api/client';
import {
  Message,
  Session,
  SessionListResponse,
  MessageHistoryResponse,
  HealthCheckResponse,
  ErrorResponse,
} from '../src/types';

// =============================================================================
// 테스트 유틸리티 및 모의 데이터
// =============================================================================

/**
 * 모의 fetch 함수 타입
 */
type MockFetch = jest.Mock<Promise<Response>>;

/**
 * 전역 fetch 모의 설정
 */
const mockFetch: MockFetch = jest.fn();
global.fetch = mockFetch;

/**
 * 테스트용 기본 URL
 */
const TEST_BASE_URL = 'http://test-api.example.com';

/**
 * 모의 세션 데이터 생성
 */
function createMockSession(overrides: Partial<Session> = {}): Session {
  return {
    id: 'session-123',
    title: '테스트 세션',
    created_at: '2024-01-15T10:00:00Z',
    last_message_at: '2024-01-15T10:30:00Z',
    ...overrides,
  };
}


/**
 * 모의 메시지 데이터 생성
 */
function createMockMessage(overrides: Partial<Message> = {}): Message {
  return {
    id: 'msg-123',
    session_id: 'session-123',
    content: '테스트 메시지입니다',
    role: 'assistant',
    timestamp: '2024-01-15T10:30:00Z',
    ...overrides,
  };
}

/**
 * 성공 응답 생성 헬퍼
 */
function createSuccessResponse<T>(data: T): Response {
  return {
    ok: true,
    status: 200,
    headers: new Headers({ 'content-type': 'application/json' }),
    json: () => Promise.resolve(data),
    text: () => Promise.resolve(JSON.stringify(data)),
  } as Response;
}

/**
 * 오류 응답 생성 헬퍼
 */
function createErrorResponse(
  status: number,
  errorData?: ErrorResponse
): Response {
  return {
    ok: false,
    status,
    headers: new Headers({ 'content-type': 'application/json' }),
    json: () => Promise.resolve(errorData || {}),
    text: () => Promise.resolve(JSON.stringify(errorData || {})),
  } as Response;
}

/**
 * 네트워크 오류 시뮬레이션
 */
function simulateNetworkError(): never {
  throw new TypeError('Failed to fetch');
}

/**
 * 타임아웃 시뮬레이션을 위한 AbortError 생성
 */
function createAbortError(): Error {
  const error = new Error('The operation was aborted');
  error.name = 'AbortError';
  return error;
}

// =============================================================================
// 테스트 시작
// =============================================================================

describe('ChatAPIClient', () => {
  let client: ChatAPIClient;

  beforeEach(() => {
    // 각 테스트 전에 모의 함수 초기화
    mockFetch.mockClear();
    // 짧은 재시도 지연으로 클라이언트 생성 (테스트 속도 향상)
    client = new ChatAPIClient(TEST_BASE_URL, {
      maxRetries: 2,
      baseRetryDelay: 10,
      timeout: 5000,
    });
  });

  // ===========================================================================
  // 생성자 테스트
  // ===========================================================================

  describe('constructor', () => {
    it('기본 URL로 클라이언트를 생성해야 합니다', () => {
      const defaultClient = new ChatAPIClient();
      expect(defaultClient).toBeInstanceOf(ChatAPIClient);
    });

    it('사용자 정의 URL로 클라이언트를 생성해야 합니다', () => {
      const customClient = new ChatAPIClient('http://custom-api.com');
      expect(customClient).toBeInstanceOf(ChatAPIClient);
    });

    it('URL 끝의 슬래시를 제거해야 합니다', async () => {
      const clientWithSlash = new ChatAPIClient('http://api.com/', {
        maxRetries: 0,
      });
      mockFetch.mockResolvedValueOnce(
        createSuccessResponse({ sessions: [], total_count: 0 })
      );

      await clientWithSlash.listSessions();

      expect(mockFetch).toHaveBeenCalledWith(
        'http://api.com/api/sessions',
        expect.any(Object)
      );
    });

    it('사용자 정의 옵션으로 클라이언트를 생성해야 합니다', () => {
      const customClient = new ChatAPIClient(TEST_BASE_URL, {
        maxRetries: 5,
        baseRetryDelay: 2000,
        timeout: 60000,
      });
      expect(customClient).toBeInstanceOf(ChatAPIClient);
    });
  });


  // ===========================================================================
  // sendMessage 테스트
  // ===========================================================================

  describe('sendMessage', () => {
    const sessionId = 'session-123';
    const content = 'CPU 사용률을 확인해주세요';

    describe('성공 케이스', () => {
      it('메시지를 성공적으로 전송하고 응답을 반환해야 합니다', async () => {
        const mockResponse = createMockMessage({
          content: '현재 CPU 사용률은 45%입니다.',
          role: 'assistant',
        });
        mockFetch.mockResolvedValueOnce(createSuccessResponse(mockResponse));

        const result = await client.sendMessage(sessionId, content);

        expect(result).toEqual(mockResponse);
        expect(mockFetch).toHaveBeenCalledWith(
          `${TEST_BASE_URL}/api/sessions/${sessionId}/messages`,
          expect.objectContaining({
            method: 'POST',
            body: JSON.stringify({ content }),
            headers: expect.objectContaining({
              'Content-Type': 'application/json',
            }),
          })
        );
      });

      it('세션 ID에 특수 문자가 있어도 올바르게 인코딩해야 합니다', async () => {
        const specialSessionId = 'session/with spaces&special';
        const mockResponse = createMockMessage();
        mockFetch.mockResolvedValueOnce(createSuccessResponse(mockResponse));

        await client.sendMessage(specialSessionId, content);

        expect(mockFetch).toHaveBeenCalledWith(
          expect.stringContaining(encodeURIComponent(specialSessionId)),
          expect.any(Object)
        );
      });
    });

    describe('오류 케이스', () => {
      it('400 오류 시 ApiError를 발생시켜야 합니다', async () => {
        const errorResponse: ErrorResponse = {
          error: {
            code: 'VALIDATION_ERROR',
            message: '메시지 내용이 비어있습니다',
          },
        };
        mockFetch.mockResolvedValueOnce(createErrorResponse(400, errorResponse));

        await expect(client.sendMessage(sessionId, '')).rejects.toThrow(ApiError);
        await expect(client.sendMessage(sessionId, '')).rejects.toMatchObject({
          statusCode: 400,
          errorCode: 'VALIDATION_ERROR',
        });
      });

      it('404 오류 시 ApiError를 발생시켜야 합니다', async () => {
        const errorResponse: ErrorResponse = {
          error: {
            code: 'SESSION_NOT_FOUND',
            message: '세션을 찾을 수 없습니다',
          },
        };
        mockFetch.mockResolvedValueOnce(createErrorResponse(404, errorResponse));

        await expect(
          client.sendMessage('invalid-session', content)
        ).rejects.toThrow(ApiError);
      });
    });
  });


  // ===========================================================================
  // getSessionHistory 테스트
  // ===========================================================================

  describe('getSessionHistory', () => {
    const sessionId = 'session-123';

    describe('성공 케이스', () => {
      it('세션 기록을 성공적으로 조회해야 합니다', async () => {
        const mockResponse: MessageHistoryResponse = {
          session_id: sessionId,
          messages: [
            createMockMessage({ id: 'msg-1', role: 'user', content: '질문입니다' }),
            createMockMessage({ id: 'msg-2', role: 'assistant', content: '답변입니다' }),
          ],
          total_count: 2,
        };
        mockFetch.mockResolvedValueOnce(createSuccessResponse(mockResponse));

        const result = await client.getSessionHistory(sessionId);

        expect(result).toEqual(mockResponse);
        expect(result.messages).toHaveLength(2);
        expect(mockFetch).toHaveBeenCalledWith(
          `${TEST_BASE_URL}/api/sessions/${sessionId}/messages`,
          expect.objectContaining({
            method: 'GET',
          })
        );
      });

      it('빈 기록을 올바르게 처리해야 합니다', async () => {
        const mockResponse: MessageHistoryResponse = {
          session_id: sessionId,
          messages: [],
          total_count: 0,
        };
        mockFetch.mockResolvedValueOnce(createSuccessResponse(mockResponse));

        const result = await client.getSessionHistory(sessionId);

        expect(result.messages).toHaveLength(0);
        expect(result.total_count).toBe(0);
      });
    });

    describe('오류 케이스', () => {
      it('존재하지 않는 세션 조회 시 ApiError를 발생시켜야 합니다', async () => {
        const errorResponse: ErrorResponse = {
          error: {
            code: 'SESSION_NOT_FOUND',
            message: '세션을 찾을 수 없습니다',
          },
        };
        mockFetch.mockResolvedValueOnce(createErrorResponse(404, errorResponse));

        await expect(
          client.getSessionHistory('non-existent-session')
        ).rejects.toThrow(ApiError);
      });
    });
  });

  // ===========================================================================
  // createSession 테스트
  // ===========================================================================

  describe('createSession', () => {
    describe('성공 케이스', () => {
      it('제목 없이 세션을 생성해야 합니다', async () => {
        const mockSession = createMockSession({ title: '새 대화' });
        mockFetch.mockResolvedValueOnce(createSuccessResponse(mockSession));

        const result = await client.createSession();

        expect(result).toEqual(mockSession);
        expect(mockFetch).toHaveBeenCalledWith(
          `${TEST_BASE_URL}/api/sessions`,
          expect.objectContaining({
            method: 'POST',
            body: JSON.stringify({}),
          })
        );
      });

      it('제목과 함께 세션을 생성해야 합니다', async () => {
        const title = '인프라 분석';
        const mockSession = createMockSession({ title });
        mockFetch.mockResolvedValueOnce(createSuccessResponse(mockSession));

        const result = await client.createSession(title);

        expect(result.title).toBe(title);
        expect(mockFetch).toHaveBeenCalledWith(
          `${TEST_BASE_URL}/api/sessions`,
          expect.objectContaining({
            body: JSON.stringify({ title }),
          })
        );
      });
    });

    describe('오류 케이스', () => {
      it('서버 오류 시 ApiError를 발생시켜야 합니다', async () => {
        mockFetch.mockResolvedValueOnce(createErrorResponse(500));

        await expect(client.createSession()).rejects.toThrow(ApiError);
      });
    });
  });


  // ===========================================================================
  // listSessions 테스트
  // ===========================================================================

  describe('listSessions', () => {
    describe('성공 케이스', () => {
      it('세션 목록을 성공적으로 조회해야 합니다', async () => {
        const mockResponse: SessionListResponse = {
          sessions: [
            createMockSession({ id: 'session-1', title: '세션 1' }),
            createMockSession({ id: 'session-2', title: '세션 2' }),
          ],
          total_count: 2,
        };
        mockFetch.mockResolvedValueOnce(createSuccessResponse(mockResponse));

        const result = await client.listSessions();

        expect(result.sessions).toHaveLength(2);
        expect(result.total_count).toBe(2);
        expect(mockFetch).toHaveBeenCalledWith(
          `${TEST_BASE_URL}/api/sessions`,
          expect.objectContaining({
            method: 'GET',
          })
        );
      });

      it('빈 세션 목록을 올바르게 처리해야 합니다', async () => {
        const mockResponse: SessionListResponse = {
          sessions: [],
          total_count: 0,
        };
        mockFetch.mockResolvedValueOnce(createSuccessResponse(mockResponse));

        const result = await client.listSessions();

        expect(result.sessions).toHaveLength(0);
        expect(result.total_count).toBe(0);
      });
    });

    describe('오류 케이스', () => {
      it('서버 오류 시 ApiError를 발생시켜야 합니다', async () => {
        mockFetch.mockResolvedValueOnce(createErrorResponse(500));

        await expect(client.listSessions()).rejects.toThrow(ApiError);
      });
    });
  });

  // ===========================================================================
  // healthCheck 테스트
  // ===========================================================================

  describe('healthCheck', () => {
    describe('성공 케이스', () => {
      it('헬스 체크를 성공적으로 수행해야 합니다', async () => {
        const mockResponse: HealthCheckResponse = {
          status: 'healthy',
          service: 'ai-chatbot-backend',
          version: '0.1.0',
          timestamp: '2024-01-15T10:30:00Z',
          components: [
            { name: 'database', status: 'healthy' },
            { name: 'mcp_grafana', status: 'healthy' },
          ],
        };
        mockFetch.mockResolvedValueOnce(createSuccessResponse(mockResponse));

        const result = await client.healthCheck();

        expect(result.status).toBe('healthy');
        expect(result.components).toHaveLength(2);
        expect(mockFetch).toHaveBeenCalledWith(
          `${TEST_BASE_URL}/health`,
          expect.objectContaining({
            method: 'GET',
          })
        );
      });

      it('비정상 상태를 올바르게 반환해야 합니다', async () => {
        const mockResponse: HealthCheckResponse = {
          status: 'unhealthy',
          service: 'ai-chatbot-backend',
          version: '0.1.0',
          timestamp: '2024-01-15T10:30:00Z',
          components: [
            { name: 'database', status: 'unhealthy', message: '연결 실패' },
          ],
        };
        mockFetch.mockResolvedValueOnce(createSuccessResponse(mockResponse));

        const result = await client.healthCheck();

        expect(result.status).toBe('unhealthy');
      });
    });

    describe('오류 케이스', () => {
      it('서버 다운 시 ApiError를 발생시켜야 합니다', async () => {
        mockFetch.mockResolvedValueOnce(createErrorResponse(503));

        await expect(client.healthCheck()).rejects.toThrow(ApiError);
      });
    });
  });


  // ===========================================================================
  // 재시도 로직 테스트
  // ===========================================================================

  describe('재시도 로직', () => {
    describe('네트워크 오류 재시도', () => {
      it('네트워크 오류 시 재시도해야 합니다', async () => {
        const mockSession = createMockSession();
        
        // 첫 번째, 두 번째 호출은 네트워크 오류, 세 번째는 성공
        mockFetch
          .mockRejectedValueOnce(new TypeError('Failed to fetch'))
          .mockRejectedValueOnce(new TypeError('Failed to fetch'))
          .mockResolvedValueOnce(createSuccessResponse(mockSession));

        const result = await client.createSession();

        expect(result).toEqual(mockSession);
        expect(mockFetch).toHaveBeenCalledTimes(3);
      });

      it('최대 재시도 횟수 초과 시 NetworkError를 발생시켜야 합니다', async () => {
        // 모든 호출이 네트워크 오류
        mockFetch.mockRejectedValue(new TypeError('Failed to fetch'));

        await expect(client.createSession()).rejects.toThrow(NetworkError);
        // maxRetries가 2이므로 총 3번 호출 (초기 1회 + 재시도 2회)
        expect(mockFetch).toHaveBeenCalledTimes(3);
      });
    });

    describe('5xx 서버 오류 재시도', () => {
      it('500 오류 시 재시도해야 합니다', async () => {
        const mockSession = createMockSession();
        
        mockFetch
          .mockResolvedValueOnce(createErrorResponse(500))
          .mockResolvedValueOnce(createErrorResponse(502))
          .mockResolvedValueOnce(createSuccessResponse(mockSession));

        const result = await client.createSession();

        expect(result).toEqual(mockSession);
        expect(mockFetch).toHaveBeenCalledTimes(3);
      });

      it('503 오류 시 재시도해야 합니다', async () => {
        const mockSession = createMockSession();
        
        mockFetch
          .mockResolvedValueOnce(createErrorResponse(503))
          .mockResolvedValueOnce(createSuccessResponse(mockSession));

        const result = await client.createSession();

        expect(result).toEqual(mockSession);
        expect(mockFetch).toHaveBeenCalledTimes(2);
      });

      it('429 (Too Many Requests) 오류 시 재시도해야 합니다', async () => {
        const mockSession = createMockSession();
        
        mockFetch
          .mockResolvedValueOnce(createErrorResponse(429))
          .mockResolvedValueOnce(createSuccessResponse(mockSession));

        const result = await client.createSession();

        expect(result).toEqual(mockSession);
        expect(mockFetch).toHaveBeenCalledTimes(2);
      });
    });

    describe('재시도하지 않는 오류', () => {
      it('400 오류는 재시도하지 않아야 합니다', async () => {
        mockFetch.mockResolvedValue(createErrorResponse(400));

        await expect(client.createSession()).rejects.toThrow(ApiError);
        expect(mockFetch).toHaveBeenCalledTimes(1);
      });

      it('401 오류는 재시도하지 않아야 합니다', async () => {
        mockFetch.mockResolvedValue(createErrorResponse(401));

        await expect(client.createSession()).rejects.toThrow(ApiError);
        expect(mockFetch).toHaveBeenCalledTimes(1);
      });

      it('403 오류는 재시도하지 않아야 합니다', async () => {
        mockFetch.mockResolvedValue(createErrorResponse(403));

        await expect(client.createSession()).rejects.toThrow(ApiError);
        expect(mockFetch).toHaveBeenCalledTimes(1);
      });

      it('404 오류는 재시도하지 않아야 합니다', async () => {
        mockFetch.mockResolvedValue(createErrorResponse(404));

        await expect(client.createSession()).rejects.toThrow(ApiError);
        expect(mockFetch).toHaveBeenCalledTimes(1);
      });
    });
  });


  // ===========================================================================
  // 타임아웃 처리 테스트
  // ===========================================================================

  describe('타임아웃 처리', () => {
    it('요청 타임아웃 시 TimeoutError를 발생시켜야 합니다', async () => {
      // AbortError를 발생시켜 타임아웃 시뮬레이션
      mockFetch.mockRejectedValue(createAbortError());

      await expect(client.createSession()).rejects.toThrow(TimeoutError);
    });

    it('타임아웃 후 재시도해야 합니다', async () => {
      const mockSession = createMockSession();
      
      mockFetch
        .mockRejectedValueOnce(createAbortError())
        .mockResolvedValueOnce(createSuccessResponse(mockSession));

      const result = await client.createSession();

      expect(result).toEqual(mockSession);
      expect(mockFetch).toHaveBeenCalledTimes(2);
    });

    it('타임아웃 오류에 타임아웃 시간이 포함되어야 합니다', async () => {
      mockFetch.mockRejectedValue(createAbortError());

      try {
        await client.createSession();
        fail('TimeoutError가 발생해야 합니다');
      } catch (error) {
        expect(error).toBeInstanceOf(TimeoutError);
        expect((error as TimeoutError).timeoutMs).toBe(5000);
      }
    });
  });

  // ===========================================================================
  // 오류 응답 파싱 테스트
  // ===========================================================================

  describe('오류 응답 파싱', () => {
    it('ErrorResponse 형식의 오류를 올바르게 파싱해야 합니다', async () => {
      const errorResponse: ErrorResponse = {
        error: {
          code: 'VALIDATION_ERROR',
          message: '입력 검증에 실패했습니다',
          details: [{ field: 'content', message: '필수 필드입니다' }],
        },
      };
      mockFetch.mockResolvedValueOnce(createErrorResponse(400, errorResponse));

      try {
        await client.createSession();
        fail('ApiError가 발생해야 합니다');
      } catch (error) {
        expect(error).toBeInstanceOf(ApiError);
        const apiError = error as ApiError;
        expect(apiError.statusCode).toBe(400);
        expect(apiError.errorCode).toBe('VALIDATION_ERROR');
        expect(apiError.message).toBe('입력 검증에 실패했습니다');
        expect(apiError.errorResponse).toEqual(errorResponse);
      }
    });

    it('일반 오류 응답을 기본 메시지로 처리해야 합니다', async () => {
      mockFetch.mockResolvedValueOnce(createErrorResponse(500));

      try {
        await client.createSession();
        fail('ApiError가 발생해야 합니다');
      } catch (error) {
        expect(error).toBeInstanceOf(ApiError);
        const apiError = error as ApiError;
        expect(apiError.statusCode).toBe(500);
        expect(apiError.message).toBe('서버 내부 오류가 발생했습니다');
      }
    });

    it('다양한 HTTP 상태 코드에 대한 기본 메시지를 반환해야 합니다', async () => {
      const statusMessages: Record<number, string> = {
        400: '잘못된 요청입니다',
        401: '인증이 필요합니다',
        403: '접근이 거부되었습니다',
        404: '리소스를 찾을 수 없습니다',
        409: '리소스 충돌이 발생했습니다',
        422: '요청 데이터 검증에 실패했습니다',
        429: '요청이 너무 많습니다. 잠시 후 다시 시도해주세요',
        502: '게이트웨이 오류가 발생했습니다',
        503: '서비스를 사용할 수 없습니다',
        504: '게이트웨이 타임아웃이 발생했습니다',
      };

      for (const [status, expectedMessage] of Object.entries(statusMessages)) {
        mockFetch.mockClear();
        mockFetch.mockResolvedValueOnce(createErrorResponse(Number(status)));

        try {
          await client.createSession();
          fail(`상태 코드 ${status}에서 ApiError가 발생해야 합니다`);
        } catch (error) {
          expect(error).toBeInstanceOf(ApiError);
          expect((error as ApiError).message).toBe(expectedMessage);
        }
      }
    });

    it('알 수 없는 상태 코드에 대한 기본 메시지를 반환해야 합니다', async () => {
      mockFetch.mockResolvedValueOnce(createErrorResponse(418)); // I'm a teapot

      try {
        await client.createSession();
        fail('ApiError가 발생해야 합니다');
      } catch (error) {
        expect(error).toBeInstanceOf(ApiError);
        expect((error as ApiError).message).toBe('HTTP 오류 418');
      }
    });

    it('JSON이 아닌 응답을 처리해야 합니다', async () => {
      const response = {
        ok: false,
        status: 500,
        headers: new Headers({ 'content-type': 'text/plain' }),
        json: () => Promise.reject(new Error('Not JSON')),
        text: () => Promise.resolve('Internal Server Error'),
      } as Response;
      mockFetch.mockResolvedValueOnce(response);

      await expect(client.createSession()).rejects.toThrow(ApiError);
    });
  });


  // ===========================================================================
  // 오류 클래스 테스트
  // ===========================================================================

  describe('오류 클래스', () => {
    describe('ApiError', () => {
      it('모든 속성이 올바르게 설정되어야 합니다', () => {
        const errorResponse: ErrorResponse = {
          error: { code: 'TEST_ERROR', message: '테스트 오류' },
        };
        const error = new ApiError('테스트 오류', 400, 'TEST_ERROR', errorResponse);

        expect(error.name).toBe('ApiError');
        expect(error.message).toBe('테스트 오류');
        expect(error.statusCode).toBe(400);
        expect(error.errorCode).toBe('TEST_ERROR');
        expect(error.errorResponse).toEqual(errorResponse);
      });

      it('기본 오류 코드가 설정되어야 합니다', () => {
        const error = new ApiError('테스트 오류', 500);

        expect(error.errorCode).toBe('UNKNOWN_ERROR');
      });
    });

    describe('NetworkError', () => {
      it('모든 속성이 올바르게 설정되어야 합니다', () => {
        const originalError = new TypeError('Failed to fetch');
        const error = new NetworkError('네트워크 오류', originalError);

        expect(error.name).toBe('NetworkError');
        expect(error.message).toBe('네트워크 오류');
        expect(error.originalError).toBe(originalError);
      });

      it('원본 오류 없이 생성할 수 있어야 합니다', () => {
        const error = new NetworkError('네트워크 오류');

        expect(error.originalError).toBeUndefined();
      });
    });

    describe('TimeoutError', () => {
      it('모든 속성이 올바르게 설정되어야 합니다', () => {
        const error = new TimeoutError('요청 타임아웃', 30000);

        expect(error.name).toBe('TimeoutError');
        expect(error.message).toBe('요청 타임아웃');
        expect(error.timeoutMs).toBe(30000);
      });
    });
  });

  // ===========================================================================
  // 요청 헤더 테스트
  // ===========================================================================

  describe('요청 헤더', () => {
    it('Content-Type 헤더가 설정되어야 합니다', async () => {
      mockFetch.mockResolvedValueOnce(
        createSuccessResponse({ sessions: [], total_count: 0 })
      );

      await client.listSessions();

      expect(mockFetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          headers: expect.objectContaining({
            'Content-Type': 'application/json',
          }),
        })
      );
    });

    it('Accept 헤더가 설정되어야 합니다', async () => {
      mockFetch.mockResolvedValueOnce(
        createSuccessResponse({ sessions: [], total_count: 0 })
      );

      await client.listSessions();

      expect(mockFetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          headers: expect.objectContaining({
            Accept: 'application/json',
          }),
        })
      );
    });
  });

  // ===========================================================================
  // AbortController 테스트
  // ===========================================================================

  describe('AbortController', () => {
    it('요청에 signal이 포함되어야 합니다', async () => {
      mockFetch.mockResolvedValueOnce(
        createSuccessResponse({ sessions: [], total_count: 0 })
      );

      await client.listSessions();

      expect(mockFetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          signal: expect.any(AbortSignal),
        })
      );
    });
  });
});
