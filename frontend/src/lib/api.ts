import {
  ApiException,
  type ChatSendRequest,
  type ChatSendResponse,
  type ConversationDetailOut,
  type ConversationListResponse,
  type NoteCreate,
  type NoteListOut,
  type NoteOut,
  type NoteUpdate,
  type SSEEvent,
  type TodoCreate,
  type TodoFilter,
  type TodoListOut,
  type TodoOut,
  type TokenResponse,
  type UserOut,
} from "@/lib/types/api";

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  name: string;
}

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

let _accessToken: string | null = null;

export function setAccessToken(token: string | null) {
  _accessToken = token;
}

class ApiClient {
  private async request<T>(path: string, init: RequestInit = {}, retry = true): Promise<T> {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      ...(init.headers as Record<string, string>),
    };

    if (_accessToken) {
      headers.Authorization = `Bearer ${_accessToken}`;
    }

    const res = await fetch(`${BASE_URL}${path}`, { ...init, headers, credentials: "include" });

    if (res.status === 401 && retry) {
      const refreshed = await this.silentRefresh();
      if (refreshed) {
        return this.request<T>(path, init, false);
      }
    }

    if (!res.ok) {
      const body = await res.json().catch(() => ({
        error: { code: "unknown", message: res.statusText, details: {}, request_id: "" },
      }));
      throw new ApiException(res.status, body.error);
    }

    if (res.status === 204) return undefined as T;
    return res.json() as Promise<T>;
  }

  async register(data: RegisterRequest): Promise<TokenResponse> {
    return this.request("/auth/register", { method: "POST", body: JSON.stringify(data) });
  }

  async login(data: LoginRequest): Promise<TokenResponse> {
    return this.request("/auth/login", { method: "POST", body: JSON.stringify(data) });
  }

  async silentRefresh(): Promise<boolean> {
    try {
      // Browser sends the httponly refresh_token cookie automatically via credentials: "include"
      const res = await fetch(`${BASE_URL}/auth/refresh`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
      });
      if (!res.ok) return false;

      const data: TokenResponse = await res.json();
      _accessToken = data.access_token;

      const { useAuthStore } = await import("@/stores/authStore");
      useAuthStore.getState().setAuth(data.user, data.access_token);
      return true;
    } catch {
      return false;
    }
  }

  async logout(): Promise<void> {
    // Browser sends the httponly refresh_token cookie automatically
    await this.request("/auth/logout", { method: "POST" });
    _accessToken = null;
  }

  async me(): Promise<UserOut> {
    return this.request("/auth/me");
  }

  async sendMessage(data: ChatSendRequest): Promise<ChatSendResponse> {
    return this.request("/v1/chat/send", { method: "POST", body: JSON.stringify(data) });
  }

  async *sendMessageStream(data: ChatSendRequest): AsyncGenerator<SSEEvent> {
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (_accessToken) headers.Authorization = `Bearer ${_accessToken}`;

    const res = await fetch(`${BASE_URL}/v1/chat/send`, {
      method: "POST",
      headers,
      credentials: "include",
      body: JSON.stringify({ ...data, stream: true }),
    });

    if (!res.ok) {
      const body = await res.json().catch(() => ({
        error: { code: "unknown", message: res.statusText, details: {}, request_id: "" },
      }));
      throw new ApiException(res.status, body.error);
    }

    const reader = res.body!.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const parts = buffer.split("\n\n");
      buffer = parts.pop() ?? "";
      for (const part of parts) {
        if (part.startsWith("data: ")) {
          try {
            yield JSON.parse(part.slice(6)) as SSEEvent;
          } catch {
            // skip malformed chunk
          }
        }
      }
    }
  }

  async listConversations(limit = 20, cursor?: string): Promise<ConversationListResponse> {
    const params = new URLSearchParams({ limit: String(limit) });
    if (cursor) params.set("cursor", cursor);
    return this.request(`/v1/chat/conversations?${params}`);
  }

  async getConversation(id: string, limit = 50): Promise<ConversationDetailOut> {
    return this.request(`/v1/chat/conversations/${id}?limit=${limit}`);
  }

  // ── Todo ───────────────────────────────────────────────────────────────────

  async listTodos(params?: {
    filter?: TodoFilter;
    status?: string;
    q?: string;
    limit?: number;
    cursor?: string;
  }): Promise<TodoListOut> {
    const p = new URLSearchParams();
    if (params?.filter) p.set("filter", params.filter);
    if (params?.status) p.set("status", params.status);
    if (params?.q) p.set("q", params.q);
    if (params?.limit) p.set("limit", String(params.limit));
    if (params?.cursor) p.set("cursor", params.cursor);
    return this.request(`/v1/todos?${p}`);
  }

  async createTodo(data: TodoCreate): Promise<TodoOut> {
    return this.request("/v1/todos", { method: "POST", body: JSON.stringify(data) });
  }

  async completeTodo(id: string): Promise<TodoOut> {
    return this.request(`/v1/todos/${id}/complete`, { method: "PATCH" });
  }

  async uncompleteTodo(id: string): Promise<TodoOut> {
    return this.request(`/v1/todos/${id}/uncomplete`, { method: "PATCH" });
  }

  async deleteTodo(id: string): Promise<void> {
    return this.request(`/v1/todos/${id}`, { method: "DELETE" });
  }

  // ── Note ───────────────────────────────────────────────────────────────────

  async listNotes(params?: {
    pinned?: boolean;
    q?: string;
    limit?: number;
    cursor?: string;
  }): Promise<NoteListOut> {
    const p = new URLSearchParams();
    if (params?.pinned !== undefined) p.set("pinned", String(params.pinned));
    if (params?.q) p.set("q", params.q);
    if (params?.limit) p.set("limit", String(params.limit));
    if (params?.cursor) p.set("cursor", params.cursor);
    return this.request(`/v1/notes?${p}`);
  }

  async createNote(data: NoteCreate): Promise<NoteOut> {
    return this.request("/v1/notes", { method: "POST", body: JSON.stringify(data) });
  }

  async updateNote(id: string, data: NoteUpdate): Promise<NoteOut> {
    return this.request(`/v1/notes/${id}`, { method: "PATCH", body: JSON.stringify(data) });
  }

  async pinNote(id: string): Promise<NoteOut> {
    return this.request(`/v1/notes/${id}/pin`, { method: "PATCH" });
  }

  async unpinNote(id: string): Promise<NoteOut> {
    return this.request(`/v1/notes/${id}/unpin`, { method: "PATCH" });
  }

  async deleteNote(id: string): Promise<void> {
    return this.request(`/v1/notes/${id}`, { method: "DELETE" });
  }
}

export const api = new ApiClient();
