import unittest

from adds_sim import ConstantProfile, LongitudinalSimulator, Scenario, ScriptedModeController, default_simulation_config


def modes_seen(result):
    modes = []
    for record in result.records:
        mode = record["coupling_mode"]
        if not modes or modes[-1] != mode:
            modes.append(mode)
    return modes


class Phase2StateMachineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = default_simulation_config()
        self.simulator = LongitudinalSimulator(self.config)

    def test_valid_decoupling_sequence(self) -> None:
        scenario = Scenario(
            scenario_id="A2.1_valid_decoupling",
            initial_speed=25.0,
            initial_gear=5,
            time_limit=1.0,
            target_speed_profile=ConstantProfile(0.0),
            grade_profile=ConstantProfile(0.0),
            adds_enabled=True,
        )
        controller = ScriptedModeController(
            gear=5,
            schedule=((0.0, "DECOUPLING", None, 0.0, False),),
        )

        result = self.simulator.run(scenario, controller)
        modes = modes_seen(result)

        self.assertEqual(modes[:2], ["DECOUPLING", "DECOUPLED"])
        self.assertNotIn("REV_MATCHING", modes)
        self.assertGreaterEqual(result.records[-1]["transition_count"], 2)

    def test_brake_demand_blocks_decoupling(self) -> None:
        scenario = Scenario(
            scenario_id="A2.2_brake_blocks_decoupling",
            initial_speed=25.0,
            initial_gear=5,
            time_limit=0.2,
            target_speed_profile=ConstantProfile(0.0),
            grade_profile=ConstantProfile(0.0),
            adds_enabled=True,
        )
        controller = ScriptedModeController(
            gear=5,
            schedule=((0.0, "DECOUPLING", None, self.config.vehicle.max_brake_force * 0.2, False),),
        )

        result = self.simulator.run(scenario, controller)

        self.assertTrue(all(record["coupling_mode"] == "CONNECTED" for record in result.records))
        self.assertTrue(any(record["safety_override"] for record in result.records))
        self.assertEqual(result.records[0]["safety_override_reason"], "BRAKE_DEMAND_BLOCKS_DECOUPLING")

    def test_rev_matched_reengagement_sequence(self) -> None:
        scenario = Scenario(
            scenario_id="A2.3_rev_matched_reengagement",
            initial_speed=27.0,
            initial_gear=5,
            time_limit=3.0,
            target_speed_profile=ConstantProfile(27.0),
            grade_profile=ConstantProfile(0.0),
            adds_enabled=True,
        )
        controller = ScriptedModeController(
            gear=5,
            schedule=(
                (0.0, "DECOUPLING", None, 0.0, False),
                (0.8, "CONNECTED", 80.0, 0.0, False),
            ),
        )

        result = self.simulator.run(scenario, controller)
        modes = modes_seen(result)

        self.assertIn("DECOUPLED", modes)
        self.assertIn("REV_MATCHING", modes)
        self.assertIn("REENGAGING", modes)
        self.assertEqual(modes[-1], "CONNECTED")
        self.assertLessEqual(result.records[-1]["coupling_slip_energy"], self.config.coupling.max_slip_energy_per_event)
        reengaging_records = [record for record in result.records if record["coupling_mode"] == "REENGAGING"]
        self.assertTrue(reengaging_records)
        self.assertTrue(
            all(
                abs(record["coupling_slip_speed"]) <= self.config.coupling.reengagement_slip_limit
                for record in reengaging_records
            )
        )

    def test_fault_during_transition_enters_fallback(self) -> None:
        scenario = Scenario(
            scenario_id="A2.4_fault_fallback",
            initial_speed=25.0,
            initial_gear=5,
            time_limit=0.6,
            target_speed_profile=ConstantProfile(0.0),
            grade_profile=ConstantProfile(0.0),
            adds_enabled=True,
        )
        controller = ScriptedModeController(
            gear=5,
            schedule=(
                (0.0, "DECOUPLING", None, 0.0, False),
                (0.12, "DECOUPLING", None, 0.0, True),
            ),
        )

        result = self.simulator.run(scenario, controller)

        self.assertTrue(any(record["coupling_mode"] == "FAULT_SAFE" for record in result.records))
        self.assertTrue(any(record["fallback_active"] for record in result.records))
        self.assertTrue(any(record["safety_override_reason"] == "FORCED_FAULT" for record in result.records))


if __name__ == "__main__":
    unittest.main()
