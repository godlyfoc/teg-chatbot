import { useCallback, useRef, useState } from "react";
import { streamMessage } from "@/services/api";
import type { Message } from "@/types/chat";

let counter = 0;
const newId = () => `msg-${++counter}-${Date.now()}`;

export function useChat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<(() => void) | null>(null);

  const sendMessage = useCallback(
    (text: string) => {
      const trimmed = text.trim();
      if (!trimmed || isLoading) return;

      setError(null);
      setIsLoading(true);

      const userMsg: Message = { id: newId(), role: "user", content: trimmed };
      const assistantId = newId();
      const assistantMsg: Message = { id: assistantId, role: "assistant", content: "" };

      setMessages((prev) => [...prev, userMsg, assistantMsg]);

      const history = messages.map((m) => ({ role: m.role, content: m.content }));

      abortRef.current = streamMessage(
        { message: trimmed, history },
        (chunk) => {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantId ? { ...m, content: m.content + chunk } : m,
            ),
          );
        },
        () => {
          setIsLoading(false);
          abortRef.current = null;
        },
        (errMsg) => {
          setError(errMsg);
          setIsLoading(false);
          setMessages((prev) => prev.filter((m) => m.id !== assistantId));
          abortRef.current = null;
        },
      );
    },
    [isLoading, messages],
  );

  const clearChat = useCallback(() => {
    abortRef.current?.();
    abortRef.current = null;
    setMessages([]);
    setError(null);
    setIsLoading(false);
  }, []);

  return { messages, isLoading, error, sendMessage, clearChat };
}
