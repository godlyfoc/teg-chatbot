import { useEffect, useMemo, useRef } from "react";
import { useChatI18n } from "@/hooks/useChatI18n";
import { useAssistantStatus } from "@/hooks/useAssistantStatus";
import { useChat } from "@/hooks/useChat";
import ChatInput from "./ChatInput";
import { IconChevronDown, IconSparkles, IconTrash } from "./ChatIcons";
import MessageBubble from "./MessageBubble";

interface Props {
  onClose: () => void;
}

export default function ChatPanel({ onClose }: Props) {
  const { t } = useChatI18n();
  const { messages, isLoading, error, sendMessage, clearChat } = useChat();
  const bottomRef = useRef<HTMLDivElement>(null);

  const lastMessage = messages[messages.length - 1];
  const hasStreamedContent =
    isLoading && lastMessage?.role === "assistant" && Boolean(lastMessage.content);

  const statusLabels = useMemo(
    () => ({
      thinking: t.thinking,
      analysing: t.analysing,
      generating: t.generating,
    }),
    [t.thinking, t.analysing, t.generating],
  );

  const statusLabel = useAssistantStatus(isLoading, hasStreamedContent, statusLabels);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading, statusLabel]);

  const showWelcome = messages.length === 0;

  return (
    <>
      <header className="chat-panel__header">
        <div className="chat-panel__title">
          <h2 className="chat-panel__heading">
            <IconSparkles />
            {t.title}
          </h2>
          <p>{t.subtitle}</p>
        </div>
        <div className="chat-panel__actions">
          <button
            type="button"
            className="chat-panel__icon-btn"
            onClick={clearChat}
            title={t.clearChat}
            aria-label={t.clearChat}
          >
            <IconTrash />
          </button>
          <button
            type="button"
            className="chat-panel__icon-btn"
            onClick={onClose}
            title={t.minimize}
            aria-label={t.minimizeChat}
          >
            <IconChevronDown />
          </button>
        </div>
      </header>

      <div className="chat-panel__messages">
        {showWelcome && (
          <div className="welcome">
            <p>{t.welcome}</p>
            <div className="suggestions">
              {t.suggestions.map((prompt) => (
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
          const isLast = index === messages.length - 1;
          const isStreamingAssistant =
            isLoading && isLast && msg.role === "assistant";

          return (
            <MessageBubble
              key={msg.id}
              message={msg}
              isStreaming={isStreamingAssistant}
              statusLabel={isStreamingAssistant ? statusLabel : null}
            />
          );
        })}

        {error && <p className="error-msg">{t.errorPrefix} {error}</p>}
        <div ref={bottomRef} />
      </div>

      <div className="chat-panel__bottom">
        <ChatInput onSend={sendMessage} disabled={isLoading} />
        <p className="chat-panel__disclaimer">{t.disclaimer}</p>
      </div>
    </>
  );
}
