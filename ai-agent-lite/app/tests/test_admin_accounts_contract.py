"""Contract checks for admin account management route source."""

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ADMIN_ACCOUNTS = ROOT / "routers" / "admin_accounts.py"
AUTH_HELPERS = ROOT / "utils" / "auth_helpers.py"
AUTH_ROUTES = ROOT / "routers" / "auth.py"


class AdminAccountContractTest(unittest.TestCase):
    def test_admin_accounts_exposes_status_and_password_quick_routes(self):
        source = ADMIN_ACCOUNTS.read_text()

        self.assertIn('@router.patch("/{username}/status")', source)
        self.assertIn('@router.patch("/{username}/password")', source)
        self.assertIn("is_disabled", source)
        self.assertIn("Cannot disable current login account", source)
        self.assertIn("Cannot disable last enabled admin account", source)

    def test_disabled_accounts_are_rejected_by_auth_boundaries(self):
        helpers_source = AUTH_HELPERS.read_text()
        auth_source = AUTH_ROUTES.read_text()

        self.assertIn("COALESCE(is_disabled,false)", helpers_source)
        self.assertIn("Account is disabled", helpers_source)
        self.assertIn("COALESCE(is_disabled,false)", auth_source)
        self.assertIn("Account is disabled", auth_source)


if __name__ == "__main__":
    unittest.main()
