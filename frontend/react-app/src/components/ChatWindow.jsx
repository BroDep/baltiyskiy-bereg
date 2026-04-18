import { useEffect, useRef } from "react";

import Message from "./Message";

function ChatWindow({ messages, isLoading }) {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  return (
    <section className="chat-window" aria-live="polite">
      {messages.length === 0 ? (
        <div className="empty-state">
          <h2>Чат пока пуст</h2>
          <p>Задайте первый вопрос, и ассистент попробует помочь.</p>
        </div>
      ) : (
        messages.map((message) => <Message key={message.id} {...message} />)
      )}

      {isLoading ? (
        <div className="message-row message-row--assistant">
          <div className="message-bubble message-bubble--assistant" aria-label="Ассистент печатает">
            <div className="typing-indicator">
              <span />
              <span />
              <span />
            </div>
          </div>
        </div>
      ) : null}

      <div ref={bottomRef} />
    </section>
  );
}

export default ChatWindow;
