"""Malformed optimizer plans must never bypass the independent verifier."""
import unittest

from engine.scenario import scenario
from engine.verification import verify_plan


class MalformedPlanContractTests(unittest.TestCase):
    def setUp(self):
        self.data = scenario()

    def assert_rejected(self, plan):
        result = verify_plan(self.data, plan)
        self.assertIs(result["passed"], False)
        self.assertTrue(result["violations"])
        self.assertIsNone(result["summary"]["critical_load_preserved"])

    def test_rejects_non_mapping_and_absent_content(self):
        for plan in (None, [], 7, "not a plan", {}):
            with self.subTest(plan=repr(plan)):
                self.assert_rejected(plan)

    def test_rejects_invalid_slot_rows(self):
        for slots in ([None], ["not an hour"], [7], [{"grid_kw": "bad"}]):
            with self.subTest(slots=repr(slots)):
                self.assert_rejected({"slots": slots, "jobs": [], "metrics": {}})

    def test_rejects_missing_required_job_fields(self):
        self.assert_rejected({
            "slots": [], "jobs": [{"id": "J1"}], "metrics": {},
        })

    def test_rejects_fabricated_metric_types(self):
        plan = {
            "slots": [], "jobs": [],
            "metrics": {"energy_cost_inr": "not a number"},
        }
        self.assert_rejected(plan)

    def test_invalid_document_does_not_reflect_sensitive_payload(self):
        secret = "sensitive-diagnostic-token"
        result = verify_plan(self.data, {"slots": [secret], "jobs": [], "metrics": {}})
        self.assertFalse(result["passed"])
        self.assertNotIn(secret, str(result))


if __name__ == "__main__":
    unittest.main()
