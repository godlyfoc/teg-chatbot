import { ga } from "./locales/ga";
import { en, type ChatMessages } from "./locales/en";

export type ChatLocale = "en" | "ga";

const catalogs: Record<ChatLocale, ChatMessages> = {
  en,
  ga,
};

/** Map browser language to supported chat UI locale (en or ga). */
export function getBrowserLocale(): ChatLocale {
  if (typeof navigator === "undefined") return "en";
  const primary = navigator.language.toLowerCase();
  const languages = navigator.languages?.map((lang) => lang.toLowerCase()) ?? [];
  const candidates = [primary, ...languages];
  for (const lang of candidates) {
    if (lang.startsWith("ga")) return "ga";
    if (lang.startsWith("en")) return "en";
  }
  return "en";
}

export function getChatMessages(locale: ChatLocale = getBrowserLocale()): ChatMessages {
  return catalogs[locale];
}

export { en, ga };
export type { ChatMessages };
