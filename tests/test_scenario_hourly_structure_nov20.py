"""The synthetic scenario timeline is internally consistent for every preset."""
import unittest

from engine.scenario import scenario


PRESETS = (
    "grid-stress", "normal", "cloudy", "high-tariff",
    "production-surge", "battery-limited", "emergency-outage",
)


class ScenarioHourlyStructureTests(unittest.TestCase):
    def test_all_presets_keep_aligned_twelve_hour_timeseries(self):
        expected_hours = [f"{hour:02d}:00" for hour in range(8, 20)]
        for preset in PRESETS:
            with self.subTest(preset=preset):
                result = scenario(preset)
                self.assertEqual(result["hours"], expected_hours)
                for key in (
                    "base_kw", "solar_kw", "tariff_inr_per_kwh",
                    "grid_limit_kw", "carbon_kg_per_kwh",
                ):
                    with self.subTest(preset=preset, series=key):
                        self.assertEqual(len(result[key]), len(expected_hours))

    def test_jobs_have_unique_ids_and_schedulable_windows(self):
        for preset in PRESETS:
            with self.subTest(preset=preset):
                case = scenario(preset)
                ids = [job["id"] for job in case["jobs"]]
                self.assertEqual(len(ids), len(set(ids)))
                for job in case["jobs"]:
                    with self.subTest(preset=preset, job=job["id"]):
                        self.assertGreater(job["power_kw"], 0)
                        self.assertGreater(job["duration_h"], 0)
                        self.assertGreaterEqual(job["earliest"], 0)
                        self.assertLessEqual(
                            job["earliest"] + job["duration_h"],
                            job["deadline"],
                        )
                        self.assertLessEqual(job["deadline"], len(case["hours"]))


if __name__ == "__main__":
    unittest.main()
