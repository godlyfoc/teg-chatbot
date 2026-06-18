export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
}

export interface ChatRequest {
  message: string;
  history: { role: string; content: string }[];
}

export interface StreamEvent {
  content?: string;
  done?: boolean;
  error?: string;
}
