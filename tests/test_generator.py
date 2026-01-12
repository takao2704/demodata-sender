import random
import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

from demodata_sender.generator import generate_payload

JST = ZoneInfo("Asia/Tokyo")


class TestGenerator(unittest.TestCase):
    def test_lunch_break_payload(self):
        current = datetime(2024, 5, 1, 12, 5, tzinfo=JST)
        payload = generate_payload(current=current, rng=random.Random(0))

        self.assertEqual(payload["intervalSec"], payload["intervalSec"])
        for line in payload["lines"]:
            for machine in line["machines"]:
                self.assertEqual(machine["status"], "IDLE")
                self.assertEqual(machine["reason"], "lunch_break")
                self.assertEqual(machine["runTimeSecDelta"], 0)
                self.assertEqual(machine["idleTimeSecDelta"], payload["intervalSec"])
                self.assertEqual(machine["stopTimeSecDelta"], 0)
                self.assertIsNone(machine["cycleTimeMs"])

    def test_off_shift_payload(self):
        current = datetime(2024, 5, 1, 2, 0, tzinfo=JST)
        payload = generate_payload(current=current, rng=random.Random(1))

        for line in payload["lines"]:
            for machine in line["machines"]:
                self.assertIn(machine["status"], {"RUN", "IDLE"})
                if machine["status"] == "RUN":
                    self.assertEqual(machine["reason"], "normal_run")
                else:
                    self.assertEqual(machine["reason"], "off_shift")
                total = (
                    machine["runTimeSecDelta"]
                    + machine["idleTimeSecDelta"]
                    + machine["stopTimeSecDelta"]
                )
                self.assertEqual(total, payload["intervalSec"])


if __name__ == "__main__":
    unittest.main()
