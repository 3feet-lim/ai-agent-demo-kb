/**
 * App 컴포넌트 단위 테스트
 *
 * App 컴포넌트의 렌더링 및 통합 동작을 테스트합니다.
 *
 * 테스트 항목:
 * - 컴포넌트 렌더링
 * - 환영 화면 표시
 * - SessionManager와 ChatInterface 통합
 * - 세션 생성 및 전환
 * - 오류 처리
 *
 * 요구사항: 2.2, 2.3, 3.1, 3.2
 */

import React from 'react';
import { render, screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import App from '../src/App';
import { defaultClient } from '../src/api/client';
import { Session, Message, SessionListResponse, MessageHistoryResponse } from '../src/types';

// =============================================================================
// API 클라이언트 모킹
// =============================================================================

jest.mock('../src/api/client', () => ({
  defaultClient: {
    listSessions: jest.fn(),
    createSession: jest.fn(),
    getSessionHistory: jest.fn(),
    sendMessage: jest.fn(),
  },
}));

// 모킹된 클라이언트 타입 정의
const mockedClient = defaultClient as jest.Mocked<typeof defaultClient>;

// =============================================================================
// 테스트 유틸리티
// =============================================================================

/**
 * 테스트용 세션 생성 함수
 */
function createTestSession(overrides: Partial<Session> = {}): Session {
  const id = `session-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  return {
    id,
    title: '테스트 세션',
    created_at: new Date().toISOString(),
    last_message_at: new Date().toISOString(),
    ...overrides,
  };
}

/**
 * 테스트용 메시지 생성 함수
 */
function createTestMessage(overrides: Partial<Message> = {}): Message {
  return {
    id: `msg-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
    session_id: 'test-session',
    content: '테스트 메시지',
    role: 'user',
    timestamp: new Date().toISOString(),
    ...overrides,
  };
}

/**
 * 기본 모킹 설정 함수
 */
function setupDefaultMocks(options: {
  sessions?: Session[];
  messages?: Message[];
} = {}) {
  const { sessions = [], messages = [] } = options;

  mockedClient.listSessions.mockResolvedValue({
    sessions,
    total_count: sessions.length,
  } as SessionListResponse);

  mockedClient.getSessionHistory.mockResolvedValue({
    session_id: sessions[0]?.id || 'test-session',
    messages,
    total_count: messages.length,
  } as MessageHistoryResponse);

  mockedClient.createSession.mockResolvedValue(
    createTestSession({ title: '새 대화' })
  );

  mockedClient.sendMessage.mockResolvedValue(
    createTestMessage({ role: 'assistant', content: 'AI 응답입니다' })
  );
}

/**
 * 모든 모킹 초기화
 */
function resetAllMocks() {
  jest.clearAllMocks();
}

// =============================================================================
// 테스트 설정
// =============================================================================

beforeEach(() => {
  resetAllMocks();
});

// =============================================================================
// 렌더링 테스트
// =============================================================================

describe('App 렌더링', () => {
  test('컴포넌트가 정상적으로 렌더링되어야 한다', async () => {
    setupDefaultMocks();

    render(<App />);

    await waitFor(() => {
      expect(screen.getByTestId('app')).toBeInTheDocument();
    });
  });

  test('SessionManager가 렌더링되어야 한다', async () => {
    setupDefaultMocks();

    render(<App />);

    await waitFor(() => {
      expect(screen.getByTestId('session-manager')).toBeInTheDocument();
    });
  });

  test('세션이 없을 때 환영 화면이 표시되어야 한다', async () => {
    setupDefaultMocks({ sessions: [] });

    render(<App />);

    await waitFor(() => {
      expect(screen.getByTestId('welcome-screen')).toBeInTheDocument();
    });
  });

  test('환영 화면에 "AI 챗봇 인프라 모니터링" 제목이 표시되어야 한다', async () => {
    setupDefaultMocks({ sessions: [] });

    render(<App />);

    await waitFor(() => {
      expect(screen.getByText('AI 챗봇 인프라 모니터링')).toBeInTheDocument();
    });
  });

  test('환영 화면에 "새 채팅 시작" 버튼이 표시되어야 한다', async () => {
    setupDefaultMocks({ sessions: [] });

    render(<App />);

    await waitFor(() => {
      expect(screen.getByTestId('welcome-new-chat-button')).toBeInTheDocument();
    });
  });
});

// =============================================================================
// 세션 로드 테스트
// =============================================================================

describe('세션 로드', () => {
  test('마운트 시 세션 목록을 로드해야 한다', async () => {
    setupDefaultMocks();

    render(<App />);

    await waitFor(() => {
      expect(mockedClient.listSessions).toHaveBeenCalledTimes(1);
    });
  });

  test('세션이 있을 때 첫 번째 세션이 자동으로 활성화되어야 한다', async () => {
    const sessions = [
      createTestSession({ id: 'session-1', title: '첫 번째 세션' }),
      createTestSession({ id: 'session-2', title: '두 번째 세션' }),
    ];
    setupDefaultMocks({ sessions });

    render(<App />);

    await waitFor(() => {
      expect(mockedClient.getSessionHistory).toHaveBeenCalledWith('session-1');
    });
  });

  test('세션이 있을 때 ChatInterface가 표시되어야 한다', async () => {
    const sessions = [createTestSession({ id: 'session-1', title: '세션 1' })];
    setupDefaultMocks({ sessions });

    render(<App />);

    await waitFor(() => {
      expect(screen.getByTestId('chat-interface')).toBeInTheDocument();
    });
  });

  test('세션이 있을 때 환영 화면이 표시되지 않아야 한다', async () => {
    const sessions = [createTestSession({ id: 'session-1', title: '세션 1' })];
    setupDefaultMocks({ sessions });

    render(<App />);

    await waitFor(() => {
      expect(screen.queryByTestId('welcome-screen')).not.toBeInTheDocument();
    });
  });
});

// =============================================================================
// 세션 생성 테스트
// =============================================================================

describe('세션 생성', () => {
  test('환영 화면에서 "새 채팅 시작" 버튼 클릭 시 새 세션이 생성되어야 한다', async () => {
    const user = userEvent.setup();
    setupDefaultMocks({ sessions: [] });

    const newSession = createTestSession({ id: 'new-session', title: '새 대화' });
    mockedClient.createSession.mockResolvedValue(newSession);

    render(<App />);

    await waitFor(() => {
      expect(screen.getByTestId('welcome-new-chat-button')).toBeInTheDocument();
    });

    const newChatButton = screen.getByTestId('welcome-new-chat-button');
    await user.click(newChatButton);

    await waitFor(() => {
      expect(mockedClient.createSession).toHaveBeenCalledTimes(1);
    });
  });

  test('SessionManager에서 "새 채팅" 버튼 클릭 시 새 세션이 생성되어야 한다', async () => {
    const user = userEvent.setup();
    const sessions = [createTestSession({ id: 'session-1', title: '세션 1' })];
    setupDefaultMocks({ sessions });

    const newSession = createTestSession({ id: 'new-session', title: '새 대화' });
    mockedClient.createSession.mockResolvedValue(newSession);

    render(<App />);

    await waitFor(() => {
      expect(screen.getByTestId('new-session-button')).toBeInTheDocument();
    });

    const newButton = screen.getByTestId('new-session-button');
    await user.click(newButton);

    await waitFor(() => {
      expect(mockedClient.createSession).toHaveBeenCalledTimes(1);
    });
  });

  test('새 세션 생성 후 해당 세션이 활성화되어야 한다', async () => {
    const user = userEvent.setup();
    setupDefaultMocks({ sessions: [] });

    const newSession = createTestSession({ id: 'new-session', title: '새 대화' });
    mockedClient.createSession.mockResolvedValue(newSession);
    mockedClient.getSessionHistory.mockResolvedValue({
      session_id: 'new-session',
      messages: [],
      total_count: 0,
    });

    render(<App />);

    await waitFor(() => {
      expect(screen.getByTestId('welcome-new-chat-button')).toBeInTheDocument();
    });

    const newChatButton = screen.getByTestId('welcome-new-chat-button');
    await user.click(newChatButton);

    await waitFor(() => {
      expect(screen.getByTestId('chat-interface')).toBeInTheDocument();
    });
  });
});

// =============================================================================
// 세션 전환 테스트
// =============================================================================

describe('세션 전환', () => {
  test('세션 클릭 시 해당 세션으로 전환되어야 한다', async () => {
    const user = userEvent.setup();
    const sessions = [
      createTestSession({ id: 'session-1', title: '세션 1' }),
      createTestSession({ id: 'session-2', title: '세션 2' }),
    ];
    setupDefaultMocks({ sessions });

    render(<App />);

    await waitFor(() => {
      expect(screen.getByTestId('session-session-2')).toBeInTheDocument();
    });

    const session2 = screen.getByTestId('session-session-2');
    await user.click(session2);

    await waitFor(() => {
      expect(mockedClient.getSessionHistory).toHaveBeenCalledWith('session-2');
    });
  });

  test('세션 전환 시 해당 세션의 메시지 기록이 로드되어야 한다', async () => {
    const user = userEvent.setup();
    const sessions = [
      createTestSession({ id: 'session-1', title: '세션 1' }),
      createTestSession({ id: 'session-2', title: '세션 2' }),
    ];
    const session2Messages = [
      createTestMessage({ id: 'msg-1', session_id: 'session-2', content: '세션 2 메시지' }),
    ];

    setupDefaultMocks({ sessions });

    // 세션 2의 메시지 기록 설정
    mockedClient.getSessionHistory.mockImplementation(async (sessionId) => {
      if (sessionId === 'session-2') {
        return {
          session_id: 'session-2',
          messages: session2Messages,
          total_count: session2Messages.length,
        };
      }
      return {
        session_id: sessionId,
        messages: [],
        total_count: 0,
      };
    });

    render(<App />);

    await waitFor(() => {
      expect(screen.getByTestId('session-session-2')).toBeInTheDocument();
    });

    const session2 = screen.getByTestId('session-session-2');
    await user.click(session2);

    await waitFor(() => {
      expect(screen.getByText('세션 2 메시지')).toBeInTheDocument();
    });
  });
});

// =============================================================================
// 오류 처리 테스트
// =============================================================================

describe('오류 처리', () => {
  test('세션 목록 로드 실패 시 오류 메시지가 표시되어야 한다', async () => {
    mockedClient.listSessions.mockRejectedValue(new Error('네트워크 오류'));

    render(<App />);

    await waitFor(() => {
      expect(screen.getByTestId('error-banner')).toBeInTheDocument();
    });
  });

  test('오류 메시지 닫기 버튼 클릭 시 오류가 사라져야 한다', async () => {
    const user = userEvent.setup();
    mockedClient.listSessions.mockRejectedValue(new Error('네트워크 오류'));

    render(<App />);

    await waitFor(() => {
      expect(screen.getByTestId('error-banner')).toBeInTheDocument();
    });

    const closeButton = screen.getByLabelText('오류 닫기');
    await user.click(closeButton);

    await waitFor(() => {
      expect(screen.queryByTestId('error-banner')).not.toBeInTheDocument();
    });
  });

  test('세션 생성 실패 시 오류 메시지가 표시되어야 한다', async () => {
    const user = userEvent.setup();
    setupDefaultMocks({ sessions: [] });
    mockedClient.createSession.mockRejectedValue(new Error('세션 생성 실패'));

    render(<App />);

    await waitFor(() => {
      expect(screen.getByTestId('welcome-new-chat-button')).toBeInTheDocument();
    });

    const newChatButton = screen.getByTestId('welcome-new-chat-button');
    await user.click(newChatButton);

    await waitFor(() => {
      expect(screen.getByTestId('error-banner')).toBeInTheDocument();
    });
  });
});

// =============================================================================
// 메시지 전송 테스트
// =============================================================================

describe('메시지 전송', () => {
  test('메시지 전송 시 sendMessage API가 호출되어야 한다', async () => {
    const user = userEvent.setup();
    const sessions = [createTestSession({ id: 'session-1', title: '세션 1' })];
    setupDefaultMocks({ sessions });

    render(<App />);

    await waitFor(() => {
      expect(screen.getByTestId('message-input')).toBeInTheDocument();
    });

    const input = screen.getByTestId('message-input');
    await user.type(input, '테스트 메시지');

    const sendButton = screen.getByTestId('send-button');
    await user.click(sendButton);

    await waitFor(() => {
      expect(mockedClient.sendMessage).toHaveBeenCalledWith('session-1', '테스트 메시지');
    });
  });

  test('메시지 전송 실패 시 오류 메시지가 표시되어야 한다', async () => {
    const user = userEvent.setup();
    const sessions = [createTestSession({ id: 'session-1', title: '세션 1' })];
    setupDefaultMocks({ sessions });
    mockedClient.sendMessage.mockRejectedValue(new Error('전송 실패'));

    render(<App />);

    await waitFor(() => {
      expect(screen.getByTestId('message-input')).toBeInTheDocument();
    });

    const input = screen.getByTestId('message-input');
    await user.type(input, '테스트 메시지');

    const sendButton = screen.getByTestId('send-button');
    await user.click(sendButton);

    await waitFor(() => {
      expect(screen.getByTestId('error-banner')).toBeInTheDocument();
    });
  });
});

// =============================================================================
// 통합 테스트
// =============================================================================

describe('통합 동작', () => {
  test('전체 흐름: 세션 생성 → 메시지 전송 → 응답 수신', async () => {
    const user = userEvent.setup();
    setupDefaultMocks({ sessions: [] });

    const newSession = createTestSession({ id: 'new-session', title: '새 대화' });
    mockedClient.createSession.mockResolvedValue(newSession);
    mockedClient.getSessionHistory.mockResolvedValue({
      session_id: 'new-session',
      messages: [],
      total_count: 0,
    });

    const aiResponse = createTestMessage({
      id: 'ai-response',
      session_id: 'new-session',
      role: 'assistant',
      content: 'AI 응답입니다',
    });
    mockedClient.sendMessage.mockResolvedValue(aiResponse);

    render(<App />);

    // 1. 환영 화면에서 새 채팅 시작
    await waitFor(() => {
      expect(screen.getByTestId('welcome-new-chat-button')).toBeInTheDocument();
    });

    const newChatButton = screen.getByTestId('welcome-new-chat-button');
    await user.click(newChatButton);

    // 2. ChatInterface가 표시됨
    await waitFor(() => {
      expect(screen.getByTestId('chat-interface')).toBeInTheDocument();
    });

    // 3. 메시지 입력 및 전송
    const input = screen.getByTestId('message-input');
    await user.type(input, '안녕하세요');

    const sendButton = screen.getByTestId('send-button');
    await user.click(sendButton);

    // 4. API 호출 확인
    await waitFor(() => {
      expect(mockedClient.sendMessage).toHaveBeenCalledWith('new-session', '안녕하세요');
    });
  });

  test('세션 목록에 새로 생성된 세션이 추가되어야 한다', async () => {
    const user = userEvent.setup();
    setupDefaultMocks({ sessions: [] });

    const newSession = createTestSession({ id: 'new-session', title: '새 대화' });
    mockedClient.createSession.mockResolvedValue(newSession);
    mockedClient.getSessionHistory.mockResolvedValue({
      session_id: 'new-session',
      messages: [],
      total_count: 0,
    });

    render(<App />);

    await waitFor(() => {
      expect(screen.getByTestId('welcome-new-chat-button')).toBeInTheDocument();
    });

    const newChatButton = screen.getByTestId('welcome-new-chat-button');
    await user.click(newChatButton);

    await waitFor(() => {
      expect(screen.getByTestId('session-new-session')).toBeInTheDocument();
    });
  });
});
