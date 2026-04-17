import React, { useEffect, useRef, useState } from 'react';
import Message from './Message';

export default function ChatWindow({ messages, isLoading, onSend }) {
  const bottomRef = useRef(null);
  const [text, setText] = useState('');

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

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
  }

  return (
    <>
      <div className="chat-window">
        {messages.map((msg, i) => (
          <Message key={i} role={msg.role} content={msg.content} meta={msg.meta} />
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
