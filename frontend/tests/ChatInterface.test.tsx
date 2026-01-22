/**
 * ChatInterface 컴포넌트 단위 테스트
 *
 * ChatInterface 컴포넌트의 렌더링 및 상호작용을 테스트합니다.
 *
 * 테스트 항목:
 * - 컴포넌트 렌더링
 * - 메시지 목록 표시
 * - 메시지 입력 및 전송
 * - 로딩 상태 표시
 * - 사용자/어시스턴트 메시지 스타일 구분
 *
 * 요구사항: 2.2, 2.3, 2.5
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import { ChatInterface, ChatInterfaceProps } from '../src/components/ChatInterface';
import { Message } from '../src/types';

// =============================================================================
// 테스트 유틸리티
// =============================================================================

/**
 * 테스트용 메시지 생성 함수
 */
function createTestMessage(
  overrides: Partial<Message> = {}
): Message {
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
 * 기본 props 생성 함수
 */
function createDefaultProps(
  overrides: Partial<ChatInterfaceProps> = {}
): ChatInterfaceProps {
  return {
    sessionId: 'test-session',
    messages: [],
    onSendMessage: jest.fn().mockResolvedValue(undefined),
    isLoading: false,
    ...overrides,
  };
}

/**
 * ChatInterface 컴포넌트 렌더링 헬퍼
 */
function renderChatInterface(props: Partial<ChatInterfaceProps> = {}) {
  const defaultProps = createDefaultProps(props);
  return {
    ...render(<ChatInterface {...defaultProps} />),
    props: defaultProps,
  };
}

// =============================================================================
// 렌더링 테스트
// =============================================================================

describe('ChatInterface 렌더링', () => {
  test('컴포넌트가 정상적으로 렌더링되어야 한다', () => {
    renderChatInterface();

    expect(screen.getByTestId('chat-interface')).toBeInTheDocument();
    expect(screen.getByTestId('messages-container')).toBeInTheDocument();
    expect(screen.getByTestId('message-form')).toBeInTheDocument();
    expect(screen.getByTestId('message-input')).toBeInTheDocument();
    expect(screen.getByTestId('send-button')).toBeInTheDocument();
  });

  test('메시지가 없을 때 빈 상태가 표시되어야 한다', () => {
    renderChatInterface({ messages: [] });

    expect(screen.getByTestId('empty-state')).toBeInTheDocument();
    expect(screen.getByText('대화를 시작하세요')).toBeInTheDocument();
  });

  test('메시지가 있을 때 빈 상태가 표시되지 않아야 한다', () => {
    const messages = [createTestMessage({ content: '안녕하세요' })];
    renderChatInterface({ messages });

    expect(screen.queryByTestId('empty-state')).not.toBeInTheDocument();
    expect(screen.getByText('안녕하세요')).toBeInTheDocument();
  });
});

// =============================================================================
// 메시지 표시 테스트
// =============================================================================

describe('메시지 표시', () => {
  test('사용자 메시지가 올바르게 표시되어야 한다', () => {
    const userMessage = createTestMessage({
      id: 'user-msg-1',
      content: '사용자 메시지입니다',
      role: 'user',
    });
    renderChatInterface({ messages: [userMessage] });

    const messageElement = screen.getByTestId('message-user-msg-1');
    expect(messageElement).toBeInTheDocument();
    expect(messageElement).toHaveClass('chat-message--user');
    expect(screen.getByText('사용자 메시지입니다')).toBeInTheDocument();
  });

  test('어시스턴트 메시지가 올바르게 표시되어야 한다', () => {
    const assistantMessage = createTestMessage({
      id: 'assistant-msg-1',
      content: 'AI 응답입니다',
      role: 'assistant',
    });
    renderChatInterface({ messages: [assistantMessage] });

    const messageElement = screen.getByTestId('message-assistant-msg-1');
    expect(messageElement).toBeInTheDocument();
    expect(messageElement).toHaveClass('chat-message--assistant');
    expect(screen.getByText('AI 응답입니다')).toBeInTheDocument();
  });

  test('여러 메시지가 순서대로 표시되어야 한다', () => {
    const messages = [
      createTestMessage({ id: 'msg-1', content: '첫 번째 메시지', role: 'user' }),
      createTestMessage({ id: 'msg-2', content: '두 번째 메시지', role: 'assistant' }),
      createTestMessage({ id: 'msg-3', content: '세 번째 메시지', role: 'user' }),
    ];
    renderChatInterface({ messages });

    const messagesContainer = screen.getByTestId('messages-container');
    const messageElements = messagesContainer.querySelectorAll('.chat-message');

    expect(messageElements).toHaveLength(3);
    expect(screen.getByText('첫 번째 메시지')).toBeInTheDocument();
    expect(screen.getByText('두 번째 메시지')).toBeInTheDocument();
    expect(screen.getByText('세 번째 메시지')).toBeInTheDocument();
  });

  test('사용자와 어시스턴트 메시지가 다른 스타일을 가져야 한다', () => {
    const messages = [
      createTestMessage({ id: 'user-1', content: '사용자', role: 'user' }),
      createTestMessage({ id: 'assistant-1', content: '어시스턴트', role: 'assistant' }),
    ];
    renderChatInterface({ messages });

    const userMessage = screen.getByTestId('message-user-1');
    const assistantMessage = screen.getByTestId('message-assistant-1');

    expect(userMessage).toHaveClass('chat-message--user');
    expect(assistantMessage).toHaveClass('chat-message--assistant');
    expect(userMessage).not.toHaveClass('chat-message--assistant');
    expect(assistantMessage).not.toHaveClass('chat-message--user');
  });
});

// =============================================================================
// 로딩 상태 테스트
// =============================================================================

describe('로딩 상태', () => {
  test('로딩 중일 때 로딩 인디케이터가 표시되어야 한다', () => {
    const messages = [createTestMessage({ content: '질문입니다' })];
    renderChatInterface({ messages, isLoading: true });

    expect(screen.getByTestId('loading-indicator')).toBeInTheDocument();
    expect(screen.getByText('AI가 응답을 생성하고 있습니다...')).toBeInTheDocument();
  });

  test('로딩 중이 아닐 때 로딩 인디케이터가 표시되지 않아야 한다', () => {
    const messages = [createTestMessage({ content: '질문입니다' })];
    renderChatInterface({ messages, isLoading: false });

    expect(screen.queryByTestId('loading-indicator')).not.toBeInTheDocument();
  });

  test('로딩 중일 때 입력 필드가 비활성화되어야 한다', () => {
    renderChatInterface({ isLoading: true });

    const input = screen.getByTestId('message-input');
    expect(input).toBeDisabled();
  });

  test('로딩 중일 때 전송 버튼이 비활성화되어야 한다', () => {
    renderChatInterface({ isLoading: true });

    const button = screen.getByTestId('send-button');
    expect(button).toBeDisabled();
  });

  test('로딩 중일 때 입력 상태 메시지가 표시되어야 한다', () => {
    renderChatInterface({ isLoading: true });

    expect(screen.getByTestId('input-status')).toBeInTheDocument();
  });
});

// =============================================================================
// 메시지 입력 테스트
// =============================================================================

describe('메시지 입력', () => {
  test('입력 필드에 텍스트를 입력할 수 있어야 한다', async () => {
    const user = userEvent.setup();
    renderChatInterface();

    const input = screen.getByTestId('message-input');
    await user.type(input, '테스트 입력');

    expect(input).toHaveValue('테스트 입력');
  });

  test('빈 입력일 때 전송 버튼이 비활성화되어야 한다', () => {
    renderChatInterface();

    const button = screen.getByTestId('send-button');
    expect(button).toBeDisabled();
  });

  test('입력이 있을 때 전송 버튼이 활성화되어야 한다', async () => {
    const user = userEvent.setup();
    renderChatInterface();

    const input = screen.getByTestId('message-input');
    await user.type(input, '테스트');

    const button = screen.getByTestId('send-button');
    expect(button).not.toBeDisabled();
  });

  test('공백만 있는 입력일 때 전송 버튼이 비활성화되어야 한다', async () => {
    const user = userEvent.setup();
    renderChatInterface();

    const input = screen.getByTestId('message-input');
    await user.type(input, '   ');

    const button = screen.getByTestId('send-button');
    expect(button).toBeDisabled();
  });
});

// =============================================================================
// 메시지 전송 테스트
// =============================================================================

describe('메시지 전송', () => {
  test('전송 버튼 클릭 시 onSendMessage가 호출되어야 한다', async () => {
    const user = userEvent.setup();
    const onSendMessage = jest.fn().mockResolvedValue(undefined);
    renderChatInterface({ onSendMessage });

    const input = screen.getByTestId('message-input');
    await user.type(input, '테스트 메시지');

    const button = screen.getByTestId('send-button');
    await user.click(button);

    expect(onSendMessage).toHaveBeenCalledWith('테스트 메시지');
  });

  test('Enter 키 입력 시 메시지가 전송되어야 한다', async () => {
    const user = userEvent.setup();
    const onSendMessage = jest.fn().mockResolvedValue(undefined);
    renderChatInterface({ onSendMessage });

    const input = screen.getByTestId('message-input');
    await user.type(input, '테스트 메시지{enter}');

    expect(onSendMessage).toHaveBeenCalledWith('테스트 메시지');
  });

  test('Shift+Enter 입력 시 메시지가 전송되지 않아야 한다', async () => {
    const user = userEvent.setup();
    const onSendMessage = jest.fn().mockResolvedValue(undefined);
    renderChatInterface({ onSendMessage });

    const input = screen.getByTestId('message-input');
    await user.type(input, '테스트 메시지');
    await user.keyboard('{Shift>}{Enter}{/Shift}');

    expect(onSendMessage).not.toHaveBeenCalled();
  });

  test('메시지 전송 후 입력 필드가 초기화되어야 한다', async () => {
    const user = userEvent.setup();
    const onSendMessage = jest.fn().mockResolvedValue(undefined);
    renderChatInterface({ onSendMessage });

    const input = screen.getByTestId('message-input');
    await user.type(input, '테스트 메시지');

    const button = screen.getByTestId('send-button');
    await user.click(button);

    await waitFor(() => {
      expect(input).toHaveValue('');
    });
  });

  test('빈 메시지는 전송되지 않아야 한다', async () => {
    const user = userEvent.setup();
    const onSendMessage = jest.fn().mockResolvedValue(undefined);
    renderChatInterface({ onSendMessage });

    const button = screen.getByTestId('send-button');
    await user.click(button);

    expect(onSendMessage).not.toHaveBeenCalled();
  });

  test('로딩 중일 때 메시지가 전송되지 않아야 한다', async () => {
    const user = userEvent.setup();
    const onSendMessage = jest.fn().mockResolvedValue(undefined);
    
    // 먼저 입력 필드에 텍스트를 입력한 후 로딩 상태로 변경
    const { rerender } = render(
      <ChatInterface
        sessionId="test-session"
        messages={[]}
        onSendMessage={onSendMessage}
        isLoading={false}
      />
    );

    const input = screen.getByTestId('message-input');
    await user.type(input, '테스트 메시지');

    // 로딩 상태로 변경
    rerender(
      <ChatInterface
        sessionId="test-session"
        messages={[]}
        onSendMessage={onSendMessage}
        isLoading={true}
      />
    );

    const button = screen.getByTestId('send-button');
    await user.click(button);

    expect(onSendMessage).not.toHaveBeenCalled();
  });

  test('메시지 전송 실패 시 입력값이 복원되어야 한다', async () => {
    const user = userEvent.setup();
    const onSendMessage = jest.fn().mockRejectedValue(new Error('전송 실패'));
    renderChatInterface({ onSendMessage });

    const input = screen.getByTestId('message-input');
    await user.type(input, '테스트 메시지');

    const button = screen.getByTestId('send-button');
    await user.click(button);

    await waitFor(() => {
      expect(input).toHaveValue('테스트 메시지');
    });
  });
});

// =============================================================================
// 세션 변경 테스트
// =============================================================================

describe('세션 변경', () => {
  test('세션 변경 시 입력 필드가 초기화되어야 한다', async () => {
    const user = userEvent.setup();
    const { rerender } = render(
      <ChatInterface
        sessionId="session-1"
        messages={[]}
        onSendMessage={jest.fn()}
        isLoading={false}
      />
    );

    const input = screen.getByTestId('message-input');
    await user.type(input, '테스트 입력');

    expect(input).toHaveValue('테스트 입력');

    // 세션 변경
    rerender(
      <ChatInterface
        sessionId="session-2"
        messages={[]}
        onSendMessage={jest.fn()}
        isLoading={false}
      />
    );

    expect(input).toHaveValue('');
  });
});

// =============================================================================
// 접근성 테스트
// =============================================================================

describe('접근성', () => {
  test('입력 필드에 aria-label이 있어야 한다', () => {
    renderChatInterface();

    const input = screen.getByTestId('message-input');
    expect(input).toHaveAttribute('aria-label', '메시지 입력');
  });

  test('전송 버튼에 aria-label이 있어야 한다', () => {
    renderChatInterface();

    const button = screen.getByTestId('send-button');
    expect(button).toHaveAttribute('aria-label', '메시지 전송');
  });
});
