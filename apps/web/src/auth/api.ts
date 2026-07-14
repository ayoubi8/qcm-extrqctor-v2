import type { AuthSession } from "./types";
import { API_BASE_URL } from "../config/apiBaseUrl";

const BASE_URL = API_BASE_URL;

async function errorMessage(response: Response, fallback: string) {
  try {
    const payload = (await response.json()) as { detail?: string };
    return payload.detail ?? fallback;
  } catch {
    return fallback;
  }
}

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
    throw new Error(await errorMessage(response, "Login failed"));
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
    throw new Error(await errorMessage(response, "Registration failed"));
  }

  return response.json() as Promise<AuthSession>;
}
