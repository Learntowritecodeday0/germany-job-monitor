"""Static integration checks for the client-side application tracker."""
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
HTML = (ROOT / "docs/index.html").read_text(encoding="utf-8")
APP = (ROOT / "docs/app.js").read_text(encoding="utf-8")
TRACKER = (ROOT / "docs/applications.js").read_text(encoding="utf-8")


class ApplicationTrackerIntegrationTest(unittest.TestCase):
    def test_tabs_and_fields_present(self):
        for item in ("tabVacancies", "tabApplications", "applicationsView",
                     "applicationRows", "applicationForm", "applicationPosted",
                     "applicationApplied", "applicationResponse", "applicationOutcome",
                     "applicationLocation", "applicationFollowUp", "applicationNotes"):
            self.assertIn('id="' + item + '"', HTML)
        self.assertIn('src="applications.js"', HTML)

    def test_shared_local_history_and_no_public_data_feed(self):
        self.assertIn("germany-job-monitor:applications:v1", APP)
        self.assertIn("germany-job-monitor:applications:v1", TRACKER)
        self.assertIn("localStorage.setItem(KEY", TRACKER)
        self.assertNotIn("fetch('/api", TRACKER)
        self.assertIn("window.JobApplicationsChanged", APP)

    def test_statuses_editing_and_import(self):
        for status in ("Applied", "Next step", "Interview", "Offer", "Rejected", "Withdrawn"):
            self.assertIn(status, TRACKER)
        for action in ("openEditor", "hideEditor", "refresh", "persist(records)"):
            self.assertIn(action, TRACKER)
        for field in ("posted_at", "response_at", "follow_up_at", "next_step", "notes", "location"):
            self.assertIn(field, APP)
        self.assertIn("const validDate=field", APP)


if __name__ == "__main__":
    unittest.main()
