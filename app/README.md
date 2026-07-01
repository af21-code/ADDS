# ADDS Streamlit Dashboard

This folder contains the Phase 7A Streamlit visualization prototype for ADDS.
Use the commands below from a terminal to install the dashboard dependencies and
run the local app. The commands are written for a terminal already opened inside
this `app` folder.

## 1. Confirm You Are In This Folder

```bash
pwd
```

## 2. Install Dashboard Dependencies

```bash
/Users/angelo/venvs/adds-venv/bin/python -m pip install -r ../requirements.txt
```

## 3. Run The Dashboard

```bash
/Users/angelo/venvs/adds-venv/bin/python -m streamlit run streamlit_app.py --server.address localhost
```

After the command starts, open the local URL printed by Streamlit. It is usually:

```text
http://localhost:8501
```

## 4. What You Should See

The dashboard opens on the `train_highway_lift_off` scenario because it is the
clearest first demonstration. You should see:

- A sidebar with a scenario selector and an ADDS controller selector.
- Three ADDS controller choices: `Rule-based ADDS`, `Offline-optimized ADDS`,
  and `Learned ADDS`.
- Six tabs: project overview, scenario comparison, catalog summary, controller
  portfolio, robustness, and downloads.
- A project overview explaining the conventional baseline, adaptive vehicle,
  fair comparison method, and operating modes.
- Metric cards showing fuel delta, relative fuel change, RMS speed-error delta,
  ADDS transitions, safety overrides, and total fuel values.
- Decision insight cards explaining whether the selected simulation looks
  beneficial, neutral, or cautionary for ADDS.
- An ADDS event-analysis section with time spent in each coupling mode and a
  transition table for decoupling, rev-matching, and re-engagement events.
- A speed chart where Conventional, ADDS, and the target speed are shown
  together.
- A fuel chart where ADDS should use less fuel in the highway lift-off scenario.
- Engine-speed charts showing how engine speed changes relative to synchronous
  drivetrain speed.
- An ADDS coupling-mode timeline showing when the system is connected,
  decoupling, decoupled, rev-matching, and re-engaging.
- A coupling slip-energy chart for re-engagement diagnostics.
- A catalog summary table and fuel-change bar chart across all scenarios.
- A controller portfolio view comparing rule-based, offline-optimized, and
  learned ADDS across the full scenario catalog.
- A robustness view that repeats the selected scenario under payload, drag,
  rolling-resistance, grip, and grade perturbations.
- Robustness charts showing fuel sensitivity and the fuel-versus-speed-tracking
  acceptance region.
- Download buttons for the current trajectory CSV, current summary JSON, full
  catalog summary, controller portfolio, and selected sensitivity CSV files.

If you choose `train_constant_speed_cruise`, the curves can look almost
identical. That is expected: the scenario has no useful coasting opportunity.
If the dashboard shows a warning saying there are no ADDS mode transitions, the
adaptive drivetrain stayed connected for that run.

Use `validation_lower_speed_coast` and `test_high_speed_coast` to inspect
generalization outside the coast profile used for training. Both scenarios are
excluded from the train split.

Use `Offline-optimized ADDS` on `test_high_speed_coast` to inspect the promoted
candidate `C03` from the policy-search audit. It should improve simulated fuel
use more than the initial rule-based baseline while keeping five ADDS mode
transitions and zero safety overrides.

## 5. Run The Test Suite

```bash
cd ..
/Users/angelo/venvs/adds-venv/bin/python -B -m unittest discover -s tests -v
```

## 6. Optional: Run The Dashboard On A Fixed Port

Use this command if you want the dashboard to always open on port `8511`:

```bash
/Users/angelo/venvs/adds-venv/bin/python -m streamlit run streamlit_app.py --server.address localhost --server.port 8511
```

Then open:

```text
http://localhost:8511
```

## Notes

- Keep the terminal window open while using the dashboard.
- Stop the dashboard with `Ctrl+C` in the terminal.
- If you are in the project root instead, use `requirements.txt` and
  `app/streamlit_app.py` instead of `../requirements.txt` and
  `streamlit_app.py`.
- The dashboard is a research visualization prototype, not a validated
  real-vehicle performance tool.
