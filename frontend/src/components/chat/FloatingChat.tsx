import { useState } from "react";
import { CHAT_WIDGET_LAYOUT } from "@/config/site";
import ChatPanel from "./ChatPanel";
import { IconChat, IconClose } from "./ChatIcons";

export default function FloatingChat() {
  const [isOpen, setIsOpen] = useState(false);
  const panelBottom = CHAT_WIDGET_LAYOUT.launcherSize + CHAT_WIDGET_LAYOUT.launcherGap;

  return (
    <div
      className="chat-widget"
      style={{
        bottom: CHAT_WIDGET_LAYOUT.bottom,
        right: CHAT_WIDGET_LAYOUT.right,
        // Used by .chat-panel { bottom: var(--chat-panel-bottom) }
        ["--chat-panel-bottom" as string]: `${panelBottom}px`,
      }}
    >
      {isOpen && (
        <div
          className="chat-panel"
          role="dialog"
          aria-label="AI chat assistant"
        >
          <ChatPanel onClose={() => setIsOpen(false)} />
        </div>
      )}

      <button
        type="button"
        className={`chat-launcher${isOpen ? " is-open" : ""}`}
        onClick={() => setIsOpen((prev) => !prev)}
        aria-label={isOpen ? "Minimize chat" : "Open AI chat"}
        aria-expanded={isOpen}
      >
        <span className="chat-launcher__icon">
          {isOpen ? <IconClose /> : <IconChat />}
        </span>
      </button>
    </div>
  );
}
