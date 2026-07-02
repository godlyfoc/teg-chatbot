export const WEBSITE_URL =
  import.meta.env.VITE_WEBSITE_URL || "https://www.teg.ie/";

export const PROXY_URL = "/api/proxy/";

export const SITE_HOSTNAME = new URL(WEBSITE_URL).hostname;

/** @deprecated Use `useChatI18n()` — kept for layout constants only */
export { getBrowserLocale, getChatMessages } from "@/i18n";

/** Fixed offsets for the chat launcher — clears teg.ie scroll-to-top button (~50px at bottom-right). */
export const CHAT_WIDGET_LAYOUT = {
  bottom: "60px",
  right: "24px",
  launcherSize: 58,
  launcherGap: 14,
} as const;
