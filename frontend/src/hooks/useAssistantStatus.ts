import { useEffect, useState } from "react";
import type { ChatMessages } from "@/i18n";

type StatusLabels = Pick<ChatMessages, "thinking" | "analysing" | "generating">;

const DEFAULT_LABELS: StatusLabels = {
  thinking: "Thinking...",
  analysing: "Analysing...",
  generating: "Generating response...",
};

/**
 * Cycles through assistant status labels while waiting for a response.
 * Hides once streamed content starts arriving.
 */
export function useAssistantStatus(
  isLoading: boolean,
  hasStreamedContent: boolean,
  labels: StatusLabels = DEFAULT_LABELS,
) {
  const [statusLabel, setStatusLabel] = useState<string | null>(null);

  useEffect(() => {
    if (!isLoading) {
      setStatusLabel(null);
      return;
    }

    if (hasStreamedContent) {
      // Streamed content is arriving — hide the loading indicator entirely.
      setStatusLabel(null);
      return;
    }

    const sequence = [
      { label: labels.thinking, durationMs: 900 },
      { label: labels.analysing, durationMs: 1000 },
      { label: labels.generating, durationMs: Number.POSITIVE_INFINITY },
    ] as const;

    setStatusLabel(sequence[0].label);
    const timers: ReturnType<typeof setTimeout>[] = [];
    let elapsed = 0;

    for (let index = 1; index < sequence.length; index += 1) {
      elapsed += sequence[index - 1].durationMs;
      const label = sequence[index].label;
      timers.push(
        setTimeout(() => {
          setStatusLabel(label);
        }, elapsed),
      );
    }

    return () => {
      timers.forEach(clearTimeout);
    };
  }, [
    isLoading,
    hasStreamedContent,
    labels.thinking,
    labels.analysing,
    labels.generating,
  ]);

  return statusLabel;
}
