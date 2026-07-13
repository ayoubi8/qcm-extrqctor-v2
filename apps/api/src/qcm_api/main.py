"""FastAPI entry point with a dependency-light fallback for foundation verification."""

import os

try:
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
except ModuleNotFoundError:  # pragma: no cover - local foundation verification path
    FastAPI = None


def _cors_origins() -> list[str]:
    raw = os.getenv("QCM_CORS_ALLOW_ORIGINS", "*")
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


def _build_auth_provider():
    supabase_url = os.getenv("SUPABASE_URL", "").strip()
    anon_key = os.getenv("SUPABASE_ANON_KEY", os.getenv("VITE_SUPABASE_ANON_KEY", "")).strip()
    service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    if not supabase_url:
        return None

    from qcm_infrastructure.auth import SupabaseAuthAdapter, SupabaseAuthSettings

    return SupabaseAuthAdapter(
        SupabaseAuthSettings(
            supabase_url=supabase_url,
            anon_key=anon_key or None,
            service_role_key=service_role_key or None,
        )
    )


def create_app():
    if FastAPI is None:
        return {"name": "qcm-api", "status": "dependencies-not-installed"}

    from qcm_api.routes.artifacts import create_artifacts_router
    from qcm_api.routes.auth import create_auth_router
    from qcm_api.routes.autorun import create_autorun_router
    from qcm_api.routes.ai_autorun import create_ai_autorun_router
    from qcm_api.routes.config import create_config_router
    from qcm_api.routes.health import create_health_router
    from qcm_api.routes.projects import create_projects_router
    from qcm_api.routes.reference_dbs import create_reference_dbs_router
    from qcm_api.routes.step1 import create_step1_router
    from qcm_api.routes.step2 import create_step2_router
    from qcm_api.routes.step3_correction import create_step3_correction_router
    from qcm_api.routes.step4_similarity import create_step4_similarity_router
    from qcm_api.routes.tasks import create_tasks_router
    from qcm_api.routes.terminal import create_terminal_router

    app = FastAPI(title="QCM Re-Engineered API", version="0.1.0")
    origins = _cors_origins()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials="*" not in origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    auth_provider = _build_auth_provider()
    health_router = create_health_router()
    if health_router is not None:
        app.include_router(health_router)
    auth_router = create_auth_router(auth_provider)
    if auth_router is not None:
        app.include_router(auth_router)
    ai_autorun_router = create_ai_autorun_router()
    if ai_autorun_router is not None:
        app.include_router(ai_autorun_router)
    autorun_router = create_autorun_router()
    if autorun_router is not None:
        app.include_router(autorun_router)
    artifacts_router = create_artifacts_router()
    if artifacts_router is not None:
        app.include_router(artifacts_router)
    projects_router = create_projects_router()
    if projects_router is not None:
        app.include_router(projects_router)
    config_router = create_config_router()
    if config_router is not None:
        app.include_router(config_router)
    tasks_router = create_tasks_router()
    if tasks_router is not None:
        app.include_router(tasks_router)
    terminal_router = create_terminal_router()
    if terminal_router is not None:
        app.include_router(terminal_router)
    step1_router = create_step1_router()
    if step1_router is not None:
        app.include_router(step1_router)
    step2_router = create_step2_router()
    if step2_router is not None:
        app.include_router(step2_router)
    step3_correction_router = create_step3_correction_router()
    if step3_correction_router is not None:
        app.include_router(step3_correction_router)
    step4_similarity_router = create_step4_similarity_router()
    if step4_similarity_router is not None:
        app.include_router(step4_similarity_router)
    reference_dbs_router = create_reference_dbs_router()
    if reference_dbs_router is not None:
        app.include_router(reference_dbs_router)

    return app


app = create_app()
