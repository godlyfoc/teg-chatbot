import { type FormEvent, type KeyboardEvent, useState } from "react";
import { useChatI18n } from "@/hooks/useChatI18n";
import { IconSend } from "./ChatIcons";
interface Props {
  onSend: (message: string) => void;
  disabled?: boolean;
}

export default function ChatInput({ onSend, disabled }: Props) {
  const { t } = useChatI18n();
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
    <form className="chat-panel__footer" onSubmit={handleSubmit}>
      <div className="chat-panel__input-box">
        <textarea
          className="chat-panel__input-field"
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={t.inputPlaceholder}
          disabled={disabled}
          rows={1}
          aria-label={t.inputAriaLabel}
        />
        <button
          type="submit"
          className="chat-panel__send-btn"
          disabled={disabled || !text.trim()}
          aria-label={t.sendAriaLabel}
        >
          <IconSend />
        </button>
      </div>
    </form>
  );
}
