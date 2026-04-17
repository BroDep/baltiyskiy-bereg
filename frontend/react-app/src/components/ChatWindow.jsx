import React, { useEffect, useRef, useState } from 'react';
import Message from './Message';

export default function ChatWindow({
  messages,
  isLoading,
  onSend,
  containerRef,
  loadingHistory,
  hasMoreHistory,
  onScrollToTop,
}) {
  const bottomRef    = useRef(null);
  const [text, setText] = useState('');
  const isAtBottom   = useRef(true);

  // Auto-scroll to bottom only if already near bottom
  useEffect(() => {
    if (isAtBottom.current) {
      bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, isLoading]);

  function handleScroll(e) {
    const el = e.currentTarget;
    // Near bottom?
    isAtBottom.current = el.scrollHeight - el.scrollTop - el.clientHeight < 120;
    // Near top → load older messages
    if (el.scrollTop < 80 && !loadingHistory && hasMoreHistory) {
      onScrollToTop?.();
    }
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  }

  function submit() {
    if (!text.trim() || isLoading) return;
    onSend(text);
    setText('');
    isAtBottom.current = true;
  }

  return (
    <>
      <div className="chat-window" ref={containerRef} onScroll={handleScroll}>

        {/* Top history markers */}
        {loadingHistory && (
          <div className="chat-history-loading">
            <span className="chat-history-spinner" />
            Загрузка истории...
          </div>
        )}
        {!loadingHistory && !hasMoreHistory && messages.length > 1 && (
          <div className="chat-history-end">Начало истории</div>
        )}

        {messages.map(msg => (
          <Message key={msg._id ?? msg.id} role={msg.role} content={msg.content} meta={msg.meta} />
        ))}

        {isLoading && (
          <div className="typing-indicator">
            <div className="typing-dot" />
            <div className="typing-dot" />
            <div className="typing-dot" />
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="message-input">
        <textarea
          className="message-input__textarea"
          rows={1}
          placeholder="Опишите вашу проблему..."
          value={text}
          onChange={e => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isLoading}
        />
        <button className="message-input__btn" onClick={submit} disabled={isLoading || !text.trim()}>
          <svg viewBox="0 0 24 24"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" /></svg>
        </button>
      </div>
    </>
  );
}
