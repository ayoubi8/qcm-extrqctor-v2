import { useState, type ReactNode } from "react";
import { useAuthStore } from "../../auth/authStore";
import type { NavigationItemId } from "../../design/navigation";
import { Sidebar } from "./Sidebar";
import { TopBar } from "./TopBar";

interface AppShellProps {
  children: ReactNode;
  terminal?: ReactNode;
}

export function AppShell({ children, terminal }: AppShellProps) {
  const { profile, clearSession } = useAuthStore();
  const [activeId, setActiveId] = useState<NavigationItemId>("dashboard");

  if (!profile) {
    return null;
  }

  return (
    <div className="flex min-h-screen flex-col bg-slate-950 text-slate-100 lg:flex-row">
      <Sidebar activeId={activeId} profile={profile} onNavigate={setActiveId} />
      <div className="flex min-h-screen min-w-0 flex-1 flex-col">
        <TopBar profile={profile} onSignOut={clearSession} />
        <main className="min-h-0 flex-1 overflow-y-auto px-4 py-5 lg:px-6">{children}</main>
        {terminal ? <footer className="border-t border-slate-800 bg-slate-950">{terminal}</footer> : null}
      </div>
    </div>
  );
}
