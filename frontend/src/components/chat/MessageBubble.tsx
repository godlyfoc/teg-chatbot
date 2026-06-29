import type { Message } from "@/types/chat";
import MarkdownContent from "./MarkdownContent";

interface Props {
  message: Message;
}

export default function MessageBubble({ message }: Props) {
  const isUser = message.role === "user";

  return (
    <div className={`message message--${message.role}`}>
      <div className="message__bubble">
        {!isUser && <div className="message__label">AI</div>}
        {isUser ? (
          <span className="message__text">{message.content}</span>
        ) : (
          <MarkdownContent content={message.content} />
        )}
      </div>
    </div>
  );
}
