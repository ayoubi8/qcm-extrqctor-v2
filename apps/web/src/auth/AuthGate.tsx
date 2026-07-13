import { useEffect } from "react";
import { AuthShell } from "../components/shell";
import { useAuthStore } from "./authStore";

export function AuthGate({ children }: { children: React.ReactNode }) {
  const { initialized, profile, loadFromStorage } = useAuthStore();

  useEffect(() => {
    if (!initialized) {
      loadFromStorage();
    }
  }, [initialized, loadFromStorage]);

  if (!initialized) {
    return <div className="min-h-screen bg-slate-950" />;
  }

  if (!profile) {
    return (
      <AuthShell title="Sign in required">
        <p>The rebuilt workspace uses approved Supabase profiles and owner-scoped access.</p>
      </AuthShell>
    );
  }

  if (profile.status !== "active") {
    return (
      <AuthShell title="Approval pending" tone="warning">
        <p>Your account exists, but an admin must approve it before project data is available.</p>
      </AuthShell>
    );
  }

  return <>{children}</>;
}
