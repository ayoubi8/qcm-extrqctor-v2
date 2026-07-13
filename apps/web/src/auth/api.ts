import type { AuthSession } from "./types";

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

function correlationId() {
  return crypto.randomUUID();
}

export async function login(email: string, password: string): Promise<AuthSession> {
  const response = await fetch(`${BASE_URL}/auth/login`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Correlation-Id": correlationId()
    },
    body: JSON.stringify({ email, password })
  });

  if (!response.ok) {
    throw new Error("Login failed");
  }

  return response.json() as Promise<AuthSession>;
}

export async function register(email: string, password: string, displayName?: string): Promise<AuthSession> {
  const response = await fetch(`${BASE_URL}/auth/register`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Correlation-Id": correlationId()
    },
    body: JSON.stringify({ email, password, display_name: displayName })
  });

  if (!response.ok) {
    throw new Error("Registration failed");
  }

  return response.json() as Promise<AuthSession>;
}
