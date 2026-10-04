import unittest
from datetime import datetime, timezone
from workflows.reminders import compute_reminder_times


class TestReminderComputation(unittest.TestCase):
    def test_compute_reminder_times_sample_deadline(self):
        sample_deadline = "2026-10-20T10:00:00Z"
        now_utc = datetime(2026, 10, 1, 0, 0, 0, tzinfo=timezone.utc)
        title = "AWS GenAI Hackathon"

        reminders = compute_reminder_times(title, sample_deadline, None, now_utc)

        self.assertEqual(len(reminders), 4)
        kinds = [r["kind"] for r in reminders]
        self.assertEqual(kinds, ["7d", "3d", "1d", "day_of"])

        self.assertEqual(reminders[0]["due_at_utc"], "2026-10-13T10:00:00Z")
        self.assertEqual(reminders[1]["due_at_utc"], "2026-10-17T10:00:00Z")
        self.assertEqual(reminders[2]["due_at_utc"], "2026-10-19T10:00:00Z")
        self.assertEqual(reminders[3]["due_at_utc"], "2026-10-20T10:00:00Z")
        self.assertEqual(reminders[1]["message"], "AWS GenAI Hackathon: deadline in 3 days")

    def test_compute_reminder_times_skips_past(self):
        sample_deadline = "2026-10-20T10:00:00Z"
        now_utc = datetime(2026, 10, 15, 0, 0, 0, tzinfo=timezone.utc)
        title = "AWS GenAI Hackathon"

        reminders = compute_reminder_times(title, sample_deadline, None, now_utc)

        self.assertEqual(len(reminders), 3)
        kinds = [r["kind"] for r in reminders]
        self.assertEqual(kinds, ["3d", "1d", "day_of"])

    def test_compute_reminder_times_uses_event_date_fallback(self):
        sample_event = "2026-10-25T14:00:00Z"
        now_utc = datetime(2026, 10, 1, 0, 0, 0, tzinfo=timezone.utc)
        title = "Cybersecurity Conference"

        reminders = compute_reminder_times(title, None, sample_event, now_utc)

        self.assertEqual(len(reminders), 4)
        kinds = [r["kind"] for r in reminders]
        self.assertEqual(kinds, ["7d", "3d", "1d", "day_of"])
        self.assertEqual(reminders[0]["due_at_utc"], "2026-10-18T14:00:00Z")
        self.assertEqual(reminders[1]["message"], "Cybersecurity Conference: event in 3 days")


if __name__ == "__main__":
    unittest.main()
