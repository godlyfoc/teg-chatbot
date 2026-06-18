import { useState } from "react";
import ChatPanel from "./ChatPanel";
import { IconChat, IconClose } from "./ChatIcons";

export default function FloatingChat() {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="chat-widget">
      <div
        className={`chat-panel${isOpen ? "" : " is-closed"}`}
        role="dialog"
        aria-label="AI chat assistant"
        aria-hidden={!isOpen}
      >
        <ChatPanel onClose={() => setIsOpen(false)} />
      </div>

      <button
        type="button"
        className={`chat-launcher${isOpen ? " is-open" : ""}`}
        onClick={() => setIsOpen((prev) => !prev)}
        aria-label={isOpen ? "Minimize chat" : "Open AI chat"}
        aria-expanded={isOpen}
      >
        {!isOpen && <span className="chat-launcher__pulse" />}
        <span className="chat-launcher__icon">
          {isOpen ? <IconClose /> : <IconChat />}
        </span>
      </button>
    </div>
  );
}
