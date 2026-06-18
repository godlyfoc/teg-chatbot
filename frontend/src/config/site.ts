export const WEBSITE_URL =
  import.meta.env.VITE_WEBSITE_URL || "https://www.teg.ie/";

export const PROXY_URL = "/api/proxy/";

export const SITE_HOSTNAME = new URL(WEBSITE_URL).hostname;

export const CHAT_CONFIG = {
  title: "TEG AI Assistant",
  subtitle: "Ask me anything about TEG",
  welcome: "Hi! I'm the TEG assistant. How can I help you today?",
  suggestions: [
    "What is TEG?",
    "What exam levels are available?",
    "How do I contact TEG?",
  ],
} as const;
