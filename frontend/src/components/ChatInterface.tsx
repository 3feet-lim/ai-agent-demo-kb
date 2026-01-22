/**
 * ChatInterface 컴포넌트
 *
 * 사용자와 AI 어시스턴트 간의 대화 인터페이스를 제공합니다.
 * 메시지 목록, 입력 필드, 전송 버튼을 포함합니다.
 *
 * 주요 기능:
 * - 자동 스크롤이 있는 메시지 목록 렌더링
 * - 메시지 입력 필드 및 전송 버튼
 * - AI 응답 중 로딩 상태 표시
 * - 사용자/어시스턴트 메시지 구분 스타일링
 *
 * 요구사항: 2.2, 2.3, 2.5
 */

import React, { useRef, useEffect, useState, useCallback, FormEvent, KeyboardEvent } from 'react';
import { Message } from '../types';
import './ChatInterface.css';

// =============================================================================
// 인터페이스 정의
// =============================================================================

/**
 * ChatInterface 컴포넌트 Props
 *
 * @property sessionId - 현재 활성 세션 ID
 * @property messages - 표시할 메시지 목록
 * @property onSendMessage - 메시지 전송 핸들러
 * @property isLoading - AI 응답 대기 중 여부
 */
export interface ChatInterfaceProps {
  /** 현재 활성 세션 ID */
  sessionId: string;

  /** 표시할 메시지 목록 (시간순 정렬) */
  messages: Message[];

  /** 메시지 전송 핸들러 */
  onSendMessage: (content: string) => Promise<void>;

  /** AI 응답 대기 중 여부 */
  isLoading: boolean;
}

// =============================================================================
// 유틸리티 함수
// =============================================================================

/**
 * 타임스탬프를 사람이 읽기 쉬운 형식으로 변환합니다.
 *
 * @param timestamp - ISO 8601 형식의 타임스탬프
 * @returns 포맷된 시간 문자열 (예: "오후 2:30")
 */
function formatTimestamp(timestamp: string): string {
  try {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('ko-KR', {
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return '';
  }
}

// =============================================================================
// 메시지 아이템 컴포넌트
// =============================================================================

/**
 * MessageItem Props
 */
interface MessageItemProps {
  /** 메시지 데이터 */
  message: Message;
}

/**
 * 개별 메시지를 렌더링하는 컴포넌트
 *
 * 사용자 메시지는 오른쪽 정렬, 파란색 배경
 * 어시스턴트 메시지는 왼쪽 정렬, 회색 배경
 */
const MessageItem: React.FC<MessageItemProps> = ({ message }) => {
  const isUser = message.role === 'user';

  return (
    <div
      className={`chat-message ${isUser ? 'chat-message--user' : 'chat-message--assistant'}`}
      data-testid={`message-${message.id}`}
    >
      <div className="chat-message__bubble">
        <div className="chat-message__content">{message.content}</div>
        <div className="chat-message__timestamp">
          {formatTimestamp(message.timestamp)}
        </div>
      </div>
    </div>
  );
};

// =============================================================================
// 로딩 인디케이터 컴포넌트
// =============================================================================

/**
 * AI 응답 대기 중 표시되는 로딩 인디케이터
 */
const LoadingIndicator: React.FC = () => {
  return (
    <div className="chat-message chat-message--assistant" data-testid="loading-indicator">
      <div className="chat-message__bubble chat-message__bubble--loading">
        <div className="chat-loading">
          <span className="chat-loading__dot"></span>
          <span className="chat-loading__dot"></span>
          <span className="chat-loading__dot"></span>
        </div>
        <span className="chat-loading__text">AI가 응답을 생성하고 있습니다...</span>
      </div>
    </div>
  );
};

// =============================================================================
// 빈 상태 컴포넌트
// =============================================================================

/**
 * 메시지가 없을 때 표시되는 빈 상태 컴포넌트
 */
const EmptyState: React.FC = () => {
  return (
    <div className="chat-empty" data-testid="empty-state">
      <div className="chat-empty__icon">💬</div>
      <h3 className="chat-empty__title">대화를 시작하세요</h3>
      <p className="chat-empty__description">
        인프라 모니터링에 대해 질문해 보세요.
        <br />
        예: "현재 CPU 사용률을 확인해주세요"
      </p>
    </div>
  );
};

// =============================================================================
// ChatInterface 메인 컴포넌트
// =============================================================================

/**
 * ChatInterface 컴포넌트
 *
 * 채팅 인터페이스의 메인 컴포넌트입니다.
 * 메시지 목록, 입력 필드, 전송 버튼을 포함합니다.
 *
 * @example
 * <ChatInterface
 *   sessionId="session-123"
 *   messages={messages}
 *   onSendMessage={handleSendMessage}
 *   isLoading={isLoading}
 * />
 */
export const ChatInterface: React.FC<ChatInterfaceProps> = ({
  sessionId,
  messages,
  onSendMessage,
  isLoading,
}) => {
  // 입력 필드 상태
  const [inputValue, setInputValue] = useState<string>('');

  // 메시지 목록 컨테이너 ref (자동 스크롤용)
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // 입력 필드 ref (포커스 관리용)
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // ---------------------------------------------------------------------------
  // 자동 스크롤 효과
  // ---------------------------------------------------------------------------

  /**
   * 메시지 목록의 맨 아래로 스크롤합니다.
   */
  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  // 메시지가 추가되거나 로딩 상태가 변경될 때 자동 스크롤
  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading, scrollToBottom]);

  // 세션이 변경될 때 입력 필드 초기화 및 포커스
  useEffect(() => {
    setInputValue('');
    inputRef.current?.focus();
  }, [sessionId]);

  // ---------------------------------------------------------------------------
  // 이벤트 핸들러
  // ---------------------------------------------------------------------------

  /**
   * 메시지 전송 핸들러
   */
  const handleSubmit = useCallback(
    async (e: FormEvent<HTMLFormElement>) => {
      e.preventDefault();

      const trimmedValue = inputValue.trim();

      // 빈 메시지 또는 로딩 중이면 무시
      if (!trimmedValue || isLoading) {
        return;
      }

      // 입력 필드 초기화
      setInputValue('');

      // 메시지 전송
      try {
        await onSendMessage(trimmedValue);
      } catch (error) {
        // 오류 발생 시 입력값 복원
        setInputValue(trimmedValue);
        console.error('메시지 전송 실패:', error);
      }
    },
    [inputValue, isLoading, onSendMessage]
  );

  /**
   * 키보드 이벤트 핸들러 (Enter로 전송, Shift+Enter로 줄바꿈)
   */
  const handleKeyDown = useCallback(
    (e: KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        // 폼 제출 트리거
        const form = e.currentTarget.form;
        if (form) {
          form.requestSubmit();
        }
      }
    },
    []
  );

  /**
   * 입력 필드 변경 핸들러
   */
  const handleInputChange = useCallback(
    (e: React.ChangeEvent<HTMLTextAreaElement>) => {
      setInputValue(e.target.value);
    },
    []
  );

  // ---------------------------------------------------------------------------
  // 렌더링
  // ---------------------------------------------------------------------------

  const hasMessages = messages.length > 0;
  const isSubmitDisabled = !inputValue.trim() || isLoading;

  return (
    <div className="chat-interface" data-testid="chat-interface">
      {/* 메시지 목록 영역 */}
      <div className="chat-messages" data-testid="messages-container">
        {hasMessages ? (
          <>
            {messages.map((message) => (
              <MessageItem key={message.id} message={message} />
            ))}
            {isLoading && <LoadingIndicator />}
          </>
        ) : (
          <EmptyState />
        )}
        {/* 자동 스크롤 앵커 */}
        <div ref={messagesEndRef} />
      </div>

      {/* 메시지 입력 영역 */}
      <form className="chat-input-form" onSubmit={handleSubmit} data-testid="message-form">
        <div className="chat-input-container">
          <textarea
            ref={inputRef}
            className="chat-input"
            value={inputValue}
            onChange={handleInputChange}
            onKeyDown={handleKeyDown}
            placeholder="메시지를 입력하세요... (Enter로 전송, Shift+Enter로 줄바꿈)"
            disabled={isLoading}
            rows={1}
            data-testid="message-input"
            aria-label="메시지 입력"
          />
          <button
            type="submit"
            className="chat-submit-button"
            disabled={isSubmitDisabled}
            data-testid="send-button"
            aria-label="메시지 전송"
          >
            {isLoading ? (
              <span className="chat-submit-button__loading">⏳</span>
            ) : (
              <span className="chat-submit-button__icon">➤</span>
            )}
          </button>
        </div>
        {isLoading && (
          <div className="chat-input-status" data-testid="input-status">
            AI가 응답을 생성하고 있습니다...
          </div>
        )}
      </form>
    </div>
  );
};

// =============================================================================
// 내보내기
// =============================================================================

export default ChatInterface;
