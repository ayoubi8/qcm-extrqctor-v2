import {
  Bot,
  FolderKanban,
  History,
  LayoutDashboard,
  Settings,
  ShieldCheck,
  TerminalSquare
} from "lucide-react";

export const mainNavigation = [
  { id: "dashboard", label: "Dashboard", icon: LayoutDashboard },
  { id: "projects", label: "Projects", icon: FolderKanban },
  { id: "history", label: "History", icon: History },
  { id: "terminal", label: "Terminal", icon: TerminalSquare },
  { id: "autorun", label: "AI Auto Run", icon: Bot },
  { id: "settings", label: "Settings", icon: Settings }
] as const;

export const adminNavigation = [{ id: "admin", label: "Admin", icon: ShieldCheck }] as const;

export type NavigationItemId = (typeof mainNavigation)[number]["id"] | (typeof adminNavigation)[number]["id"];
