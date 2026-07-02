import type { ChatRequest, StreamEvent } from "@/types/chat";

export function streamMessage(
  request: ChatRequest,
  onChunk: (text: string) => void,
  onDone: () => void,
  onError: (error: string) => void,
  onReset?: () => void,
  onReplace?: (text: string) => void,
): () => void {
  const controller = new AbortController();

  fetch("/api/chat/stream", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
    signal: controller.signal,
  })
    .then(async (response) => {
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const reader = response.body?.getReader();
      if (!reader) throw new Error("No response body");

      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const parts = buffer.split("\n\n");
        buffer = parts.pop() || "";

        for (const part of parts) {
          if (!part.startsWith("data: ")) continue;
          const parsed: StreamEvent = JSON.parse(part.slice(6));

          if (parsed.error) {
            onError(parsed.error);
            return;
          }
          if (parsed.reset) onReset?.();
          if (parsed.replace) onReplace?.(parsed.replace);
          if (parsed.content) onChunk(parsed.content);
          if (parsed.done) {
            onDone();
            return;
          }
        }
      }
      onDone();
    })
    .catch((err) => {
      if (err.name !== "AbortError") {
        onError(err.message || "Stream failed");
      }
    });

  return () => controller.abort();
}
