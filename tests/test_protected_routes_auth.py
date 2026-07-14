"""Integration test: protected routes require a verified Supabase JWT and derive user_id from it.

Skipped when FastAPI/httpx are not installed (local contract-only verification).
On the VPS (deps installed) it exercises the real route wiring against an in-process
TestClient with a fake auth provider, asserting:
  - missing/invalid token -> 401
  - pending-approval profile -> 403
  - verified active user -> protected calls succeed and are user-scoped
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
for sub in ("domain", "shared", "application", "infrastructure", "observability", "api"):
    sys.path.insert(0, str(ROOT / "packages" / sub / "src"))
for sub in ("api",):
    sys.path.insert(0, str(ROOT / "apps" / sub / "src"))

try:
    from fastapi.testclient import TestClient
except ModuleNotFoundError:
    TestClient = None

if TestClient is not None:
    from qcm_api.main import create_app
    from qcm_domain.auth import AppRole, ProfileStatus, UserContext

    class _FakeAuthProvider:
        def verify_access_token(self, token: str, *, correlation_id: str) -> UserContext:
            if token == "active":
                return UserContext("user-123", "active@example.com", AppRole.USER, ProfileStatus.ACTIVE, correlation_id)
            if token == "pending":
                return UserContext("user-pending", "pending@example.com", AppRole.USER, ProfileStatus.PENDING_APPROVAL, correlation_id)
            raise ValueError("invalid token")


@unittest.skipUnless(TestClient is not None, "FastAPI/httpx not installed")
@unittest.skipIf(
    __import__("os").getenv("SUPABASE_URL"),
    "in-memory auth-wiring contract test; persistence is covered live by test_repositories_live",
)
class ProtectedRoutesAuthTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with patch("qcm_api.main._build_auth_provider", return_value=_FakeAuthProvider()):
            cls.app = create_app()
        cls.client = TestClient(cls.app)

    def test_missing_token_is_unauthorized(self):
        response = self.client.get("/projects/any/snapshot")
        self.assertEqual(response.status_code, 401)

    def test_invalid_token_is_unauthorized(self):
        response = self.client.get(
            "/projects/any/snapshot",
            headers={"Authorization": "Bearer bad"},
        )
        self.assertEqual(response.status_code, 401)

    def test_pending_approval_is_forbidden(self):
        response = self.client.get(
            "/projects/any/snapshot",
            headers={"Authorization": "Bearer pending"},
        )
        self.assertEqual(response.status_code, 403)

    def test_active_user_creates_project_and_reads_snapshot(self):
        headers = {"Authorization": "Bearer active"}
        create = self.client.post(
            "/projects",
            json={"name": "Phase A project", "idempotency_key": "idem-1"},
            headers=headers,
        )
        self.assertEqual(create.status_code, 200)
        project = create.json()
        self.assertEqual(project["user_id"], "user-123")

        snapshot = self.client.get(f"/projects/{project['project_id']}/snapshot", headers=headers)
        self.assertEqual(snapshot.status_code, 200)
        self.assertEqual(snapshot.json()["project"]["user_id"], "user-123")

    def test_active_user_unknown_project_snapshot_is_404(self):
        response = self.client.get("/projects/does-not-exist/snapshot", headers={"Authorization": "Bearer active"})
        self.assertEqual(response.status_code, 404)

    def test_client_supplied_user_id_is_ignored(self):
        # Even if the body claims a different user_id, the server must use the token identity.
        create = self.client.post(
            "/projects",
            json={"name": "Spoof attempt", "user_id": "attacker", "idempotency_key": "idem-spoof"},
            headers={"Authorization": "Bearer active"},
        )
        self.assertEqual(create.status_code, 200)
        self.assertEqual(create.json()["user_id"], "user-123")


if __name__ == "__main__":
    unittest.main()