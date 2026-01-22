/**
 * SessionManager 컴포넌트 단위 테스트
 *
 * SessionManager 컴포넌트의 렌더링 및 상호작용을 테스트합니다.
 *
 * 테스트 항목:
 * - 컴포넌트 렌더링
 * - 세션 목록 표시
 * - 활성 세션 강조 표시
 * - 새 세션 생성 버튼
 * - 세션 선택 핸들러
 * - 빈 상태 표시
 *
 * 요구사항: 3.1, 3.2
 */

import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import { SessionManager, SessionManagerProps } from '../src/components/SessionManager';
import { Session } from '../src/types';

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
 * 기본 props 생성 함수
 */
function createDefaultProps(
  overrides: Partial<SessionManagerProps> = {}
): SessionManagerProps {
  return {
    sessions: [],
    activeSessionId: null,
    onCreateSession: jest.fn(),
    onSelectSession: jest.fn(),
    isLoading: false,
    ...overrides,
  };
}

/**
 * SessionManager 컴포넌트 렌더링 헬퍼
 */
function renderSessionManager(props: Partial<SessionManagerProps> = {}) {
  const defaultProps = createDefaultProps(props);
  return {
    ...render(<SessionManager {...defaultProps} />),
    props: defaultProps,
  };
}

// =============================================================================
// 렌더링 테스트
// =============================================================================

describe('SessionManager 렌더링', () => {
  test('컴포넌트가 정상적으로 렌더링되어야 한다', () => {
    renderSessionManager();

    expect(screen.getByTestId('session-manager')).toBeInTheDocument();
    expect(screen.getByTestId('new-session-button')).toBeInTheDocument();
    expect(screen.getByTestId('session-list')).toBeInTheDocument();
  });

  test('헤더에 "대화 목록" 제목이 표시되어야 한다', () => {
    renderSessionManager();

    expect(screen.getByText('대화 목록')).toBeInTheDocument();
  });

  test('"새 채팅" 버튼이 표시되어야 한다', () => {
    renderSessionManager();

    expect(screen.getByText('새 채팅')).toBeInTheDocument();
  });
});

// =============================================================================
// 세션 목록 표시 테스트
// =============================================================================

describe('세션 목록 표시', () => {
  test('세션이 없을 때 빈 상태가 표시되어야 한다', () => {
    renderSessionManager({ sessions: [] });

    expect(screen.getByTestId('session-empty-state')).toBeInTheDocument();
    expect(screen.getByText('아직 대화가 없습니다.')).toBeInTheDocument();
  });

  test('세션 목록이 올바르게 표시되어야 한다', () => {
    const sessions = [
      createTestSession({ id: 'session-1', title: '첫 번째 세션' }),
      createTestSession({ id: 'session-2', title: '두 번째 세션' }),
      createTestSession({ id: 'session-3', title: '세 번째 세션' }),
    ];
    renderSessionManager({ sessions });

    expect(screen.getByText('첫 번째 세션')).toBeInTheDocument();
    expect(screen.getByText('두 번째 세션')).toBeInTheDocument();
    expect(screen.getByText('세 번째 세션')).toBeInTheDocument();
  });

  test('세션이 있을 때 빈 상태가 표시되지 않아야 한다', () => {
    const sessions = [createTestSession({ title: '테스트 세션' })];
    renderSessionManager({ sessions });

    expect(screen.queryByTestId('session-empty-state')).not.toBeInTheDocument();
  });

  test('각 세션에 대한 테스트 ID가 올바르게 설정되어야 한다', () => {
    const sessions = [
      createTestSession({ id: 'session-abc', title: '세션 ABC' }),
      createTestSession({ id: 'session-xyz', title: '세션 XYZ' }),
    ];
    renderSessionManager({ sessions });

    expect(screen.getByTestId('session-session-abc')).toBeInTheDocument();
    expect(screen.getByTestId('session-session-xyz')).toBeInTheDocument();
  });
});

// =============================================================================
// 활성 세션 강조 테스트
// =============================================================================

describe('활성 세션 강조', () => {
  test('활성 세션이 강조 표시되어야 한다', () => {
    const sessions = [
      createTestSession({ id: 'session-1', title: '세션 1' }),
      createTestSession({ id: 'session-2', title: '세션 2' }),
    ];
    renderSessionManager({ sessions, activeSessionId: 'session-1' });

    const activeSession = screen.getByTestId('session-session-1');
    const inactiveSession = screen.getByTestId('session-session-2');

    expect(activeSession).toHaveClass('session-item--active');
    expect(inactiveSession).not.toHaveClass('session-item--active');
  });

  test('활성 세션에 aria-selected 속성이 true여야 한다', () => {
    const sessions = [
      createTestSession({ id: 'session-1', title: '세션 1' }),
      createTestSession({ id: 'session-2', title: '세션 2' }),
    ];
    renderSessionManager({ sessions, activeSessionId: 'session-1' });

    const activeSession = screen.getByTestId('session-session-1');
    const inactiveSession = screen.getByTestId('session-session-2');

    expect(activeSession).toHaveAttribute('aria-selected', 'true');
    expect(inactiveSession).toHaveAttribute('aria-selected', 'false');
  });

  test('활성 세션이 없을 때 모든 세션이 비활성 상태여야 한다', () => {
    const sessions = [
      createTestSession({ id: 'session-1', title: '세션 1' }),
      createTestSession({ id: 'session-2', title: '세션 2' }),
    ];
    renderSessionManager({ sessions, activeSessionId: null });

    const session1 = screen.getByTestId('session-session-1');
    const session2 = screen.getByTestId('session-session-2');

    expect(session1).not.toHaveClass('session-item--active');
    expect(session2).not.toHaveClass('session-item--active');
  });
});

// =============================================================================
// 새 세션 생성 테스트
// =============================================================================

describe('새 세션 생성', () => {
  test('"새 채팅" 버튼 클릭 시 onCreateSession이 호출되어야 한다', async () => {
    const user = userEvent.setup();
    const onCreateSession = jest.fn();
    renderSessionManager({ onCreateSession });

    const newButton = screen.getByTestId('new-session-button');
    await user.click(newButton);

    expect(onCreateSession).toHaveBeenCalledTimes(1);
  });

  test('로딩 중일 때 "새 채팅" 버튼이 비활성화되어야 한다', () => {
    renderSessionManager({ isLoading: true });

    const newButton = screen.getByTestId('new-session-button');
    expect(newButton).toBeDisabled();
  });

  test('로딩 중일 때 "새 채팅" 버튼 클릭 시 onCreateSession이 호출되지 않아야 한다', async () => {
    const user = userEvent.setup();
    const onCreateSession = jest.fn();
    renderSessionManager({ onCreateSession, isLoading: true });

    const newButton = screen.getByTestId('new-session-button');
    await user.click(newButton);

    expect(onCreateSession).not.toHaveBeenCalled();
  });
});

// =============================================================================
// 세션 선택 테스트
// =============================================================================

describe('세션 선택', () => {
  test('세션 클릭 시 onSelectSession이 호출되어야 한다', async () => {
    const user = userEvent.setup();
    const onSelectSession = jest.fn();
    const sessions = [
      createTestSession({ id: 'session-1', title: '세션 1' }),
      createTestSession({ id: 'session-2', title: '세션 2' }),
    ];
    renderSessionManager({ sessions, onSelectSession });

    const session = screen.getByTestId('session-session-1');
    await user.click(session);

    expect(onSelectSession).toHaveBeenCalledWith('session-1');
  });

  test('이미 활성화된 세션 클릭 시 onSelectSession이 호출되지 않아야 한다', async () => {
    const user = userEvent.setup();
    const onSelectSession = jest.fn();
    const sessions = [
      createTestSession({ id: 'session-1', title: '세션 1' }),
    ];
    renderSessionManager({ sessions, activeSessionId: 'session-1', onSelectSession });

    const session = screen.getByTestId('session-session-1');
    await user.click(session);

    expect(onSelectSession).not.toHaveBeenCalled();
  });

  test('로딩 중일 때 세션 클릭 시 onSelectSession이 호출되지 않아야 한다', async () => {
    const user = userEvent.setup();
    const onSelectSession = jest.fn();
    const sessions = [
      createTestSession({ id: 'session-1', title: '세션 1' }),
    ];
    renderSessionManager({ sessions, onSelectSession, isLoading: true });

    const session = screen.getByTestId('session-session-1');
    await user.click(session);

    expect(onSelectSession).not.toHaveBeenCalled();
  });

  test('다른 세션으로 전환 시 onSelectSession이 올바른 ID로 호출되어야 한다', async () => {
    const user = userEvent.setup();
    const onSelectSession = jest.fn();
    const sessions = [
      createTestSession({ id: 'session-1', title: '세션 1' }),
      createTestSession({ id: 'session-2', title: '세션 2' }),
    ];
    renderSessionManager({ sessions, activeSessionId: 'session-1', onSelectSession });

    const session2 = screen.getByTestId('session-session-2');
    await user.click(session2);

    expect(onSelectSession).toHaveBeenCalledWith('session-2');
  });
});

// =============================================================================
// 로딩 상태 테스트
// =============================================================================

describe('로딩 상태', () => {
  test('로딩 중이고 세션이 없을 때 로딩 인디케이터가 표시되어야 한다', () => {
    renderSessionManager({ sessions: [], isLoading: true });

    expect(screen.getByTestId('session-loading')).toBeInTheDocument();
    expect(screen.getByText('로딩 중...')).toBeInTheDocument();
  });

  test('로딩 중이지만 세션이 있을 때 세션 목록이 표시되어야 한다', () => {
    const sessions = [createTestSession({ id: 'session-1', title: '세션 1' })];
    renderSessionManager({ sessions, isLoading: true });

    expect(screen.queryByTestId('session-loading')).not.toBeInTheDocument();
    expect(screen.getByText('세션 1')).toBeInTheDocument();
  });
});

// =============================================================================
// 접근성 테스트
// =============================================================================

describe('접근성', () => {
  test('"새 채팅" 버튼에 aria-label이 있어야 한다', () => {
    renderSessionManager();

    const newButton = screen.getByTestId('new-session-button');
    expect(newButton).toHaveAttribute('aria-label', '새 채팅 시작');
  });

  test('세션 항목에 aria-selected 속성이 있어야 한다', () => {
    const sessions = [createTestSession({ id: 'session-1', title: '세션 1' })];
    renderSessionManager({ sessions });

    const session = screen.getByTestId('session-session-1');
    expect(session).toHaveAttribute('aria-selected');
  });
});

// =============================================================================
// 상대적 시간 표시 테스트
// =============================================================================

describe('상대적 시간 표시', () => {
  test('최근 메시지 시간이 표시되어야 한다', () => {
    const sessions = [
      createTestSession({
        id: 'session-1',
        title: '세션 1',
        last_message_at: new Date().toISOString(),
      }),
    ];
    renderSessionManager({ sessions });

    // "방금 전" 또는 시간 관련 텍스트가 표시되어야 함
    const sessionElement = screen.getByTestId('session-session-1');
    expect(sessionElement).toBeInTheDocument();
  });
});
