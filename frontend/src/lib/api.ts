import {
  ApiException,
  type ChatSendRequest,
  type ChatSendResponse,
  type ConversationListResponse,
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

  async listConversations(limit = 20, cursor?: string): Promise<ConversationListResponse> {
    const params = new URLSearchParams({ limit: String(limit) });
    if (cursor) params.set("cursor", cursor);
    return this.request(`/v1/chat/conversations?${params}`);
  }
}

export const api = new ApiClient();
