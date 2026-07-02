import type { Message } from "@/types/chat";
import { useChatI18n } from "@/hooks/useChatI18n";
import { formatMessageTime } from "@/utils/formatMessageTime";
import MarkdownContent from "./MarkdownContent";
import BulbMark from "./BulbMark";

interface Props {
  message: Message;
  isStreaming?: boolean;
  statusLabel?: string | null;
}

export default function MessageBubble({ message, isStreaming = false, statusLabel = null }: Props) {
  const { locale } = useChatI18n();
  const isUser = message.role === "user";
  const showTime = !isStreaming || Boolean(message.content);

  if (isUser) {
    return (
      <div className="message message--user">
        <div className="message__col">
          <div className="message__bubble message__bubble--user">
            <span className="message__text">{message.content}</span>
          </div>
          {showTime && (
            <time className="message__time" dateTime={new Date(message.createdAt).toISOString()}>
              {formatMessageTime(message.createdAt, locale)}
            </time>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="message message--assistant">
      {isStreaming && statusLabel && (
        <div className="assistant-status-row">
          <BulbMark pulse={isStreaming} />
          <p className="assistant-status" role="status" aria-live="polite">
            <span className="assistant-status__text">{statusLabel}</span>
          </p>
        </div>
      )}

      {message.content && (
        <div className={isStreaming && statusLabel ? "message__content-row" : "message__row"}>
          {isStreaming && statusLabel ? (
            <span className="message__icon-spacer" aria-hidden="true" />
          ) : (
            <BulbMark pulse={isStreaming} />
          )}
          <div className="message__col">
            <div className="message__bubble message__bubble--assistant">
              <MarkdownContent content={message.content} />
            </div>
            {showTime && (
              <time className="message__time" dateTime={new Date(message.createdAt).toISOString()}>
                {formatMessageTime(message.createdAt, locale)}
              </time>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
