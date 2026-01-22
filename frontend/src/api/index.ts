/**
 * API 모듈 진입점
 *
 * 이 모듈은 백엔드 API와 통신하기 위한 클라이언트 및 관련 유틸리티를 내보냅니다.
 *
 * @example
 * import { ChatAPIClient, defaultClient, ApiError } from './api';
 *
 * // 기본 클라이언트 사용
 * const session = await defaultClient.createSession();
 *
 * // 커스텀 클라이언트 생성
 * const customClient = new ChatAPIClient('http://custom-server:8000');
 */

export {
  ChatAPIClient,
  defaultClient,
  ApiError,
  NetworkError,
  TimeoutError,
} from './client';

export type { default as ChatAPIClientType } from './client';
