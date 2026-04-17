import React, { useEffect, useLayoutEffect, useRef, useState } from 'react';
import './App.css';
import Analytics from './components/Analytics';
import ChatWindow from './components/ChatWindow';
import LoginScreen from './components/LoginScreen';

const WELCOME = {
  _id: 'welcome',
  role: 'assistant',
  content: 'Здравствуйте! Я AI-ассистент IT-поддержки **Балтийского Берега**.\n\nОпишите вашу проблему, и я постараюсь помочь.',
  meta: { confidence_label: 'high', confidence_score: 10, sources: [], escalate: false },
};

function storedUser() {
  try { return JSON.parse(localStorage.getItem('bb_user') || 'null'); } catch { return null; }
}

export default function App() {
  const [user, setUser]           = useState(storedUser);
  const [activeTab, setActiveTab] = useState('chat');
  const [messages, setMessages]   = useState([WELCOME]);
  const [isLoading, setIsLoading] = useState(false);
  const [statusDot, setStatusDot] = useState('');

  // History pagination
  const [hasMoreHistory, setHasMoreHistory]     = useState(false);
  const [loadingHistory, setLoadingHistory]     = useState(false);
  const chatContainerRef = useRef(null);

  // session_id fallback (no auth)
  const sessionId = useRef(
    sessionStorage.getItem('session_id') || (() => {
      const id = crypto.randomUUID();
      sessionStorage.setItem('session_id', id);
      return id;
    })()
  );

  useEffect(() => {
    fetch('/api/health')
      .then(r => r.json())
      .then(d => setStatusDot(d.status === 'ok' ? 'ok' : 'degraded'))
      .catch(() => setStatusDot('error'));
  }, []);

  // ── Auth ──────────────────────────────────────────────────────────────────

  async function handleLogin(userData) {
    localStorage.setItem('bb_user', JSON.stringify(userData));
    setUser(userData);
    await loadInitialHistory(userData.user_id);
  }

  function handleLogout() {
    localStorage.removeItem('bb_user');
    setUser(null);
    setMessages([WELCOME]);
    setHasMoreHistory(false);
  }

  // ── History loading ────────────────────────────────────────────────────────

  function fromHistoryItem(item) {
    return {
      _id: item.id,
      id: item.id,
      role: item.role,
      content: item.content,
      meta: item.meta || undefined,
    };
  }

  async function loadInitialHistory(userId) {
    try {
      const resp = await fetch(`/api/chat/history?user_id=${userId}&limit=20`);
      const data = await resp.json();
      if (data.items.length > 0) {
        setMessages(data.items.map(fromHistoryItem));
        setHasMoreHistory(data.has_more);
      } else {
        setMessages([WELCOME]);
        setHasMoreHistory(false);
      }
    } catch {
      setMessages([WELCOME]);
    }
  }

  async function loadOlderMessages() {
    if (!user || loadingHistory || !hasMoreHistory) return;
    const oldestId = messages.find(m => m.id)?.id;
    if (!oldestId) return;

    setLoadingHistory(true);
    const container = chatContainerRef.current;
    const prevScrollHeight = container?.scrollHeight || 0;

    try {
      const resp = await fetch(`/api/chat/history?user_id=${user.user_id}&before_id=${oldestId}&limit=20`);
      const data = await resp.json();
      if (data.items.length > 0) {
        setMessages(prev => [...data.items.map(fromHistoryItem), ...prev]);
        setHasMoreHistory(data.has_more);
        // restore scroll after render
        requestAnimationFrame(() => {
          if (container) container.scrollTop = container.scrollHeight - prevScrollHeight;
        });
      } else {
        setHasMoreHistory(false);
      }
    } catch { /* silent */ }
    setLoadingHistory(false);
  }

  // ── Send message ──────────────────────────────────────────────────────────

  async function sendMessage(text) {
    const trimmed = text.trim();
    if (!trimmed || isLoading) return;

    const userMsg = { _id: crypto.randomUUID(), role: 'user', content: trimmed };
    setMessages(prev => [...prev, userMsg]);
    setIsLoading(true);

    try {
      const resp = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: trimmed, session_id: sessionId.current, user_id: user?.user_id ?? null }),
      });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json();
      setMessages(prev => [...prev, {
        _id: crypto.randomUUID(),
        role: 'assistant',
        content: data.answer,
        meta: { confidence_label: data.confidence_label, confidence_score: data.confidence_score, sources: data.sources || [], escalate: data.escalate },
      }]);
    } catch {
      setMessages(prev => [...prev, {
        _id: crypto.randomUUID(),
        role: 'assistant',
        content: 'Произошла ошибка при обращении к серверу. Попробуйте ещё раз.',
        meta: { confidence_label: 'low', confidence_score: 0, sources: [], escalate: false },
      }]);
    } finally {
      setIsLoading(false);
    }
  }

  // ── Render ─────────────────────────────────────────────────────────────────

  if (!user) {
    return (
      <div className="app">
        <header className="header">
          <div>
            <div className="header__title">Балтийский Берег — IT Поддержка</div>
            <div className="header__subtitle">AI-ассистент службы технической поддержки</div>
          </div>
          {statusDot && <div className={`status-dot status-dot--${statusDot}`} />}
        </header>
        <LoginScreen onLogin={handleLogin} />
      </div>
    );
  }

  return (
    <div className="app">
      <header className="header">
        <div>
          <div className="header__title">Балтийский Берег — IT Поддержка</div>
          <div className="header__subtitle">AI-ассистент службы технической поддержки</div>
        </div>
        <div className="header__right">
          <span className="header__username">{user.username}</span>
          <button className="header__logout" onClick={handleLogout}>Выйти</button>
          {statusDot && <div className={`status-dot status-dot--${statusDot}`} />}
        </div>
      </header>

      <nav className="tabs">
        <button className={`tab ${activeTab === 'chat' ? 'tab--active' : ''}`} onClick={() => setActiveTab('chat')}>Чат</button>
        <button className={`tab ${activeTab === 'analytics' ? 'tab--active' : ''}`} onClick={() => setActiveTab('analytics')}>Аналитика</button>
      </nav>

      <div className="tab-content">
        {activeTab === 'chat' && (
          <ChatWindow
            messages={messages}
            isLoading={isLoading}
            onSend={sendMessage}
            containerRef={chatContainerRef}
            loadingHistory={loadingHistory}
            hasMoreHistory={hasMoreHistory}
            onScrollToTop={loadOlderMessages}
          />
        )}
        {activeTab === 'analytics' && <Analytics />}
      </div>
    </div>
  );
}
