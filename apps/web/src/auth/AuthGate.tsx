import { useEffect, useState, type FormEvent } from "react";
import { Button, TextInput } from "../components/ui";
import { AuthShell } from "../components/shell";
import { login, register } from "./api";
import { useAuthStore } from "./authStore";

type AuthMode = "login" | "register";

export function AuthGate({ children }: { children: React.ReactNode }) {
  const { initialized, profile, loadFromStorage, setSession } = useAuthStore();
  const [mode, setMode] = useState<AuthMode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!initialized) {
      loadFromStorage();
    }
  }, [initialized, loadFromStorage]);

  if (!initialized) {
    return <div className="min-h-screen bg-slate-950" />;
  }

  if (!profile) {
    const isRegistering = mode === "register";

    const submit = async (event: FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      setError(null);
      setSubmitting(true);

      try {
        const session = isRegistering ? await register(email, password, displayName || undefined) : await login(email, password);
        setSession(session);
      } catch {
        setError(isRegistering ? "Registration failed. Check the API URL and try again." : "Sign in failed. Check your email and password.");
      } finally {
        setSubmitting(false);
      }
    };

    return (
      <AuthShell title={isRegistering ? "Create account" : "Sign in"}>
        <form className="mt-4 grid gap-3" onSubmit={submit}>
          <TextInput label="Email" type="email" autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} required />
          <TextInput
            label="Password"
            type="password"
            autoComplete={isRegistering ? "new-password" : "current-password"}
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
          />
          {isRegistering ? (
            <TextInput
              label="Display name"
              type="text"
              autoComplete="name"
              value={displayName}
              onChange={(event) => setDisplayName(event.target.value)}
            />
          ) : null}
          {error ? <p className="rounded-md border border-red-400/40 bg-red-500/10 p-3 text-sm text-red-200">{error}</p> : null}
          <Button type="submit" variant="primary" disabled={isSubmitting}>
            {isSubmitting ? "Please wait" : isRegistering ? "Create account" : "Sign in"}
          </Button>
        </form>
        <button
          type="button"
          className="mt-4 text-left text-sm text-cyan-200 hover:text-cyan-100"
          onClick={() => {
            setMode(isRegistering ? "login" : "register");
            setError(null);
          }}
        >
          {isRegistering ? "Already approved? Sign in" : "Need access? Create an account"}
        </button>
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
