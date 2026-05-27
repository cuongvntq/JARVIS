// API response types matching backend schemas

export interface UserOut {
  id: string;
  email: string;
  name: string;
  timezone: string;
  assistant_name: string;
  locale: string;
  avatar_url: string | null;
}

export interface TokenResponse {
  access_token: string;
  refresh_token?: string | null; // not present in browser flow; delivered via httponly cookie
  expires_in: number;
  user: UserOut;
}

export interface MessageOut {
  id: string;
  role: "user" | "assistant" | "system" | "tool";
  content: string;
  tokens_in: number;
  tokens_out: number;
  created_at: string;
}

export interface ChatSendRequest {
  conversation_id: string | null;
  content: string;
  stream: boolean;
}

export interface ChatSendResponse {
  conversation_id: string;
  user_message: MessageOut;
  assistant_message: MessageOut;
}

export interface ConversationOut {
  id: string;
  title: string;
  last_message_at: string | null;
  message_count: number;
  created_at: string;
}

export interface ConversationListResponse {
  items: ConversationOut[];
  next_cursor: string | null;
}

export interface ConversationDetailOut {
  id: string;
  title: string;
  last_message_at: string | null;
  message_count: number;
  created_at: string;
  messages: MessageOut[];
  has_more: boolean;
}

export interface ApiErrorBody {
  code: string;
  message: string;
  details: Record<string, unknown>;
  request_id: string;
}

export class ApiException extends Error {
  constructor(
    public statusCode: number,
    public error: ApiErrorBody,
  ) {
    super(error.message);
    this.name = "ApiException";
  }
}
