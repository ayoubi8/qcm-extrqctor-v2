import { adminNavigation, mainNavigation, type NavigationItemId } from "../../design/navigation";
import type { Profile } from "../../auth/types";

interface SidebarProps {
  activeId: NavigationItemId;
  profile: Profile;
  onNavigate: (id: NavigationItemId) => void;
}

export function Sidebar({ activeId, profile, onNavigate }: SidebarProps) {
  const items = profile.role === "admin" ? [...mainNavigation, ...adminNavigation] : mainNavigation;

  return (
    <aside className="flex w-full shrink-0 flex-col border-r border-slate-800 bg-slate-950 lg:w-[var(--qcm-sidebar-width)]">
      <div className="flex min-h-16 items-center gap-3 border-b border-slate-800 px-4">
        <div className="grid h-9 w-9 place-items-center rounded-md border border-cyan-400/50 bg-cyan-400/10 font-mono text-sm font-semibold text-cyan-200">
          Q
        </div>
        <div>
          <div className="text-sm font-semibold text-slate-100">QCM Extractor</div>
          <div className="text-xs text-slate-500">Re-engineered</div>
        </div>
      </div>
      <nav className="flex gap-1 overflow-x-auto p-3 lg:flex-col lg:overflow-visible" aria-label="Main navigation">
        {items.map((item) => (
          <button
            key={item.id}
            type="button"
            className={`flex min-h-10 shrink-0 items-center gap-3 rounded-md border px-3 text-left text-sm transition-colors ${
              activeId === item.id
                ? "border-cyan-400/60 bg-cyan-400/10 text-cyan-100"
                : "border-transparent text-slate-400 hover:bg-slate-900 hover:text-slate-100"
            }`}
            onClick={() => onNavigate(item.id)}
          >
            <item.icon className="h-4 w-4" aria-hidden="true" />
            <span>{item.label}</span>
          </button>
        ))}
      </nav>
    </aside>
  );
}
