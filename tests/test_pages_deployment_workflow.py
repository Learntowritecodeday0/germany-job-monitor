"""Guard against immediate Pages deployment before the artifact upload is visible.

Checking the separation between jobs avoids coupling to GitHub's eventually
consistent artifact lookup. This is a structural test, not live deployment.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = (ROOT / ".github" / "workflows" / "monitor.yml").read_text(encoding="utf-8")


class PagesDeployWorkflowTests(unittest.TestCase):
    def test_upload_and_deploy_are_separate_dependent_jobs(self):
        build, deploy = WORKFLOW.split("\n  deploy-pages:\n", 1)
        self.assertIn("\n  check-and-publish:\n", build)
        self.assertIn("uses: actions/upload-pages-artifact@v3", build)
        self.assertNotIn("uses: actions/deploy-pages@", build)
        self.assertIn("needs: check-and-publish", deploy)
        self.assertIn("uses: actions/deploy-pages@v4", deploy)

    def test_deploy_has_pages_environment_and_token_permissions(self):
        deploy = WORKFLOW.split("\n  deploy-pages:\n", 1)[1]
        self.assertIn("name: github-pages", deploy)
        for permission in ("pages: write", "id-token: write", "actions: read"):
            self.assertIn(permission, deploy)
        self.assertIn("id: deployment", deploy)
        self.assertIn("steps.deployment.outputs.page_url", deploy)

    def test_code_push_scans_without_recursive_snapshot_build(self):
        self.assertIn("  push:", WORKFLOW)
        self.assertIn("    branches: [main]", WORKFLOW)
        self.assertIn('      - "data/state.json"', WORKFLOW)
        self.assertIn('      - "docs/jobs.json"', WORKFLOW)
        self.assertIn("  schedule:", WORKFLOW)
        self.assertIn("  workflow_dispatch:", WORKFLOW)

    def test_build_still_uploads_after_generating_snapshot(self):
        build = WORKFLOW.split("\n  deploy-pages:\n", 1)[0]
        self.assertLess(build.index("run: python monitor.py"),
                        build.index("git add data/state.json docs/jobs.json"))
        self.assertLess(build.index("git add data/state.json docs/jobs.json"),
                        build.index("uses: actions/upload-pages-artifact@v3"))


if __name__ == "__main__":
    unittest.main()
