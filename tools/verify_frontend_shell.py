"""Verify Plan 13 frontend design tokens, shell structure, and visual test manifest."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_PATHS = [
    "apps/web/src/design/tokens.ts",
    "apps/web/src/design/navigation.ts",
    "apps/web/src/styles/index.css",
    "apps/web/src/components/ui/Button.tsx",
    "apps/web/src/components/ui/Card.tsx",
    "apps/web/src/components/ui/Modal.tsx",
    "apps/web/src/components/ui/StatusBadge.tsx",
    "apps/web/src/components/ui/Tabs.tsx",
    "apps/web/src/components/ui/TextInput.tsx",
    "apps/web/src/components/shell/AppShell.tsx",
    "apps/web/src/components/shell/AuthShell.tsx",
    "apps/web/src/components/shell/ProjectShell.tsx",
    "apps/web/src/components/shell/Sidebar.tsx",
    "apps/web/src/components/shell/TopBar.tsx",
    "tests/visual/plan13_visual_matrix.json",
]


def text(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def main() -> int:
    missing = [path for path in REQUIRED_PATHS if not (ROOT / path).exists()]
    if missing:
        raise AssertionError(f"Missing Plan 13 frontend shell paths: {missing}")

    tokens = text("apps/web/src/design/tokens.ts")
    for expected in ["#020617", "#22d3ee", "sidebarWidth", "terminalHeight"]:
        assert expected in tokens

    css = text("apps/web/src/styles/index.css")
    for expected in ["--qcm-bg", "--qcm-primary", "focus-visible", "::-webkit-scrollbar"]:
        assert expected in css

    app_shell = text("apps/web/src/components/shell/AppShell.tsx")
    project_shell = text("apps/web/src/components/shell/ProjectShell.tsx")
    for expected in ["Sidebar", "TopBar", "terminal"]:
        assert expected in app_shell
    for expected in ["StatusBadge", "actions", "children"]:
        assert expected in project_shell

    sidebar = text("apps/web/src/components/shell/Sidebar.tsx")
    assert "w-[var(--qcm-sidebar-width)]" in sidebar
    assert "aria-label=\"Main navigation\"" in sidebar

    modal = text("apps/web/src/components/ui/Modal.tsx")
    assert "role=\"dialog\"" in modal
    assert "aria-modal=\"true\"" in modal

    manifest = json.loads(text("tests/visual/plan13_visual_matrix.json"))
    assert manifest["plan"] == 13
    assert {item["name"] for item in manifest["viewports"]} == {"mobile", "tablet", "desktop"}
    assert "dashboard-shell" in manifest["states"]

    print("Plan 13 frontend design tokens, shell, accessibility hooks, and visual matrix verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
