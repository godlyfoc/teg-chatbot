import type { ChatLocale } from "@/i18n";
import { getChatMessages } from "@/i18n";

export function formatMessageTime(timestamp: number, locale: ChatLocale = "en"): string {
  const labels = getChatMessages(locale);
  const date = new Date(timestamp);
  const now = new Date();
  const time = date.toLocaleTimeString(locale === "ga" ? "ga-IE" : "en-IE", {
    hour: "numeric",
    minute: "2-digit",
  });

  if (date.toDateString() === now.toDateString()) {
    return `${labels.today} ${time}`;
  }

  const yesterday = new Date(now);
  yesterday.setDate(now.getDate() - 1);
  if (date.toDateString() === yesterday.toDateString()) {
    return `${labels.yesterday} ${time}`;
  }

  return `${date.toLocaleDateString(locale === "ga" ? "ga-IE" : "en-IE", {
    month: "short",
    day: "numeric",
  })}, ${time}`;
}
