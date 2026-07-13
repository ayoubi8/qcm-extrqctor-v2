export type AppRole = "user" | "admin" | "service" | "worker";
export type ProfileStatus =
  | "pending_approval"
  | "active"
  | "suspended"
  | "deletion_requested"
  | "deleted";

export interface Profile {
  user_id: string;
  email: string;
  role: AppRole;
  status: ProfileStatus;
  display_name?: string | null;
}

export interface SessionTokens {
  access_token: string;
  refresh_token?: string | null;
  token_type: "bearer";
  expires_in_seconds?: number | null;
}

export interface AuthSession {
  profile: Profile;
  tokens: SessionTokens;
}
