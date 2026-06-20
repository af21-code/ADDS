# ADDS Streamlit Dashboard

This folder contains the Phase 7A Streamlit visualization prototype for ADDS.
Use the commands below from a terminal to install the dashboard dependencies and
run the local app.

## 1. Open The Project Folder

```bash
cd "/Users/angelo/Documents/ADDS: Adaptive Drivetrain Decoupling System"
```

## 2. Install Dashboard Dependencies

```bash
/Users/angelo/venvs/adds-venv/bin/python -m pip install -r requirements.txt
```

## 3. Run The Dashboard

```bash
/Users/angelo/venvs/adds-venv/bin/python -m streamlit run app/streamlit_app.py --server.address localhost
```

After the command starts, open the local URL printed by Streamlit. It is usually:

```text
http://localhost:8501
```

## 4. Run The Test Suite

```bash
/Users/angelo/venvs/adds-venv/bin/python -B -m unittest discover -s tests -v
```

## 5. Optional: Run The Dashboard On A Fixed Port

Use this command if you want the dashboard to always open on port `8511`:

```bash
/Users/angelo/venvs/adds-venv/bin/python -m streamlit run app/streamlit_app.py --server.address localhost --server.port 8511
```

Then open:

```text
http://localhost:8511
```

## Notes

- Keep the terminal window open while using the dashboard.
- Stop the dashboard with `Ctrl+C` in the terminal.
- The dashboard is a research visualization prototype, not a validated
  real-vehicle performance tool.
