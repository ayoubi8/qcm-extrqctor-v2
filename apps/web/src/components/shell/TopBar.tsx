import { Bell, LogOut, Search } from "lucide-react";
import type { Profile } from "../../auth/types";
import { Button, StatusBadge } from "../ui";

interface TopBarProps {
  profile: Profile;
  onSignOut: () => void;
}

export function TopBar({ profile, onSignOut }: TopBarProps) {
  return (
    <header className="flex min-h-16 flex-wrap items-center justify-between gap-3 border-b border-slate-800 bg-slate-950/95 px-4">
      <label className="flex min-h-10 w-full max-w-md items-center gap-2 rounded-md border border-slate-800 bg-slate-900 px-3 text-sm text-slate-400" htmlFor="shell-search">
        <Search className="h-4 w-4" aria-hidden="true" />
        <input id="shell-search" className="w-full bg-transparent text-slate-100 outline-none placeholder:text-slate-500" placeholder="Search projects" />
      </label>
      <div className="flex items-center gap-2">
        <StatusBadge tone={profile.role === "admin" ? "warning" : "info"}>{profile.role}</StatusBadge>
        <Button variant="ghost" icon={<Bell className="h-4 w-4" aria-hidden="true" />}>
          Alerts
        </Button>
        <Button variant="secondary" icon={<LogOut className="h-4 w-4" aria-hidden="true" />} onClick={onSignOut}>
          Sign out
        </Button>
      </div>
    </header>
  );
}
