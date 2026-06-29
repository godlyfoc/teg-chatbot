import { useEffect, useRef } from "react";
import { CHAT_CONFIG } from "@/config/site";
import { useChat } from "@/hooks/useChat";
import ChatInput from "./ChatInput";
import { IconChevronDown, IconTrash } from "./ChatIcons";
import MessageBubble from "./MessageBubble";

interface Props {
  onClose: () => void;
}

export default function ChatPanel({ onClose }: Props) {
  const { messages, isLoading, error, sendMessage, clearChat } = useChat();
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  const showWelcome = messages.length === 0;

  return (
    <>
      <header className="chat-panel__header">
        <div className="chat-panel__title">
          <div className="chat-panel__avatar" aria-hidden="true">AI</div>
          <div className="chat-panel__title-text">
            <h2>{CHAT_CONFIG.title}</h2>
            <p>{isLoading ? "Thinking…" : CHAT_CONFIG.subtitle}</p>
          </div>
        </div>
        <div className="chat-panel__actions">
          <button
            type="button"
            className="chat-panel__icon-btn"
            onClick={clearChat}
            title="Clear chat"
            aria-label="Clear chat"
          >
            <IconTrash />
          </button>
          <button
            type="button"
            className="chat-panel__icon-btn"
            onClick={onClose}
            title="Minimize"
            aria-label="Minimize chat"
          >
            <IconChevronDown />
          </button>
        </div>
      </header>

      <div className="chat-panel__messages">
        {showWelcome && (
          <div className="welcome">
            <p>{CHAT_CONFIG.welcome}</p>
            <div className="suggestions">
              {CHAT_CONFIG.suggestions.map((prompt) => (
                <button
                  key={prompt}
                  type="button"
                  className="suggestion"
                  onClick={() => sendMessage(prompt)}
                  disabled={isLoading}
                >
                  {prompt}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg, index) => {
          const isEmptyStreaming =
            isLoading &&
            msg.role === "assistant" &&
            !msg.content &&
            index === messages.length - 1;
          if (isEmptyStreaming) return null;
          return <MessageBubble key={msg.id} message={msg} />;
        })}

        {isLoading && messages[messages.length - 1]?.content === "" && (
          <div className="typing">
            <span /><span /><span />
          </div>
        )}

        {error && <p className="error-msg">Error: {error}</p>}
        <div ref={bottomRef} />
      </div>

      <ChatInput onSend={sendMessage} disabled={isLoading} />
      <p className="chat-panel__disclaimer">{CHAT_CONFIG.disclaimer}</p>
    </>
  );
}
