import sys
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "domain" / "src"))
sys.path.insert(0, str(ROOT / "packages" / "shared" / "src"))
sys.path.insert(0, str(ROOT / "packages" / "application" / "src"))
sys.path.insert(0, str(ROOT / "packages" / "infrastructure" / "src"))
sys.path.insert(0, str(ROOT / "apps" / "worker" / "src"))

from qcm_application.ownership import (
    ApprovalRequiredError,
    AuthorizationError,
    OwnedResource,
    require_admin,
    require_owner,
)
from qcm_domain.auth import AppRole, ProfileStatus, UserContext
from qcm_infrastructure.auth.supabase_adapter import SupabaseAuthAdapter, SupabaseAuthSettings
from qcm_shared.auth_contracts import LoginRequest, ModelPreference, Profile, SessionTokens
from qcm_worker.auth_context import build_worker_context


class AuthTenancyTest(unittest.TestCase):
    def test_unapproved_profile_cannot_access_owned_resource(self) -> None:
        user = UserContext(
            user_id="u1",
            email="user@example.com",
            role=AppRole.USER,
            status=ProfileStatus.PENDING_APPROVAL,
            correlation_id="corr",
        )
        with self.assertRaises(ApprovalRequiredError):
            require_owner(user, OwnedResource(user_id="u1", project_id="p1"))

    def test_cross_user_project_is_denied(self) -> None:
        user = UserContext("u1", "user@example.com", AppRole.USER, ProfileStatus.ACTIVE, "corr")
        with self.assertRaises(AuthorizationError):
            require_owner(user, OwnedResource(user_id="u2", project_id="p2"))

    def test_admin_can_cross_user_scope_after_approval(self) -> None:
        admin = UserContext("admin", "admin@example.com", AppRole.ADMIN, ProfileStatus.ACTIVE, "corr")
        require_admin(admin)
        require_owner(admin, OwnedResource(user_id="u2", project_id="p2"))

    def test_shared_auth_contracts_validate_core_fields(self) -> None:
        with self.assertRaises(ValueError):
            LoginRequest(email="not-email", password="pw")
        with self.assertRaises(ValueError):
            SessionTokens(access_token="")
        with self.assertRaises(ValueError):
            Profile(user_id="", email="user@example.com", role=AppRole.USER, status=ProfileStatus.ACTIVE)
        self.assertEqual(ModelPreference("openrouter", "openai/gpt").provider, "openrouter")

    def test_worker_context_is_worker_scoped(self) -> None:
        context = build_worker_context(worker_id="worker-1", correlation_id="corr")
        self.assertEqual(context.role, AppRole.WORKER)

    def test_supabase_adapter_requires_url_and_service_key_for_service_context(self) -> None:
        with self.assertRaises(ValueError):
            SupabaseAuthSettings(supabase_url="")
        adapter = SupabaseAuthAdapter(SupabaseAuthSettings("https://example.supabase.co"))
        with self.assertRaises(ValueError):
            adapter.service_context(correlation_id="corr")


if __name__ == "__main__":
    unittest.main()
