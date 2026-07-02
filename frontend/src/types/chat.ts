export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  createdAt: number;
}

export interface ChatRequest {
  message: string;
  history: { role: string; content: string }[];
}

export interface StreamEvent {
  content?: string;
  replace?: string;
  reset?: boolean;
  done?: boolean;
  error?: string;
}
