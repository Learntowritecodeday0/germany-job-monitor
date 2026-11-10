import unittest
import sys
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import notify


def a_job(key, *, baseline=False, band="Review first", hidden=False, active=True):
    return {
        "key": key, "title": "Nanoparticle Scientist", "company": "Example Ltd",
        "location": "Munich", "url": f"https://example.com/{key}",
        "first_detected": "2026-11-10T15:00:00+00:00", "at_startup": baseline,
        "match_band": band, "hide_by_default": hidden, "active": active,
        "matched_topics": ["Nanoparticles / silica"],
    }


class AlertTests(unittest.TestCase):
    def test_initial_vacancies_not_alerted(self):
        self.assertEqual(notify.candidates({"jobs": {"old": a_job("old", baseline=True)}}), [])

    def test_only_new_relevant_and_eligible_preferences(self):
        state = {"jobs": {
            "new": a_job("new"),
            "low": a_job("low", band="Low"),
            "vocational": a_job("vocational", hidden=True),
            "closed": a_job("closed", active=False),
        }}
        self.assertEqual([j["key"] for j in notify.candidates(state)], ["new"])

    def test_mail_activation_cutoff_excludes_old_jobs(self):
        state = {"jobs": {"new": a_job("new")}, "alerts_started_at": "2026-11-11T00:00:00+00:00"}
        self.assertEqual(notify.candidates(state), [])

    def test_alerts_not_repeated_after_sent(self):
        state = {"jobs": {"new": a_job("new")}, "alerts_sent": {"new": "2026-11-10T16:00:00+00:00"}}
        self.assertEqual(notify.candidates(state), [])

    def test_message_contains_link_and_no_password(self):
        body = notify.email_content([a_job("new")]).get_content()
        self.assertIn("https://example.com/new", body)
        self.assertIn("actual worksite", body)

    def test_missing_configuration_skips_notifies(self):
        with patch.dict("notify.os.environ", {"SMTP_USER": "", "SMTP_PASSWORD": "", "ALERT_TO": "", "SEND_TEST_EMAIL": ""}):
            self.assertEqual(notify.main(), 0)

    def test_successful_send_records_job_without_private_email(self):
        import json
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as tempdir:
            statefile = Path(tempdir) / "state.json"
            statefile.write_text(json.dumps({"jobs": {"new": a_job("new")}, "sources": {}, "alerts_started_at": "2026-11-09T00:00:00+00:00"}), encoding="utf-8")
            creds = {"SMTP_USER": "sender@example.com", "SMTP_PASSWORD": "private",
                     "ALERT_TO": "inbox@example.com", "SEND_TEST_EMAIL": ""}
            with patch.object(notify, "STATE", statefile), patch.object(notify, "smtp_send") as sender, patch.dict("notify.os.environ", creds):
                self.assertEqual(notify.main(), 0)
                self.assertEqual(sender.call_count, 1)
                self.assertEqual(notify.main(), 0)
                self.assertEqual(sender.call_count, 1)
            saved = statefile.read_text(encoding="utf-8")
            self.assertIn("alerts_sent", saved)
            self.assertNotIn("private", saved)
            self.assertNotIn("inbox@example.com", saved)

    def test_missing_configuration_fails_manual_test(self):
        with patch.dict("notify.os.environ", {"SMTP_USER": "", "SMTP_PASSWORD": "", "ALERT_TO": "", "SEND_TEST_EMAIL": "true"}):
            self.assertEqual(notify.main(), 1)


if __name__ == "__main__":
    unittest.main()
