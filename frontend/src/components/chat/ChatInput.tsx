import { type FormEvent, type KeyboardEvent, useState } from "react";
import { IconSend } from "./ChatIcons";

interface Props {
  onSend: (message: string) => void;
  disabled?: boolean;
}

export default function ChatInput({ onSend, disabled }: Props) {
  const [text, setText] = useState("");

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!text.trim() || disabled) return;
    onSend(text);
    setText("");
  }

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  }

  return (
    <form className="chat-panel__input" onSubmit={handleSubmit}>
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Ask a question…"
        disabled={disabled}
        rows={1}
        aria-label="Message"
      />
      <button type="submit" disabled={disabled || !text.trim()} aria-label="Send">
        <IconSend />
      </button>
    </form>
  );
}
