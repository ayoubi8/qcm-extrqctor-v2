"""Verify the Plan 01 foundation without requiring third-party packages."""

from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYTHONPATHS = [
    ROOT / "packages" / "domain" / "src",
    ROOT / "packages" / "application" / "src",
    ROOT / "packages" / "infrastructure" / "src",
    ROOT / "packages" / "observability" / "src",
    ROOT / "packages" / "shared" / "src",
    ROOT / "apps" / "api" / "src",
    ROOT / "apps" / "worker" / "src",
]

REQUIRED_PATHS = [
    "apps/api/src/qcm_api/main.py",
    "apps/api/src/qcm_api/error_handlers.py",
    "apps/api/src/qcm_api/routes/artifacts.py",
    "apps/api/src/qcm_api/routes/auth.py",
    "apps/api/src/qcm_api/routes/ai_autorun.py",
    "apps/api/src/qcm_api/routes/autorun.py",
    "apps/api/src/qcm_api/routes/config.py",
    "apps/api/src/qcm_api/routes/health.py",
    "apps/api/src/qcm_api/routes/projects.py",
    "apps/api/src/qcm_api/routes/reference_dbs.py",
    "apps/api/src/qcm_api/routes/step1.py",
    "apps/api/src/qcm_api/routes/step2.py",
    "apps/api/src/qcm_api/routes/step3_correction.py",
    "apps/api/src/qcm_api/routes/step4_similarity.py",
    "apps/api/src/qcm_api/routes/tasks.py",
    "apps/api/src/qcm_api/routes/terminal.py",
    "apps/worker/src/qcm_worker/auth_context.py",
    "apps/worker/src/qcm_worker/ai_autorun_handler.py",
    "apps/worker/src/qcm_worker/autorun_handler.py",
    "apps/worker/src/qcm_worker/cleanup.py",
    "apps/worker/src/qcm_worker/health.py",
    "apps/worker/src/qcm_worker/main.py",
    "apps/worker/src/qcm_worker/runner.py",
    "apps/worker/src/qcm_worker/step1_handler.py",
    "apps/worker/src/qcm_worker/step2_orchestrator_handler.py",
    "apps/worker/src/qcm_worker/step3_correction_handler.py",
    "apps/worker/src/qcm_worker/step4_similarity_handler.py",
    "apps/web/src/pipeline/step1/api.ts",
    "apps/web/src/pipeline/step1/Step1ConfigPanel.tsx",
    "apps/web/src/pipeline/step1/types.ts",
    "apps/web/src/pipeline/step2/api.ts",
    "apps/web/src/pipeline/step2/AdvancedMetadata.tsx",
    "apps/web/src/pipeline/step2/Step2ConfigPanel.tsx",
    "apps/web/src/pipeline/step2/types.ts",
    "apps/web/src/pipeline/step3-correction/api.ts",
    "apps/web/src/pipeline/step3-correction/Step3CorrectionConfigPanel.tsx",
    "apps/web/src/pipeline/step3-correction/types.ts",
    "apps/web/src/pipeline/step4-similarity/api.ts",
    "apps/web/src/pipeline/step4-similarity/Step4SimilarityConfigPanel.tsx",
    "apps/web/src/pipeline/step4-similarity/types.ts",
    "apps/web/src/api/client.ts",
    "apps/web/src/components/shell/AppShell.tsx",
    "apps/web/src/components/shell/AuthShell.tsx",
    "apps/web/src/components/shell/ProjectShell.tsx",
    "apps/web/src/components/shell/Sidebar.tsx",
    "apps/web/src/components/shell/TopBar.tsx",
    "apps/web/src/components/ui/Button.tsx",
    "apps/web/src/components/ui/Card.tsx",
    "apps/web/src/components/ui/Modal.tsx",
    "apps/web/src/components/ui/StatusBadge.tsx",
    "apps/web/src/components/ui/Tabs.tsx",
    "apps/web/src/components/ui/TextInput.tsx",
    "apps/web/src/design/navigation.ts",
    "apps/web/src/design/tokens.ts",
    "apps/web/src/projects/HistoryRestorePanel.tsx",
    "apps/web/src/projects/ProjectLauncher.tsx",
    "apps/web/src/projects/types.ts",
    "apps/web/src/pipeline/ConfigPanel.tsx",
    "apps/web/src/pipeline/PipelinePage.tsx",
    "apps/web/src/pipeline/StepList.tsx",
    "apps/web/src/pipeline/pipelineStore.ts",
    "apps/web/src/pipeline/stepRegistry.ts",
    "apps/web/src/pipeline/types.ts",
    "apps/web/src/styles/index.css",
    "apps/web/src/results/ArtifactViewer.tsx",
    "apps/web/src/results/ResultHub.tsx",
    "apps/web/src/results/RunSelector.tsx",
    "apps/web/src/results/types.ts",
    "apps/web/src/terminal/api.ts",
    "apps/web/src/terminal/TerminalPanel.tsx",
    "apps/web/src/terminal/TerminalEventList.tsx",
    "apps/web/src/terminal/useTerminalReplay.ts",
    "apps/web/src/App.tsx",
    "apps/web/src/ai_autorun/AiAutoRunWindow.tsx",
    "apps/web/src/ai_autorun/aiAutoRunStore.ts",
    "apps/web/src/ai_autorun/api.ts",
    "apps/web/src/ai_autorun/types.ts",
    "apps/web/src/auth/authStore.ts",
    "apps/web/src/auth/AuthGate.tsx",
    "apps/web/src/autorun/AutoRunNotification.tsx",
    "apps/web/src/autorun/AutoRunPanel.tsx",
    "apps/web/src/autorun/api.ts",
    "apps/web/src/autorun/autorunStore.ts",
    "apps/web/src/autorun/types.ts",
    "packages/domain/src/qcm_domain/artifacts.py",
    "packages/domain/src/qcm_domain/ai_autorun.py",
    "packages/domain/src/qcm_domain/auth.py",
    "packages/domain/src/qcm_domain/corrections.py",
    "packages/domain/src/qcm_domain/documents.py",
    "packages/domain/src/qcm_domain/qcm.py",
    "packages/domain/src/qcm_domain/reference_db.py",
    "packages/domain/src/qcm_domain/templates.py",
    "packages/domain/src/qcm_domain/steps/step2_contracts.py",
    "packages/domain/src/qcm_domain/errors.py",
    "packages/domain/src/qcm_domain/tasks.py",
    "packages/domain/src/qcm_domain/enums.py",
    "packages/application/src/qcm_application/artifact_service.py",
    "packages/application/src/qcm_application/ai_autorun_service.py",
    "packages/application/src/qcm_application/auth_service.py",
    "packages/application/src/qcm_application/autorun_service.py",
    "packages/application/src/qcm_application/config_snapshot.py",
    "packages/application/src/qcm_application/ownership.py",
    "packages/application/src/qcm_application/ports.py",
    "packages/application/src/qcm_application/provider_service.py",
    "packages/application/src/qcm_application/reference_db_service.py",
    "packages/application/src/qcm_application/repositories.py",
    "packages/application/src/qcm_application/task_service.py",
    "packages/application/src/qcm_application/steps/step1_service.py",
    "packages/application/src/qcm_application/steps/step2_finalize.py",
    "packages/application/src/qcm_application/steps/step2_format.py",
    "packages/application/src/qcm_application/steps/step2_metadata.py",
    "packages/application/src/qcm_application/steps/step2_pages.py",
    "packages/application/src/qcm_application/steps/step2_orchestrator.py",
    "packages/application/src/qcm_application/steps/step3_correction_service.py",
    "packages/application/src/qcm_application/steps/step4_similarity_service.py",
    "packages/application/src/qcm_application/use_cases/projects.py",
    "packages/application/src/qcm_application/use_cases/runs.py",
    "packages/infrastructure/src/qcm_infrastructure/db/repositories.py",
    "packages/infrastructure/src/qcm_infrastructure/llm/openrouter_adapter.py",
    "packages/infrastructure/src/qcm_infrastructure/tasks/memory.py",
    "packages/observability/src/qcm_observability/budget.py",
    "packages/observability/src/qcm_observability/health.py",
    "packages/observability/src/qcm_observability/logging.py",
    "packages/infrastructure/src/qcm_infrastructure/storage/base.py",
    "packages/infrastructure/src/qcm_infrastructure/storage/supabase_adapter.py",
    "packages/infrastructure/src/qcm_infrastructure/auth/supabase_adapter.py",
    "packages/infrastructure/src/qcm_infrastructure/providers/openrouter.py",
    "packages/infrastructure/src/qcm_infrastructure/pdf/base.py",
    "packages/infrastructure/src/qcm_infrastructure/pdf/fakes.py",
    "packages/shared/src/qcm_shared/auth_contracts.py",
    "packages/shared/src/qcm_shared/ai_autorun_contracts.py",
    "packages/shared/src/qcm_shared/autorun_contracts.py",
    "packages/shared/src/qcm_shared/api_contracts.py",
    "packages/shared/src/qcm_shared/contracts.py",
    "packages/shared/src/qcm_shared/provider_contracts.py",
    "packages/shared/src/qcm_shared/storage_contracts.py",
    "packages/shared/src/qcm_shared/task_contracts.py",
    "packages/shared/src/qcm_shared/step1_contracts.py",
    "packages/shared/src/qcm_shared/step2_contracts.py",
    "packages/shared/src/qcm_shared/step3_contracts.py",
    "packages/shared/src/qcm_shared/step4_contracts.py",
    "artifact-schemas/v1/artifact_manifest.schema.json",
    "migrations/0001_profiles_projects.sql",
    "migrations/0002_runs_tasks_artifacts.sql",
    "migrations/0003_step_specific.sql",
    "migrations/0004_legacy_import_validation.sql",
    "prompts/v1/registry.json",
    "prompts/ai_autorun/planner.v1.md",
    "prompts/ai_autorun/evaluator.v1.md",
    ".github/workflows/verify.yml",
    "infra/env.schema.json",
    "infra/vercel/vercel.json",
    "infra/supabase/config.toml",
    "infra/supabase/storage_policies.sql",
    "infra/hf-space/Dockerfile",
    "docs/runbooks/provider_limits_snapshot.md",
    "docs/runbooks/deployment.md",
    "docs/runbooks/backup_restore.md",
    "docs/runbooks/incident_response.md",
    "docs/runbooks/free_tier_operations.md",
    "migrations/README.md",
    "tools/verify_migrations.py",
    "tools/verify_storage.py",
    "tools/verify_backend.py",
    "tools/verify_tasks.py",
    "tools/verify_step1.py",
    "tools/verify_step2.py",
    "tools/verify_step2_pages.py",
    "tools/verify_step2_metadata.py",
    "tools/verify_step3_correction.py",
    "tools/verify_step4_similarity.py",
    "tools/verify_frontend_shell.py",
    "tools/verify_frontend_workflow.py",
    "tools/verify_manual_autorun.py",
    "tools/verify_ai_autorun.py",
    "tools/verify_infrastructure.py",
    "tests/visual/plan13_visual_matrix.json",
    "tests/visual/plan14_workflow_matrix.json",
    "tests/visual/release_visual_matrix.json",
    "tests/e2e/playwright_plan.json",
    "tests/golden/synthetic_manifest.json",
    "tests/security/security_matrix.json",
    "tests/fixtures/synthetic_legacy_manifest.json",
    "tools/migration/legacy_import_validator.py",
    "tools/verify_release.py",
    "docs/release/release_gate_config.json",
    "docs/release/security_acceptance.md",
    "docs/release/migration_acceptance.md",
    "docs/release/rollout_plan.md",
    "docs/release/rollback_plan.md",
    "docs/release/final_acceptance_report.md",
]

FORBIDDEN_IMPORT_PREFIXES = {
    "packages/domain/src": ("qcm_application", "qcm_infrastructure", "qcm_api", "qcm_worker"),
    "packages/application/src": ("qcm_infrastructure", "qcm_api", "qcm_worker"),
    "packages/shared/src": ("qcm_infrastructure", "qcm_api", "qcm_worker"),
}


def add_paths() -> None:
    for path in PYTHONPATHS:
        sys.path.insert(0, str(path))


def assert_required_paths() -> None:
    missing = [path for path in REQUIRED_PATHS if not (ROOT / path).exists()]
    if missing:
        raise AssertionError(f"Missing foundation paths: {missing}")


def imported_modules(source: Path) -> set[str]:
    tree = ast.parse(source.read_text(encoding="utf-8"))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


def assert_import_boundaries() -> None:
    for relative_root, forbidden_prefixes in FORBIDDEN_IMPORT_PREFIXES.items():
        for source in (ROOT / relative_root).rglob("*.py"):
            for module in imported_modules(source):
                if module.startswith(forbidden_prefixes):
                    raise AssertionError(f"{source.relative_to(ROOT)} imports forbidden module {module}")


def assert_contracts_import() -> None:
    from qcm_application.ownership import AuthorizationError, OwnedResource, require_owner
    from qcm_domain.auth import AppRole, ProfileStatus, UserContext
    from qcm_application.correction_modes import normalize_step3_mode
    from qcm_domain.enums import ProductStepKey
    from qcm_domain.documents import DIRECT_TEXT_THRESHOLD, classify_page_text
    from qcm_domain.steps.step2_contracts import COMBINED_STEP2_CYCLE_ORDER
    from qcm_domain.qcm import stable_qcm_uid
    from qcm_domain.templates import validate_qcm_template, default_qcm_template
    from qcm_domain.corrections import normalize_correction_mode, CorrectionMode
    from qcm_domain.reference_db import DEFAULT_MATCH_THRESHOLD, normalize_match_mode, SimilarityMatchMode
    from qcm_shared.artifacts.registry import ARTIFACT_REGISTRY
    from qcm_shared.ai_autorun_contracts import AI_AUTORUN_TASK_KIND
    from qcm_shared.autorun_contracts import MANUAL_AUTORUN_TASK_KIND
    from qcm_shared.auth_contracts import ModelPreference
    from qcm_shared.contracts import ArtifactType, TaskStatus
    from qcm_shared.step4_contracts import STEP4_TASK_KIND
    from qcm_observability.budget import DEFAULT_FREE_TIER_BUDGET

    assert ProductStepKey.STEP2_QCM_EXTRACTION.value == "step2_qcm_extraction"
    assert classify_page_text(1, "A" * (DIRECT_TEXT_THRESHOLD + 1)).direct_text_detected
    assert len(COMBINED_STEP2_CYCLE_ORDER) == 4
    assert stable_qcm_uid(1, 2, 3) == "1_2_3"
    assert validate_qcm_template(default_qcm_template()).valid
    assert normalize_correction_mode("vision_ai") == CorrectionMode.VISION
    assert DEFAULT_MATCH_THRESHOLD == 0.75
    assert normalize_match_mode("weighted") == SimilarityMatchMode.WEIGHTED
    assert STEP4_TASK_KIND == "step4_similarity_match"
    assert MANUAL_AUTORUN_TASK_KIND == "manual_autorun"
    assert AI_AUTORUN_TASK_KIND == "ai_autorun"
    assert TaskStatus.QUEUED.value == "queued"
    assert ArtifactType.STEP2_FINAL_JSON in ARTIFACT_REGISTRY
    assert ArtifactType.STEP4_SIMILARITY_JSON in ARTIFACT_REGISTRY
    assert normalize_step3_mode("vision_ai") == "vision"
    user = UserContext("u1", "user@example.com", AppRole.USER, ProfileStatus.ACTIVE, "corr")
    require_owner(user, OwnedResource("u1", "p1"))
    try:
        require_owner(user, OwnedResource("u2", "p2"))
    except AuthorizationError:
        pass
    else:
        raise AssertionError("cross-user ownership check did not fail")
    assert ModelPreference("openrouter", "model").provider == "openrouter"
    assert DEFAULT_FREE_TIER_BUDGET.max_source_file_bytes == 52_428_800


def main() -> int:
    add_paths()
    assert_required_paths()
    assert_import_boundaries()
    assert_contracts_import()
    print("Plan 18 release gates and prior boundaries verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
