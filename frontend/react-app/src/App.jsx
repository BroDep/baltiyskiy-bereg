import React, { useEffect, useRef, useState } from 'react';
import './App.css';
import Analytics from './components/Analytics';
import ChatWindow from './components/ChatWindow';

const WELCOME = {
  role: 'assistant',
  content: 'Здравствуйте! Я AI-ассистент IT-поддержки **Балтийского Берега**.\n\nОпишите вашу проблему, и я постараюсь помочь.',
  meta: { confidence_label: 'high', confidence_score: 10, sources: [], escalate: false },
};

export default function App() {
  const [activeTab, setActiveTab] = useState('chat');
  const [messages, setMessages] = useState([WELCOME]);
  const [isLoading, setIsLoading] = useState(false);
  const [statusDot, setStatusDot] = useState('');
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

  async function sendMessage(text) {
    const trimmed = text.trim();
    if (!trimmed || isLoading) return;
    setMessages(prev => [...prev, { role: 'user', content: trimmed }]);
    setIsLoading(true);
    try {
      const resp = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: trimmed, session_id: sessionId.current }),
      });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json();
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: data.answer,
        meta: { confidence_label: data.confidence_label, confidence_score: data.confidence_score, sources: data.sources || [], escalate: data.escalate },
      }]);
    } catch {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: 'Произошла ошибка при обращении к серверу. Попробуйте ещё раз.',
        meta: { confidence_label: 'low', confidence_score: 0, sources: [], escalate: false },
      }]);
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="app">
      <header className="header">
        <div>
          <div className="header__title">Балтийский Берег — IT Поддержка</div>
          <div className="header__subtitle">AI-ассистент службы технической поддержки</div>
        </div>
        {statusDot && <div className={`status-dot status-dot--${statusDot}`} />}
      </header>

      <nav className="tabs">
        <button className={`tab ${activeTab === 'chat' ? 'tab--active' : ''}`} onClick={() => setActiveTab('chat')}>
          Чат
        </button>
        <button className={`tab ${activeTab === 'analytics' ? 'tab--active' : ''}`} onClick={() => setActiveTab('analytics')}>
          Аналитика
        </button>
      </nav>

      <div className="tab-content">
        {activeTab === 'chat' && (
          <ChatWindow messages={messages} isLoading={isLoading} onSend={sendMessage} />
        )}
        {activeTab === 'analytics' && <Analytics />}
      </div>
    </div>
  );
}
