import { useMemo } from "react";
import { getBrowserLocale, getChatMessages } from "@/i18n";

export function useChatI18n() {
  return useMemo(() => {
    const locale = getBrowserLocale();
    return { locale, t: getChatMessages(locale) };
  }, []);
}
