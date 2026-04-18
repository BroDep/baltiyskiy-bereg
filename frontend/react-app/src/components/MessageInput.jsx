import { useState } from "react";

function MessageInput({ isLoading, onSend }) {
  const [value, setValue] = useState("");

  const submit = async () => {
    const trimmed = value.trim();
    if (!trimmed) {
      return;
    }

    setValue("");
    await onSend(trimmed);
  };

  const handleKeyDown = async (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      await submit();
    }
  };

  return (
    <div className="message-input">
      <textarea
        placeholder="Опишите вопрос или проблему..."
        value={value}
        onChange={(event) => setValue(event.target.value)}
        onKeyDown={handleKeyDown}
        disabled={isLoading}
      />
      <button type="button" onClick={submit} disabled={isLoading || !value.trim()}>
        {isLoading ? "Отправляем..." : "Отправить"}
      </button>
    </div>
  );
}

export default MessageInput;
