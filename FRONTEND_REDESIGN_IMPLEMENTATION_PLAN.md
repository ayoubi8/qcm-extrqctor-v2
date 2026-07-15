# QCM Extractor New Version Frontend Redesign Implementation Plan

This document is a practical handoff for redesigning the frontend in:

`C:\Users\ayoub\Documents\qcm\new version\apps\web`

The goal is not to create a marketing site. The goal is to redesign the actual QCM Extractor workspace so it feels like a serious medical/academic document-processing tool: dense, calm, clear, fast to scan, and reliable during long pipeline runs.

## 1. Product Direction

QCM Extractor should feel like an operational console for extracting, correcting, validating, and exporting QCM data from PDFs.

The redesign should communicate:

- Precision: every step has a clear state, input, output, and next action.
- Control: users can run one step, run multiple steps, inspect artifacts, restore history, and monitor terminal events.
- Trust: errors, warnings, retries, and fallback states are visible without being noisy.
- Continuity: the user should always know which project, run, step, and artifact they are looking at.

Avoid:

- Landing page composition.
- Large decorative hero sections.
- Oversized cards that waste working space.
- Purely decorative gradients, blobs, or abstract illustrations.
- Text explaining the UI inside the UI.
- One-color monotony where everything is only cyan/slate.

## 2. Current Frontend Map

Primary app files:

- `apps/web/src/App.tsx`
- `apps/web/src/main.tsx`
- `apps/web/src/styles/index.css`
- `apps/web/src/design/tokens.ts`
- `apps/web/src/design/navigation.ts`

Shell:

- `apps/web/src/components/shell/AppShell.tsx`
- `apps/web/src/components/shell/Sidebar.tsx`
- `apps/web/src/components/shell/TopBar.tsx`
- `apps/web/src/components/shell/ProjectShell.tsx`

Shared UI:

- `apps/web/src/components/ui/Button.tsx`
- `apps/web/src/components/ui/Card.tsx`
- `apps/web/src/components/ui/TextInput.tsx`
- `apps/web/src/components/ui/Tabs.tsx`
- `apps/web/src/components/ui/StatusBadge.tsx`
- `apps/web/src/components/ui/Modal.tsx`

Pipeline:

- `apps/web/src/pipeline/PipelinePage.tsx`
- `apps/web/src/pipeline/StepList.tsx`
- `apps/web/src/pipeline/ConfigPanel.tsx`
- `apps/web/src/pipeline/stepRegistry.ts`
- `apps/web/src/pipeline/pipelineStore.ts`
- `apps/web/src/pipeline/step1/Step1ConfigPanel.tsx`
- `apps/web/src/pipeline/step2/Step2ConfigPanel.tsx`
- `apps/web/src/pipeline/step3-correction/Step3CorrectionConfigPanel.tsx`
- `apps/web/src/pipeline/step4-similarity/Step4SimilarityConfigPanel.tsx`

Supporting workflow:

- `apps/web/src/projects/ProjectLauncher.tsx`
- `apps/web/src/projects/HistoryRestorePanel.tsx`
- `apps/web/src/results/RunSelector.tsx`
- `apps/web/src/results/ResultHub.tsx`
- `apps/web/src/results/ArtifactViewer.tsx`
- `apps/web/src/terminal/TerminalPanel.tsx`
- `apps/web/src/terminal/TerminalEventList.tsx`
- `apps/web/src/autorun/AutoRunPanel.tsx`
- `apps/web/src/autorun/AutoRunNotification.tsx`
- `apps/web/src/ai_autorun/AiAutoRunWindow.tsx`

## 3. Design Style

Use a dark professional workspace style. The app should look like a focused extraction console, not a dashboard template.

Visual qualities:

- Background: deep neutral near-black.
- Surfaces: layered slate/charcoal with clear but subtle borders.
- Accent: cyan for primary actions and active focus, teal/emerald for successful output, amber for attention, red for destructive/error.
- Density: compact rows, clear headings, low vertical waste.
- Shape: 4px to 8px radius only.
- Borders: 1px borders should do most of the separation work.
- Shadows: use sparingly for overlays only, such as drawers and floating AI window.
- Motion: only fast, practical transitions for hover, focus, active states, and collapsible panels.

Do not use:

- Big rounded cards.
- Nested cards inside cards.
- Gradient backgrounds as the primary visual language.
- Cyan everywhere.
- Large empty sections.

## 4. Color System

Update `apps/web/src/design/tokens.ts` and `apps/web/src/styles/index.css` so all colors come from semantic tokens.

Recommended palette:

```ts
color: {
  background: "#070A0F",
  backgroundSubtle: "#0B111A",
  surface: "#111827",
  surfaceRaised: "#151F2E",
  surfaceMuted: "#1D2736",
  surfaceInset: "#080D14",
  border: "#263244",
  borderStrong: "#3B4A5F",
  text: "#F5F7FA",
  textMuted: "#9AA8BA",
  textSubtle: "#68778B",
  primary: "#38C7E8",
  primaryHover: "#67DDF2",
  primaryPressed: "#1AA8CB",
  secondary: "#44D7B6",
  success: "#35D08A",
  warning: "#F4B740",
  danger: "#F97066",
  info: "#7C9CFF"
}
```

CSS variable names:

- `--qcm-bg`
- `--qcm-bg-subtle`
- `--qcm-surface`
- `--qcm-surface-raised`
- `--qcm-surface-muted`
- `--qcm-surface-inset`
- `--qcm-border`
- `--qcm-border-strong`
- `--qcm-text`
- `--qcm-text-muted`
- `--qcm-text-subtle`
- `--qcm-primary`
- `--qcm-primary-hover`
- `--qcm-primary-pressed`
- `--qcm-secondary`
- `--qcm-success`
- `--qcm-warning`
- `--qcm-danger`
- `--qcm-info`

Usage rules:

- Background: `--qcm-bg`.
- Sidebar/topbar/footer: `--qcm-bg-subtle`.
- Main cards/panels: `--qcm-surface`.
- Selected cards/rows: transparent primary fill, such as `rgba(56, 199, 232, 0.10)`.
- Inputs: `--qcm-surface-inset`.
- Dividers: `--qcm-border`.
- Strong outlines and active borders: `--qcm-border-strong` or `--qcm-primary`.
- Primary action: cyan.
- Success state: green.
- Warning state: amber.
- Failed/destructive state: red.
- Informational metadata: blue-violet info, used rarely.

## 5. Typography

Keep Inter/system UI. Do not add decorative fonts.

Type scale:

- App title/project title: 20px, 600 weight.
- Section headings: 14px, 600 weight.
- Row primary text: 14px, 500 weight.
- Body/control text: 14px, 400 or 500 weight.
- Metadata/helper text: 12px, 400 weight.
- Terminal/log text: 12px, mono.

Rules:

- Do not use hero-sized type.
- Do not use negative letter spacing.
- Do not scale font size with viewport width.
- Use sentence case for labels and buttons.
- Use concise labels: `Run extraction`, `Run QCM extraction`, `Run correction`, `Run similarity`.
- Replace raw technical IDs in primary labels with readable text. Keep IDs in muted metadata.

Examples:

- Good primary label: `QCM extraction`
- Good metadata: `step2_orchestrate`
- Avoid primary label: `step2_orchestrate`

## 6. Button System

Refactor repeated raw buttons in step panels to use `components/ui/Button.tsx`.

Button variants:

- `primary`: main forward action, filled cyan.
- `secondary`: normal command, slate surface.
- `ghost`: low-priority command, transparent until hover.
- `danger`: destructive/cancel action.
- `success`: optional, only for confirm/apply actions after validation.
- `icon`: square icon-only controls for close, minimize, refresh, download when label is not needed.

Button dimensions:

- Normal height: 40px.
- Compact height: 32px.
- Icon button: 36px by 36px.
- Radius: 6px.
- Horizontal padding: 12px for normal buttons.

Button behavior:

- Primary default: cyan fill, dark text.
- Primary hover: brighter cyan.
- Primary pressed: darker cyan, slight inset effect or color shift.
- Secondary default: surface/inset with border.
- Secondary hover: stronger border and raised surface.
- Ghost hover: muted surface fill.
- Danger hover: stronger red background.
- Disabled: opacity 50%, cursor not allowed, no hover color.
- Focus visible: 2px cyan outline with 2px offset.

Icon rules:

- Use `lucide-react`.
- Include icons for command buttons where helpful.
- Do not use text-only controls when a standard icon button is better, especially close/minimize/refresh/download.
- Icon-only buttons must have `aria-label`.

Required button label changes:

- `Run Step 1` -> `Run extraction`
- `Run Step 2` -> `Run QCM extraction`
- `Run Correction` -> `Run correction`
- `Run Match` -> `Run similarity`
- `Refresh snapshot` -> icon button with `RefreshCw`, or `Refresh state` if text is needed.
- `AI Auto Run` -> `AI run`
- `Auto Run` -> `Auto run`

## 7. Hover, Focus, Active, Loading States

Every interactive element must have all four visible states:

- Hover: border or background shift.
- Focus-visible: cyan outline.
- Active/selected: cyan border and subtle cyan fill.
- Disabled/locked: muted opacity and cursor state.

Pipeline-specific states:

- Locked: lock icon, muted text, no hover lift.
- Ready: neutral border, subtle active hover.
- Queued: clock/list icon or loader, amber/info tone.
- Running: spinning loader and `Running` badge.
- Completed: check icon and green badge.
- Warning: amber alert icon and warning badge.
- Failed: red alert icon and error badge.

Do not show all statuses as neutral badges. Status color is functional information.

Loading state requirements:

- Buttons that trigger mutations should show a loader icon and change label, such as `Running...`.
- Panels waiting for server state should use compact skeleton rows or muted loading text.
- Do not let loading text resize buttons.

## 8. Text And Microcopy

Tone: clear, direct, operational.

Project header:

- Current: `Create, restore, run, inspect artifacts, and recover state from server snapshots.`
- Replace with: `Run extraction steps, inspect artifacts, and restore previous project state.`

Card titles:

- `Visible pipeline` -> `Pipeline`
- `Step configuration` -> `Step settings`
- `Run selector` -> `Run`
- `Results` -> `Artifacts`
- `Artifact preview` -> `Preview`
- `Persistent terminal` -> `Terminal`
- `New project` -> `Project`

Empty states:

- Artifact empty: `No artifacts for this run yet.`
- Preview empty: `Select an artifact to inspect its metadata and download it.`
- Terminal fallback: `Showing local replay events because live terminal replay is unavailable.`

Field labels:

- Every input must have a visible label.
- Do not rely on placeholders as labels.
- Numeric fields must explain units or range in a short helper line when not obvious.
- Technical configuration values may remain visible, but they should not be the only readable text.

## 9. Layout System

The redesigned workspace should use stable, responsive regions.

Desktop layout:

- Sidebar: fixed 256px left rail.
- Topbar: 64px high.
- Terminal: fixed or resizable bottom panel, default 224px.
- Main workspace: three functional columns.

Recommended desktop grid:

```txt
Left rail inside main: 300px
Center work area: minmax(0, 1fr)
Right inspector: 360px
```

Meaning:

- Left main column: project creation/restoration/history.
- Center column: pipeline steps and selected step settings.
- Right column: runs, artifacts, preview/download.

Tablet:

- Use two columns.
- Pipeline/settings should stay above artifacts.
- History/project tools can collapse above or below depending on available width.

Mobile:

- Single column.
- Topbar search should wrap cleanly.
- Sidebar navigation becomes horizontal scroll or drawer.
- Terminal should collapse to a toggleable panel to preserve vertical space.

Spacing:

- Page padding: 20px desktop, 16px tablet/mobile.
- Card padding: 16px.
- Dense row padding: 12px.
- Grid gap: 16px.
- Compact control gap: 8px.

## 10. Shell Redesign

### Sidebar

File: `apps/web/src/components/shell/Sidebar.tsx`

Keep the sidebar quiet and useful.

Changes:

- Keep brand block compact.
- Replace single-letter `Q` block with a compact mark plus label.
- Show active nav with left accent line or cyan border/fill.
- Keep labels visible on desktop.
- On mobile, convert to horizontal nav or drawer.
- Add tooltips only if nav becomes icon-only.

Sidebar colors:

- Background: `--qcm-bg-subtle`.
- Border: `--qcm-border`.
- Active: cyan border/fill.
- Hover: `--qcm-surface`.

### Topbar

File: `apps/web/src/components/shell/TopBar.tsx`

Changes:

- Search should not dominate the header.
- Add project/run context if available later.
- Keep role badge and alerts compact.
- Use icon buttons for alerts.
- Use a compact sign-out button or menu.

Topbar content priority:

1. Search projects/files.
2. Current sync status.
3. User/role/actions.

## 11. Pipeline Organization

The pipeline should be reorganized as a workflow control center.

### Step Model

Keep four main steps:

1. Text extraction
2. QCM extraction
3. Correction
4. Similarity

Enhance each step row with:

- Step number.
- Human title.
- Short plain-language purpose.
- Technical task kind as muted metadata.
- Status badge with correct tone.
- Artifact count or output types.
- Last run timestamp when available.
- Warning count if any.

Recommended step descriptions:

- Text extraction: `Extract text from the source PDF using direct, OCR, or mixed mode.`
- QCM extraction: `Convert extracted text into structured QCM JSON and Excel output.`
- Correction: `Detect and attach correction pages or vision-derived answer evidence.`
- Similarity: `Compare QCMs against reference data and export match reports.`

### StepList Redesign

File: `apps/web/src/pipeline/StepList.tsx`

Row structure:

```txt
[number/status icon] [title + description + task kind] [status badge]
```

Row behavior:

- Active row: cyan border/fill.
- Hover row: stronger border, surface raised.
- Locked row: muted, lock icon, no strong hover.
- Running row: animated loader icon.
- Completed row: green check.
- Failed row: red alert.

Do not put status badges in neutral style except for neutral statuses.

### ConfigPanel Redesign

File: `apps/web/src/pipeline/ConfigPanel.tsx`

The selected step settings should look like one coherent form, not separate raw input clusters.

Required structure:

```txt
Header:
  Step title
  Current status
  Short description

Settings groups:
  Mode
  Inputs
  Advanced options
  Output

Footer:
  Reset
  Validate if available
  Run selected step
```

Use shared components:

- `Button`
- `TextInput`
- new `SelectField`
- new `CheckboxField`
- new `SegmentedControl`
- new `NumberInput`
- new `FieldGroup`

Do not keep copy-pasted raw button/input classes in each step panel.

## 12. Step Panel Requirements

### Step 1: Text Extraction

File: `apps/web/src/pipeline/step1/Step1ConfigPanel.tsx`

Controls:

- Extraction mode as segmented control: `Automatic`, `Direct`, `OCR`, `Mixed`.
- Text repair as toggle.
- Override reason as optional text field.

Run button:

- Label: `Run extraction`
- Icon: `FileSearch`

Helper text:

- `Automatic chooses the best extraction path based on the source file.`

### Step 2: QCM Extraction

File: `apps/web/src/pipeline/step2/Step2ConfigPanel.tsx`

Controls:

- Template name.
- Year.
- Output format.
- Batch size.
- Page concurrency.
- Prompt ID.
- Model provider/model ID as read-only or advanced settings.

Organization:

- Basic settings visible by default.
- Advanced settings collapsible.

Run button:

- Label: `Run QCM extraction`
- Icon: `FileSpreadsheet`

### Step 3: Correction

File: `apps/web/src/pipeline/step3-correction/Step3CorrectionConfigPanel.tsx`

Controls:

- Correction mode segmented control: `Page detection`, `Vision`, `Auto detection`.
- Selected pages text input with helper: `Comma-separated page numbers.`
- Candidate threshold number input.
- Include neighbors toggle.
- Force overwrite toggle in advanced settings.

Run button:

- Label: `Run correction`
- Icon: `ScanSearch`

### Step 4: Similarity

File: `apps/web/src/pipeline/step4-similarity/Step4SimilarityConfigPanel.tsx`

Controls:

- Match mode segmented control: `Text only`, `Full`, `Weighted`.
- Reference database field.
- Threshold slider or number input from 0 to 1.
- Text weight and correction weight with range hints.
- Export existing toggle.
- Export QCM IDs text input with helper.

Run button:

- Label: `Run similarity`
- Icon: `FileSpreadsheet` or `GitCompare`.

## 13. Results And Artifact Inspector

### Run Selector

File: `apps/web/src/results/RunSelector.tsx`

Improve from a basic select to a compact run control:

- Label: `Run`
- Show status badge beside selected run.
- Show created/updated date when available.
- Keep native select acceptable, but style consistently.

### Result Hub

File: `apps/web/src/results/ResultHub.tsx`

Rename visible title to `Artifacts`.

Artifact row should show:

- File icon based on content type.
- Filename.
- Artifact type.
- Version badge.
- Size.
- Created date.

Active artifact:

- Cyan border/fill.

Empty state:

- `No artifacts for this run yet.`

### Artifact Viewer

File: `apps/web/src/results/ArtifactViewer.tsx`

Rename visible title to `Preview`.

Preview should show:

- File name.
- Content type badge.
- Version.
- Size, formatted as KB/MB.
- Created date.
- Artifact version ID in monospace.
- Download button.

Use a compact metadata grid instead of a paragraph.

## 14. Terminal Design

Files:

- `apps/web/src/terminal/TerminalPanel.tsx`
- `apps/web/src/terminal/TerminalEventList.tsx`

Terminal should feel like an operational event stream.

Changes:

- Title: `Terminal`.
- Fixed/resizable height target: 224px.
- Mono font at 12px.
- Rows should include timestamp, level, message.
- Level colors:
  - success: green.
  - warning: amber.
  - error: red.
  - info/system: cyan or muted.
- Add compact toolbar actions:
  - copy
  - clear visual filter
  - collapse/expand if implemented

Do not make terminal a big card inside the footer. It should be integrated with the app frame.

## 15. Auto Run Panel

File: `apps/web/src/autorun/AutoRunPanel.tsx`

The panel is a right-side drawer.

Design requirements:

- Width: 420px desktop, full width mobile.
- Header: title, short subtitle, close icon button.
- Step list: checkbox rows with status and task kind.
- Footer: sticky action bar.
- Buttons:
  - Validate: secondary.
  - Start: primary.
  - Pause/Retry: ghost or secondary.
  - Cancel: danger.
  - Close: icon button in header, not a footer text button.

Validation output:

- Success uses green bordered panel.
- Errors use red bordered panel.
- Warnings use amber bordered panel.

## 16. AI Auto Run Window

File: `apps/web/src/ai_autorun/AiAutoRunWindow.tsx`

Redesign AI Auto Run as a guided automation progress window, inspired by the reference screenshot style, but adapted to QCM Extractor.

The user should not configure models, templates, correction modes, thresholds, prompts, or metadata manually inside this window. The only user choice happens before launch:

- Create a new project, upload/select source PDF, then click `AI run`.
- Or restore/select an old project, then click `AI run`.

After launch, the AI Auto Run window should show what the system is doing, what it selected, and what it completed. It should feel like the app is working with intelligence and transparency, while keeping configuration automatic.

Design requirements:

- Width: max 420px.
- Header with bot icon, title, minimize, close.
- Use icon buttons with `aria-label`.
- Avoid nested cards. The floating window itself is the container.
- Remove the current planner form fields from the visible UI:
  - No `Primary model` input.
  - No `Template` input.
  - No `Correction mode` select.
- Replace the old safety note with: `For wrong results, use manual mode.`
- Buttons:
  - Launch: primary, before run starts.
  - Retry: secondary.
  - Cancel: danger.
  - Open results: primary, after run succeeds.

Do not expose chain-of-thought or private reasoning. Only show stage names, selected configs, evidence summaries, progress counts, statuses, and errors.

### AI Auto Run Experience

The window should work like a progress timeline.

Initial state:

```txt
AI Auto Run

Ready to run automatic extraction for this project.

[Launch AI run]
```

Running state:

```txt
AI Auto Run

[spinner] We are analyzing your document...
[empty]   We are checking the resident trends...
[empty]   We are identifying the final outputs...
[empty]   Preparing corrections and results...

For wrong results, use manual mode.
```

Completed state:

```txt
AI Auto Run

[check] Done

60 QCMs extracted and corrections matched.

[Open results]
[Run again]
```

### AI Stage Titles

Use four main user-facing stage titles. They should be calm, readable, and human. These are progress titles, not technical logs.

1. `We are analyzing your document...`
2. `We are checking the resident trends...`
3. `We are identifying the final outputs...`
4. `Preparing corrections and results...`

Use `resident` exactly if the project vocabulary is medical residency. Do not use the typo `residanat` in UI text.

### AI Stage 1: Document Analysis And Text Extraction

User-facing title:

`We are analyzing your document...`

Detailed progress lines shown under this active stage:

```txt
Choosing extraction mode...
Direct PDF extraction selected.
OCR selected for scanned pages.
Page 1 extracted.
Page 2 extracted.
Page 3 extracted.
Text extraction finished.
```

Rules:

- The system decides between `direct PDF extraction`, `OCR`, or `mixed extraction`.
- If OCR is selected, show `OCR selected for scanned pages.`
- If direct extraction is selected, show `Direct PDF extraction selected.`
- If mixed mode is selected, show `Mixed extraction selected.`
- Show page-by-page progress when available.
- End with `Text extraction finished.`

### AI Stage 2: QCM Extraction And Metadata Detection

User-facing title:

`We are checking the resident trends...`

Detailed progress lines:

```txt
QCM extraction started...
7 QCMs extracted.
10 QCMs extracted.
9 QCMs extracted.
Total extracted: 60 QCMs.
AI is choosing metadata detection config...
Step config selected.
Metadata detection started...
Metadata detected.
```

Rules:

- Show running extracted counts as the backend reports batches.
- Always show the total when extraction finishes.
- Let the AI choose metadata config automatically.
- Show only concise decisions, not hidden reasoning.
- Good text: `AI is choosing metadata detection config...`
- Bad text: `AI reasoning: I chose this because...`

### AI Stage 3: Output Generation

User-facing title:

`We are identifying the final outputs...`

Detailed progress lines:

```txt
Building JSON output...
Building XLSX output...
JSON and XLSX generated.
```

Alternative if only JSON is produced:

```txt
Building JSON output...
JSON generated.
```

Rules:

- Use `JSON`, not `jsond`.
- Use `XLSX`, not `xlsx` in final polished UI labels.
- After output generation, automatically update the artifact/results area.

### AI Stage 4: Correction Matching And Final Results

User-facing title:

`Preparing corrections and results...`

Detailed progress lines:

```txt
AI is setting correction config...
Correction config selected.
Correction matching started...
60 corrections found and matched.
Results are ready.
```

Rules:

- The AI sets correction config automatically.
- Show correction matching progress if available.
- End with a strong success state.
- The success state should be visibly green and celebratory but still professional.

### Done State

When the full AI run succeeds:

- Show a large green check icon.
- Show large text: `Done`.
- Show summary: `60 QCMs extracted and corrections matched.`
- Open the results automatically in the right-side results/preview area.
- Select the latest run automatically.
- Select the newest primary artifact automatically.
- If app routing supports tabs, open the results view in a new app tab/section automatically.
- If browser popup rules block a real new browser tab, do not force a popup. Instead switch the in-app view to results and show an `Open results` button.

Done state layout:

```txt
        [green check icon]
              Done
60 QCMs extracted and corrections matched.

[Open results] [Run again]
```

### Error State

If AI Auto Run fails:

```txt
AI Auto Run

[failed stage] QCM extraction failed.

The run stopped before outputs were generated.

[Retry] [Use manual mode]
```

Rules:

- Show the failed stage.
- Preserve completed stage logs above the failed stage.
- Offer retry.
- Offer manual mode.
- Do not hide partial artifacts if they exist.

### Visual Style For The Floating Window

Follow the main redesign plan tokens, but use a slightly lighter panel surface so it reads as a focused modal:

- Backdrop behind modal: `rgba(7, 10, 15, 0.62)` with blur.
- Window background: `--qcm-surface-raised`.
- Border: `1px solid rgba(56, 199, 232, 0.32)`.
- Top accent line: cyan, showing progress percentage.
- Radius: 8px.
- Shadow: strong overlay shadow only here.
- Width: `min(460px, calc(100vw - 32px))`.
- Mobile: centered with 16px margins.

Timeline row styles:

- Active stage: cyan spinner or partial ring, bright text.
- Completed stage: green check, normal bright text.
- Pending stage: muted empty circle, muted text.
- Failed stage: red alert icon, red text.
- Detail logs: 12px muted text, indented below the active/completed stage.

Do not use a white modal like the screenshot if the rest of the app is dark. Keep it consistent with the QCM Extractor dark console style.

### Required AI Auto Run State Model

GLM should add a UI state model that can represent stage progress without depending on hidden AI reasoning.

Suggested frontend types:

```ts
type AiAutoRunStageId =
  | "document_analysis"
  | "qcm_extraction"
  | "output_generation"
  | "correction_matching";

type AiAutoRunStageStatus = "pending" | "active" | "completed" | "failed";

interface AiAutoRunStageView {
  id: AiAutoRunStageId;
  title: string;
  status: AiAutoRunStageStatus;
  detailLines: string[];
}

interface AiAutoRunProgressView {
  status: "idle" | "running" | "completed" | "failed";
  percent: number;
  stages: AiAutoRunStageView[];
  extractedQcmCount?: number;
  matchedCorrectionCount?: number;
  latestRunId?: string;
  latestArtifactVersionId?: string;
  errorMessage?: string;
}
```

This state can be fed by real backend events later. For now, GLM may map existing run/terminal events into this structure.

## 17. Shared Components To Add Or Improve

Add these components under `apps/web/src/components/ui/`:

- `IconButton.tsx`
- `SelectField.tsx`
- `CheckboxField.tsx`
- `ToggleField.tsx`
- `NumberInput.tsx`
- `SegmentedControl.tsx`
- `FieldGroup.tsx`
- `EmptyState.tsx`
- `MetadataGrid.tsx`
- `Spinner.tsx`

Update `apps/web/src/components/ui/index.ts` to export them.

Component rules:

- All controls accept `disabled`.
- All fields accept `label`, `helperText`, and error text when useful.
- All controls use semantic tokens or Tailwind classes mapped to the token palette.
- Do not duplicate long Tailwind strings across step panels.

## 18. Accessibility Requirements

Must-have:

- All icon-only buttons have `aria-label`.
- All inputs have labels.
- Segmented controls use `aria-pressed` or radio semantics.
- Disabled/locked controls communicate disabled state.
- Focus-visible state is obvious.
- Color is not the only status signal; use icon and text too.
- Text contrast must stay readable on dark backgrounds.
- Buttons keep stable size when loading.

## 19. Responsive Requirements

Desktop target:

- 1440px wide should show the full three-column workflow.
- No major panels should overlap.
- Terminal should remain visible without covering the main content.

Tablet target:

- 768px wide should use two columns or stacked major sections.
- Buttons wrap cleanly.
- Step rows remain readable.

Mobile target:

- 390px wide should be fully usable.
- No button text should overflow.
- Forms stack.
- Sidebar becomes horizontal nav or drawer.
- Right inspector stacks below pipeline.
- Floating AI window uses `calc(100vw - 32px)` width.

## 20. Implementation Order

### Phase 1: Token And Component Foundation

Files:

- `apps/web/src/design/tokens.ts`
- `apps/web/src/styles/index.css`
- `apps/web/src/components/ui/*`

Tasks:

1. Replace the color palette with the semantic palette in this plan.
2. Add missing CSS variables.
3. Upgrade `Button` with loading, compact, icon-friendly support.
4. Add `IconButton`, `SegmentedControl`, `SelectField`, `CheckboxField`, `ToggleField`, `NumberInput`, `FieldGroup`, `EmptyState`, `MetadataGrid`, and `Spinner`.
5. Export all shared components.

### Phase 2: Shell Redesign

Files:

- `AppShell.tsx`
- `Sidebar.tsx`
- `TopBar.tsx`
- `ProjectShell.tsx`

Tasks:

1. Apply the new color and spacing system.
2. Make sidebar and topbar responsive.
3. Improve active navigation state.
4. Simplify topbar actions.
5. Tighten project header text and actions.

### Phase 3: Pipeline Redesign

Files:

- `PipelinePage.tsx`
- `StepList.tsx`
- `ConfigPanel.tsx`
- all step config panels

Tasks:

1. Rename visible titles: `Pipeline`, `Step settings`, `Artifacts`, `Preview`, `Run`, `Terminal`.
2. Redesign `StepList` rows with number, icon, description, metadata, and status.
3. Replace raw step-panel controls with shared field components.
4. Add advanced sections where appropriate.
5. Add loading labels and disabled states to run buttons.
6. Keep the three-column workflow but improve responsive behavior.

### Phase 4: Results, Terminal, Auto Run

Files:

- `RunSelector.tsx`
- `ResultHub.tsx`
- `ArtifactViewer.tsx`
- `TerminalPanel.tsx`
- `TerminalEventList.tsx`
- `AutoRunPanel.tsx`
- `AiAutoRunWindow.tsx`

Tasks:

1. Redesign artifact rows and preview metadata.
2. Integrate terminal visually with the app frame.
3. Redesign Auto Run drawer with sticky footer and close icon.
4. Redesign AI Auto Run as an automatic guided progress window with no visible user configuration fields.
5. Improve empty, fallback, error, and success states.

### Phase 5: QA And Polish

Tasks:

1. Run `npm --workspace apps/web run build`.
2. Check desktop at 1440px.
3. Check tablet at 768px.
4. Check mobile at 390px.
5. Verify no text overflows buttons, badges, cards, or panels.
6. Verify keyboard focus for all controls.
7. Verify locked, ready, running, completed, warning, and failed states.
8. Verify terminal content does not break layout.
9. Verify drawer and floating window stay within viewport.

## 21. Acceptance Checklist

The redesign is complete when:

- The app opens directly into the working QCM extraction console.
- The user can identify the current project, run, selected step, and selected artifact at a glance.
- The pipeline has clear status, sequence, outputs, and next actions.
- All step settings use consistent shared controls.
- Buttons have consistent hover, focus, disabled, active, and loading states.
- Inputs have visible labels.
- Colors come from semantic tokens.
- Artifacts and terminal events are easy to scan.
- Auto Run and AI Auto Run feel integrated, not bolted on.
- AI Auto Run requires no visible configuration after project selection and shows automatic stage progress.
- AI Auto Run ends with a green `Done` state and opens/selects the latest results automatically.
- The UI works without overlap at desktop, tablet, and mobile widths.
- `npm --workspace apps/web run build` passes.

## 22. Important Constraint

This plan is only for the new version frontend:

`C:\Users\ayoub\Documents\qcm\new version\apps\web`

Do not redesign the old frontend at:

`C:\Users\ayoub\Documents\qcm\frontend`
