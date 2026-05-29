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

// ── Todo ─────────────────────────────────────────────────────────────────────

export type TodoStatus = "pending" | "in_progress" | "completed" | "cancelled";
export type TodoPriority = "low" | "medium" | "high" | "urgent";
export type TodoFilter = "today" | "upcoming" | "overdue" | "completed" | "all";

export interface TodoOut {
  id: string;
  user_id: string;
  title: string;
  description: string | null;
  status: TodoStatus;
  priority: TodoPriority;
  due_at: string | null;
  completed_at: string | null;
  tags: string[];
  source: string;
  created_at: string;
  updated_at: string;
}

export interface TodoCreate {
  title: string;
  description?: string | null;
  priority?: TodoPriority;
  due_at?: string | null;
  tags?: string[];
  source?: "ui" | "chat";
}

export interface TodoListOut {
  items: TodoOut[];
  next_cursor: string | null;
}

// ── Note ─────────────────────────────────────────────────────────────────────

export interface NoteOut {
  id: string;
  user_id: string;
  title: string;
  content: string;
  tags: string[];
  pinned: boolean;
  source: string;
  created_at: string;
  updated_at: string;
}

export interface NoteCreate {
  title: string;
  content?: string;
  tags?: string[];
  pinned?: boolean;
  source?: "ui" | "chat";
}

export interface NoteUpdate {
  title?: string | null;
  content?: string | null;
  tags?: string[] | null;
  pinned?: boolean | null;
}

export interface NoteListOut {
  items: NoteOut[];
  next_cursor: string | null;
}
