import { useCallback, useEffect, useMemo, useState } from "react";

import ChatWindow from "./components/ChatWindow";
import MessageInput from "./components/MessageInput";

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || "";

const initialMessages = [
  {
    id: "welcome",
    role: "assistant",
    content:
      "Здравствуйте! Я готов ответить на ваш вопрос по сервис-деску Балтийского Берега.",
  },
];

function mapConfidenceLabel(confidence) {
  if (confidence >= 0.85) {
    return "high";
  }
  if (confidence >= 0.7) {
    return "medium";
  }
  return "low";
}

function mapSources(citations = []) {
  return citations.map((citation) => ({
    title: citation.title,
    excerpt: citation.excerpt,
    score: 1,
    ticket_id: citation.source_type === "ticket" ? citation.source_id : undefined,
    kb_doc_id: citation.source_type === "kb" ? citation.source_id : undefined,
  }));
}

function App() {
  const [messages, setMessages] = useState(initialMessages);
  const [isLoading, setIsLoading] = useState(false);
  const [backendStatus, setBackendStatus] = useState("checking");

  const checkBackend = useCallback(async () => {
    setBackendStatus("checking");

    try {
      const response = await fetch(`${API_BASE_URL}/api/health`);
      if (!response.ok) {
        throw new Error(`Health request failed with ${response.status}`);
      }
      const payload = await response.json();
      setBackendStatus(payload.status === "ok" ? "online" : "offline");
    } catch (error) {
      console.error("Backend health check failed", error);
      setBackendStatus("offline");
    }
  }, []);

  useEffect(() => {
    void checkBackend();
  }, [checkBackend]);

  const sendMessage = useCallback(
    async (text) => {
      const trimmedText = text.trim();
      if (!trimmedText || isLoading) {
        return;
      }

      const userMessage = {
        id: `user-${Date.now()}`,
        role: "user",
        content: trimmedText,
      };

      setMessages((current) => [...current, userMessage]);
      setIsLoading(true);

      try {
        const response = await fetch(`${API_BASE_URL}/api/chat`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ message: trimmedText }),
        });

        if (!response.ok) {
          throw new Error(`Chat request failed with ${response.status}`);
        }

        const payload = await response.json();

        setMessages((current) => [
          ...current,
          {
            id: `assistant-${Date.now()}`,
            role: "assistant",
            content: payload.reply,
            meta: {
              confidence_label: mapConfidenceLabel(payload.confidence ?? 0),
              confidence_score: Math.round((payload.confidence ?? 0) * 100) / 10,
              sources: mapSources(payload.citations),
              escalate: Boolean(payload.needs_human),
              grounded: payload.grounded,
              reason: payload.reason,
            },
          },
        ]);
        setBackendStatus("online");
      } catch (error) {
        console.error("Chat request failed", error);
        setBackendStatus("offline");
        setMessages((current) => [
          ...current,
          {
            id: `assistant-error-${Date.now()}`,
            role: "assistant",
            content:
              "Не удалось получить ответ от сервера. Проверьте доступность backend и попробуйте еще раз.",
            meta: { escalate: true },
          },
        ]);
      } finally {
        setIsLoading(false);
      }
    },
    [isLoading],
  );

  const statusLabel = useMemo(() => {
    if (backendStatus === "online") {
      return "Backend доступен";
    }
    if (backendStatus === "offline") {
      return "Backend недоступен";
    }
    return "Проверяем backend";
  }, [backendStatus]);

  return (
    <div className="app-shell">
      <main className="app-card">
        <header className="app-header">
          <div>
            <h1>Балтийский Берег — чат ассистент</h1>
            <p>Простой web MVP вместо Telegram: вопрос → ответ от YandexGPT.</p>
          </div>
          <div className={`status-pill status-pill--${backendStatus}`}>
            {statusLabel}
          </div>
        </header>

        <ChatWindow messages={messages} isLoading={isLoading} />

        <MessageInput isLoading={isLoading} onSend={sendMessage} />
      </main>
    </div>
  );
}

export default App;
