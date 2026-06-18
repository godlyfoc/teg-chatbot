import type { Message } from "@/types/chat";

interface Props {
  message: Message;
}

export default function MessageBubble({ message }: Props) {
  const isUser = message.role === "user";

  return (
    <div className={`message message--${message.role}`}>
      <div className="message__bubble">
        {!isUser && <div className="message__label">AI</div>}
        <span>{message.content}</span>
      </div>
    </div>
  );
}
