# Plan 13 Frontend Design System And Application Shell Notes

Status: implemented as a dependency-light frontend shell foundation.

Implemented:

- Preserved dark QCM Extractor identity with CSS variables and exported TypeScript design tokens.
- Tailwind token extensions for QCM background, surface, border, primary, secondary, tertiary, success, and danger colors.
- Reusable UI primitives for buttons, cards, badges, inputs, tabs, and modal dialogs.
- Reusable shell components for auth shell, app shell, sidebar, top bar, and project shell.
- App placeholder upgraded from a Plan 02 card grid to the Plan 13 operational shell with sidebar, top bar, project header, tabs, status badges, and persistent terminal footer.
- Accessibility hooks for focus-visible states, labelled navigation, dialog semantics, and stable shell dimensions.
- Static visual regression matrix covering auth, shell, terminal, modal, loading, error, and responsive viewports.
- Plan 13 verifier for tokens, shell structure, accessibility hooks, and the visual matrix.

Deferred to later plans:

- Full project, pipeline, history, results, settings, and admin pages.
- Playwright screenshot generation once frontend dependencies are installed and the app can run in browser.
- User preference persistence for theme and shell layout.

Verification:

```powershell
python -B tools/verify_foundation.py
python -B tools/verify_migrations.py
python -B tools/verify_storage.py
python -B tools/verify_backend.py
python -B tools/verify_tasks.py
python -B tools/verify_step1.py
python -B tools/verify_step2.py
python -B tools/verify_step2_pages.py
python -B tools/verify_step2_metadata.py
python -B tools/verify_step3_correction.py
python -B tools/verify_step4_similarity.py
python -B tools/verify_frontend_shell.py
python -B -m unittest discover tests
```

Result: all commands passed locally after Plan 13 implementation. Vite/TypeScript browser build was not run because `apps/web/node_modules` is not installed in this workspace.

Next plan: Plan 14 Frontend Projects, Pipeline, History, Results, And Terminal.
