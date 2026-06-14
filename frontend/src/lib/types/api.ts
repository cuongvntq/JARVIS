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

// ── Memory ───────────────────────────────────────────────────────────────────

export type MemoryType = "fact" | "preference" | "rule" | "relation" | "goal" | "other";

export interface MemoryOut {
  id: string;
  user_id: string;
  memory_type: MemoryType;
  content: string;
  importance: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface MemoryCreate {
  content: string;
  memory_type?: MemoryType;
  importance?: number;
}

export interface MemoryUpdate {
  content?: string;
  memory_type?: MemoryType;
  importance?: number;
}

export interface MemoryListOut {
  items: MemoryOut[];
  next_cursor: string | null;
}

export interface MemorySearchRequest {
  query: string;
  limit?: number;
  min_similarity?: number;
}

export interface MemorySearchOut {
  items: MemoryOut[];
  count: number;
}

// ── Reminder ─────────────────────────────────────────────────────────────────

export type ReminderStatus = "pending" | "sending" | "sent" | "failed" | "cancelled" | "due";

export interface ReminderOut {
  id: string;
  user_id: string;
  title: string;
  description: string | null;
  remind_at: string;
  status: ReminderStatus;
  source: string;
  created_at: string;
  updated_at: string;
}

export interface ReminderCreate {
  title: string;
  remind_at: string;
  description?: string | null;
  source?: "ui" | "chat";
}

export interface ReminderUpdate {
  title?: string | null;
  remind_at?: string | null;
  description?: string | null;
}

export interface ReminderListOut {
  items: ReminderOut[];
  next_cursor: string | null;
}

// ── Dashboard ────────────────────────────────────────────────────────────────

export interface TodosCount {
  today: number;
  overdue: number;
  upcoming: number;
}

export interface DashboardOut {
  todos_today: TodoOut[];
  todos_count: TodosCount;
  reminders_upcoming: ReminderOut[];
  memories_count: number;
  as_of: string;
}

// ── Settings ──────────────────────────────────────────────────────────────────

export interface UserUpdateRequest {
  name?: string | null;
  timezone?: string | null;
  assistant_name?: string | null;
  locale?: string | null;
}

// ── Google Calendar (Sprint 8) ────────────────────────────────────────────────

export interface GoogleConnectOut {
  authorize_url: string;
}

export interface GoogleStatusOut {
  connected: boolean;
  email: string | null;
  scopes: string | null;
  access_token_expires_at: string | null;
}

export interface GoogleCalendarOut {
  id: string;
  summary: string;
  primary: boolean;
  time_zone: string | null;
}

// ── SSE streaming events ──────────────────────────────────────────────────────

export type SSEEvent =
  | { type: "meta"; conversation_id: string; user_message_id: string }
  | { type: "tool_start"; tool: string; label: string }
  | { type: "tool_done"; tool: string; summary: string }
  | { type: "delta"; content: string }
  | {
      type: "done";
      assistant_message_id: string;
      tokens_in: number;
      tokens_out: number;
      model: string;
    }
  | { type: "error"; code: string; message: string };
