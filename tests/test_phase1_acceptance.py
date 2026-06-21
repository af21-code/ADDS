import unittest

from adds_sim import (
    CoastController,
    ConstantEngineTorqueController,
    ConstantProfile,
    LongitudinalSimulator,
    Scenario,
    SpeedTrackingController,
    default_simulation_config,
    summarize_run,
)


class Phase1AcceptanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = default_simulation_config()
        self.simulator = LongitudinalSimulator(self.config)

    def test_static_force_balance_has_near_zero_acceleration(self) -> None:
        speed = 25.0
        gear = 5
        hold_force = self.simulator.force_to_hold_speed(speed, 0.0)
        total_ratio = self.config.transmission.total_ratio(gear)
        engine_torque = hold_force * self.config.vehicle.wheel_radius / (
            total_ratio * self.config.transmission.efficiency_motoring
        )
        scenario = Scenario(
            scenario_id="A1.1_static_force_balance",
            initial_speed=speed,
            initial_gear=gear,
            time_limit=0.2,
            target_speed_profile=ConstantProfile(speed),
            grade_profile=ConstantProfile(0.0),
            drivetrain_connected=True,
        )

        result = self.simulator.run(scenario, ConstantEngineTorqueController(engine_torque=engine_torque, gear=gear))

        self.assertLess(abs(result.records[0]["vehicle_acceleration"]), 1e-9)

    def test_connected_coast_down_decelerates_faster_than_decoupled(self) -> None:
        connected = Scenario(
            scenario_id="A1.2_connected_coast",
            initial_speed=30.0,
            initial_gear=5,
            time_limit=8.0,
            target_speed_profile=ConstantProfile(0.0),
            grade_profile=ConstantProfile(0.0),
            drivetrain_connected=True,
        )
        decoupled = Scenario(
            scenario_id="A1.2_decoupled_coast",
            initial_speed=30.0,
            initial_gear=5,
            time_limit=8.0,
            target_speed_profile=ConstantProfile(0.0),
            grade_profile=ConstantProfile(0.0),
            drivetrain_connected=False,
        )

        connected_result = self.simulator.run(connected, CoastController(gear=5))
        decoupled_result = self.simulator.run(decoupled, CoastController(gear=5))

        connected_speeds = [record["vehicle_speed"] for record in connected_result.records]
        decoupled_speeds = [record["vehicle_speed"] for record in decoupled_result.records]
        self.assertTrue(all(a >= b for a, b in zip(connected_speeds, connected_speeds[1:])))
        self.assertTrue(all(a >= b for a, b in zip(decoupled_speeds, decoupled_speeds[1:])))
        self.assertLess(connected_result.final_state.speed, decoupled_result.final_state.speed)
        self.assertGreater(decoupled_result.final_state.fuel_used, 0.0)

    def test_grade_direction_changes_required_holding_force(self) -> None:
        speed = 20.0
        uphill_force = self.simulator.force_to_hold_speed(speed, 0.04)
        level_force = self.simulator.force_to_hold_speed(speed, 0.0)
        downhill_force = self.simulator.force_to_hold_speed(speed, -0.04)

        self.assertGreater(uphill_force, level_force)
        self.assertLess(downhill_force, level_force)

    def test_gear_kinematics_and_invalid_gear(self) -> None:
        speed = 22.0
        wheel_speed = speed / self.config.vehicle.wheel_radius
        for gear, ratio in enumerate(self.config.transmission.gear_ratios, start=1):
            expected = wheel_speed * ratio * self.config.transmission.final_drive_ratio
            self.assertAlmostEqual(self.simulator.synchronous_engine_speed(speed, gear), expected)

        with self.assertRaises(ValueError):
            self.simulator.synchronous_engine_speed(speed, 99)

    def test_energy_accounting_residual_stays_bounded(self) -> None:
        scenario = Scenario(
            scenario_id="A1.5_energy_accounting",
            initial_speed=25.0,
            initial_gear=5,
            time_limit=20.0,
            target_speed_profile=ConstantProfile(25.0),
            grade_profile=ConstantProfile(0.0),
            drivetrain_connected=True,
        )

        result = self.simulator.run(scenario, SpeedTrackingController(gear=5))
        summary = summarize_run(result)

        self.assertFalse(summary["numerical_failure"])
        self.assertLess(summary["energy_balance_residual_ratio"], self.config.solver.energy_residual_tolerance)
        self.assertGreaterEqual(summary["aero_energy"], 0.0)
        self.assertGreaterEqual(summary["rolling_resistance_energy"], 0.0)
        self.assertGreaterEqual(summary["brake_energy"], 0.0)


if __name__ == "__main__":
    unittest.main()
