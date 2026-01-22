/**
 * 메인 App 컴포넌트
 *
 * AI 챗봇 인프라 모니터링 애플리케이션의 메인 컴포넌트입니다.
 * ChatInterface와 SessionManager를 통합하여 완전한 채팅 애플리케이션을 제공합니다.
 *
 * 주요 기능:
 * - 세션 목록 관리 및 표시
 * - 세션 생성 및 전환
 * - 메시지 전송 및 수신
 * - 로딩 및 오류 상태 처리
 *
 * 요구사항: 2.2, 3.1, 3.2, 3.3
 */

import React, { useState, useEffect, useCallback } from 'react';
import { ChatInterface, SessionManager } from './components';
import { defaultClient } from './api/client';
import { Message, Session } from './types';
import './App.css';



// =============================================================================
// App 컴포넌트
// =============================================================================

/**
 * 메인 App 컴포넌트
 *
 * 채팅 애플리케이션의 최상위 컴포넌트입니다.
 * 사이드바(SessionManager)와 메인 영역(ChatInterface)으로 구성됩니다.
 *
 * @example
 * <App />
 */
function App(): React.ReactElement {
  // ---------------------------------------------------------------------------
  // 상태 관리
  // ---------------------------------------------------------------------------

  /** 세션 목록 */
  const [sessions, setSessions] = useState<Session[]>(initialState.sessions);

  /** 현재 활성 세션 ID */
  const [activeSessionId, setActiveSessionId] = useState<string | null>(
    initialState.activeSessionId
  );

  /** 현재 세션의 메시지 목록 */
  const [messages, setMessages] = useState<Message[]>(initialState.messages);

  /** API 호출 로딩 상태 */
  const [isLoading, setIsLoading] = useState<boolean>(initialState.isLoading);

  /** 오류 메시지 */
  const [error, setError] = useState<string | null>(initialState.error);

  // ---------------------------------------------------------------------------
  // 세션 목록 로드 (마운트 시)
  // ---------------------------------------------------------------------------

  /**
   * 세션 목록을 서버에서 로드합니다.
   */
  const loadSessions = useCallback(async (): Promise<void> => {
    try {
      setIsLoading(true);
      setError(null);

      const response = await defaultClient.listSessions();
      setSessions(response.sessions);

      // 세션이 있고 활성 세션이 없으면 첫 번째 세션을 활성화
      if (response.sessions.length > 0 && !activeSessionId) {
        setActiveSessionId(response.sessions[0].id);
      }
    } catch (err) {
      console.error('세션 목록 로드 실패:', err);
      setError('세션 목록을 불러오는데 실패했습니다.');
    } finally {
      setIsLoading(false);
    }
  }, [activeSessionId]);

  // 컴포넌트 마운트 시 세션 목록 로드
  useEffect(() => {
    loadSessions();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ---------------------------------------------------------------------------
  // 메시지 로드 (activeSessionId 변경 시)
  // ---------------------------------------------------------------------------

  /**
   * 현재 세션의 메시지 기록을 로드합니다.
   */
  const loadMessages = useCallback(async (sessionId: string): Promise<void> => {
    try {
      setIsLoading(true);
      setError(null);

      const response = await defaultClient.getSessionHistory(sessionId);
      setMessages(response.messages);
    } catch (err) {
      console.error('메시지 기록 로드 실패:', err);
      setError('메시지 기록을 불러오는데 실패했습니다.');
      setMessages([]);
    } finally {
      setIsLoading(false);
    }
  }, []);

  // activeSessionId가 변경될 때 메시지 로드
  useEffect(() => {
    if (activeSessionId) {
      loadMessages(activeSessionId);
    } else {
      setMessages([]);
    }
  }, [activeSessionId, loadMessages]);

  // ---------------------------------------------------------------------------
  // 이벤트 핸들러
  // ---------------------------------------------------------------------------

  /**
   * 새 세션 생성 핸들러
   *
   * 새로운 대화 세션을 생성하고 활성화합니다.
   */
  const handleCreateSession = useCallback(async (): Promise<void> => {
    try {
      setIsLoading(true);
      setError(null);

      // 새 세션 생성
      const newSession = await defaultClient.createSession();

      // 세션 목록 업데이트 (새 세션을 맨 앞에 추가)
      setSessions((prevSessions) => [newSession, ...prevSessions]);

      // 새 세션을 활성화
      setActiveSessionId(newSession.id);

      // 메시지 목록 초기화
      setMessages([]);
    } catch (err) {
      console.error('세션 생성 실패:', err);
      setError('새 세션을 생성하는데 실패했습니다.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  /**
   * 세션 선택 핸들러
   *
   * 선택한 세션으로 전환합니다.
   *
   * @param sessionId - 선택한 세션 ID
   */
  const handleSelectSession = useCallback((sessionId: string): void => {
    setActiveSessionId(sessionId);
    setError(null);
  }, []);

  /**
   * 메시지 전송 핸들러
   *
   * 사용자 메시지를 전송하고 AI 응답을 받습니다.
   *
   * @param content - 메시지 내용
   */
  const handleSendMessage = useCallback(
    async (content: string): Promise<void> => {
      if (!activeSessionId) {
        setError('활성 세션이 없습니다. 새 채팅을 시작해주세요.');
        return;
      }

      try {
        setIsLoading(true);
        setError(null);

        // 사용자 메시지를 즉시 UI에 추가 (낙관적 업데이트)
        const tempUserMessage: Message = {
          id: `temp-${Date.now()}`,
          session_id: activeSessionId,
          content,
          role: 'user',
          timestamp: new Date().toISOString(),
        };
        setMessages((prevMessages) => [...prevMessages, tempUserMessage]);

        // 서버에 메시지 전송
        const response = await defaultClient.sendMessage(activeSessionId, content);

        // 서버 응답으로 메시지 목록 업데이트
        // 임시 사용자 메시지를 실제 응답으로 교체하고 AI 응답 추가
        setMessages((prevMessages) => {
          // 임시 메시지 제거
          const filteredMessages = prevMessages.filter(
            (msg) => msg.id !== tempUserMessage.id
          );

          // 사용자 메시지와 AI 응답 추가
          // 서버에서 사용자 메시지도 반환하는 경우를 대비
          const userMessage: Message = {
            id: `user-${Date.now()}`,
            session_id: activeSessionId,
            content,
            role: 'user',
            timestamp: new Date().toISOString(),
          };

          return [...filteredMessages, userMessage, response];
        });

        // 세션 목록에서 현재 세션의 last_message_at 업데이트
        setSessions((prevSessions) =>
          prevSessions.map((session) =>
            session.id === activeSessionId
              ? { ...session, last_message_at: new Date().toISOString() }
              : session
          )
        );
      } catch (err) {
        console.error('메시지 전송 실패:', err);
        setError('메시지 전송에 실패했습니다. 다시 시도해주세요.');

        // 실패 시 임시 메시지 제거
        setMessages((prevMessages) =>
          prevMessages.filter((msg) => !msg.id.startsWith('temp-'))
        );
      } finally {
        setIsLoading(false);
      }
    },
    [activeSessionId]
  );

  /**
   * 오류 메시지 닫기 핸들러
   */
  const handleCloseError = useCallback((): void => {
    setError(null);
  }, []);

  // ---------------------------------------------------------------------------
  // 렌더링
  // ---------------------------------------------------------------------------

  return (
    <div className="app" data-testid="app">
      {/* 오류 알림 */}
      {error && (
        <div className="app__error" data-testid="error-banner">
          <span className="app__error-message">{error}</span>
          <button
            className="app__error-close"
            onClick={handleCloseError}
            aria-label="오류 닫기"
          >
            ✕
          </button>
        </div>
      )}

      {/* 메인 레이아웃 */}
      <div className="app__layout">
        {/* 사이드바 - 세션 관리 */}
        <SessionManager
          sessions={sessions}
          activeSessionId={activeSessionId}
          onCreateSession={handleCreateSession}
          onSelectSession={handleSelectSession}
          isLoading={isLoading}
        />

        {/* 메인 영역 - 채팅 인터페이스 */}
        <main className="app__main">
          {activeSessionId ? (
            <ChatInterface
              sessionId={activeSessionId}
              messages={messages}
              onSendMessage={handleSendMessage}
              isLoading={isLoading}
            />
          ) : (
            <div className="app__welcome" data-testid="welcome-screen">
              <div className="app__welcome-content">
                <div className="app__welcome-icon">🤖</div>
                <h1 className="app__welcome-title">
                  AI 챗봇 인프라 모니터링
                </h1>
                <p className="app__welcome-description">
                  인프라 모니터링을 위한 AI 기반 챗봇입니다.
                  <br />
                  새 채팅을 시작하여 인프라 상태를 확인하세요.
                </p>
                <button
                  className="app__welcome-button"
                  onClick={handleCreateSession}
                  disabled={isLoading}
                  data-testid="welcome-new-chat-button"
                >
                  {isLoading ? '생성 중...' : '새 채팅 시작'}
                </button>
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}

// =============================================================================
// 내보내기
// =============================================================================

export default App;
