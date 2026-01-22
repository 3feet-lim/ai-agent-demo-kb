/**
 * SessionManager 컴포넌트
 *
 * 대화 세션 목록을 관리하고 표시하는 컴포넌트입니다.
 * 새 세션 생성 및 세션 전환 기능을 제공합니다.
 *
 * 주요 기능:
 * - 세션 목록 렌더링
 * - "새 채팅" 버튼 제공
 * - 세션 선택 핸들러
 * - 활성 세션 강조 표시
 *
 * 요구사항: 3.1, 3.2
 */

import React, { useCallback } from 'react';
import { Session } from '../types';
import './SessionManager.css';

// =============================================================================
// 인터페이스 정의
// =============================================================================

/**
 * SessionManager 컴포넌트 Props
 *
 * @property sessions - 세션 목록
 * @property activeSessionId - 현재 활성 세션 ID
 * @property onCreateSession - 새 세션 생성 핸들러
 * @property onSelectSession - 세션 선택 핸들러
 * @property isLoading - 로딩 상태 여부
 */
export interface SessionManagerProps {
  /** 세션 목록 (최근 메시지 순 정렬) */
  sessions: Session[];

  /** 현재 활성 세션 ID */
  activeSessionId: string | null;

  /** 새 세션 생성 핸들러 */
  onCreateSession: () => void;

  /** 세션 선택 핸들러 */
  onSelectSession: (sessionId: string) => void;

  /** 로딩 상태 여부 */
  isLoading?: boolean;
}

// =============================================================================
// 유틸리티 함수
// =============================================================================

/**
 * 타임스탬프를 상대적 시간 형식으로 변환합니다.
 *
 * @param timestamp - ISO 8601 형식의 타임스탬프
 * @returns 상대적 시간 문자열 (예: "방금 전", "5분 전", "어제")
 */
function formatRelativeTime(timestamp: string): string {
  try {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMinutes = Math.floor(diffMs / (1000 * 60));
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (diffMinutes < 1) {
      return '방금 전';
    } else if (diffMinutes < 60) {
      return `${diffMinutes}분 전`;
    } else if (diffHours < 24) {
      return `${diffHours}시간 전`;
    } else if (diffDays === 1) {
      return '어제';
    } else if (diffDays < 7) {
      return `${diffDays}일 전`;
    } else {
      return date.toLocaleDateString('ko-KR', {
        month: 'short',
        day: 'numeric',
      });
    }
  } catch {
    return '';
  }
}

// =============================================================================
// 세션 아이템 컴포넌트
// =============================================================================

/**
 * SessionItem Props
 */
interface SessionItemProps {
  /** 세션 데이터 */
  session: Session;

  /** 활성 상태 여부 */
  isActive: boolean;

  /** 클릭 핸들러 */
  onClick: () => void;
}

/**
 * 개별 세션을 렌더링하는 컴포넌트
 */
const SessionItem: React.FC<SessionItemProps> = ({ session, isActive, onClick }) => {
  return (
    <button
      className={`session-item ${isActive ? 'session-item--active' : ''}`}
      onClick={onClick}
      data-testid={`session-${session.id}`}
      aria-selected={isActive}
    >
      <div className="session-item__icon">💬</div>
      <div className="session-item__content">
        <div className="session-item__title">{session.title}</div>
        <div className="session-item__time">
          {formatRelativeTime(session.last_message_at)}
        </div>
      </div>
    </button>
  );
};

// =============================================================================
// 빈 상태 컴포넌트
// =============================================================================

/**
 * 세션이 없을 때 표시되는 빈 상태 컴포넌트
 */
const EmptyState: React.FC = () => {
  return (
    <div className="session-empty" data-testid="session-empty-state">
      <div className="session-empty__icon">📝</div>
      <p className="session-empty__text">
        아직 대화가 없습니다.
        <br />
        새 채팅을 시작해보세요!
      </p>
    </div>
  );
};

// =============================================================================
// SessionManager 메인 컴포넌트
// =============================================================================

/**
 * SessionManager 컴포넌트
 *
 * 대화 세션 목록을 관리하고 표시하는 사이드바 컴포넌트입니다.
 *
 * @example
 * <SessionManager
 *   sessions={sessions}
 *   activeSessionId={currentSessionId}
 *   onCreateSession={handleCreateSession}
 *   onSelectSession={handleSelectSession}
 * />
 */
export const SessionManager: React.FC<SessionManagerProps> = ({
  sessions,
  activeSessionId,
  onCreateSession,
  onSelectSession,
  isLoading = false,
}) => {
  // ---------------------------------------------------------------------------
  // 이벤트 핸들러
  // ---------------------------------------------------------------------------

  /**
   * 새 세션 생성 버튼 클릭 핸들러
   */
  const handleCreateClick = useCallback(() => {
    if (!isLoading) {
      onCreateSession();
    }
  }, [isLoading, onCreateSession]);

  /**
   * 세션 선택 핸들러
   */
  const handleSessionClick = useCallback(
    (sessionId: string) => {
      if (!isLoading && sessionId !== activeSessionId) {
        onSelectSession(sessionId);
      }
    },
    [isLoading, activeSessionId, onSelectSession]
  );

  // ---------------------------------------------------------------------------
  // 렌더링
  // ---------------------------------------------------------------------------

  const hasSessions = sessions.length > 0;

  return (
    <aside className="session-manager" data-testid="session-manager">
      {/* 헤더 영역 */}
      <div className="session-manager__header">
        <h2 className="session-manager__title">대화 목록</h2>
        <button
          className="session-manager__new-button"
          onClick={handleCreateClick}
          disabled={isLoading}
          data-testid="new-session-button"
          aria-label="새 채팅 시작"
        >
          <span className="session-manager__new-icon">+</span>
          <span className="session-manager__new-text">새 채팅</span>
        </button>
      </div>

      {/* 세션 목록 영역 */}
      <div className="session-manager__list" data-testid="session-list">
        {isLoading && sessions.length === 0 ? (
          <div className="session-loading" data-testid="session-loading">
            <span className="session-loading__spinner">⏳</span>
            <span className="session-loading__text">로딩 중...</span>
          </div>
        ) : hasSessions ? (
          sessions.map((session) => (
            <SessionItem
              key={session.id}
              session={session}
              isActive={session.id === activeSessionId}
              onClick={() => handleSessionClick(session.id)}
            />
          ))
        ) : (
          <EmptyState />
        )}
      </div>
    </aside>
  );
};

// =============================================================================
// 내보내기
// =============================================================================

export default SessionManager;
