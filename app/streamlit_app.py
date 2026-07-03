"""Streamlit prototype for visual ADDS simulation comparisons."""

from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from adds_sim.controller_portfolio import (
    build_controller_portfolio_report,
    build_controller_robustness_portfolio_report,
)
from adds_sim.track_lap import run_track_lap_comparison
from adds_sim.visualization import (
    MODE_ORDER,
    available_dashboard_scenarios,
    build_dashboard_catalog_summary,
    build_dashboard_comparison,
    build_dashboard_sensitivity,
    records_for_dashboard,
)


st.set_page_config(
    page_title="ADDS Visualization Prototype",
    page_icon="ADDS",
    layout="wide",
)


@st.cache_data(show_spinner=False)
def _scenario_options():
    return available_dashboard_scenarios()


@st.cache_data(show_spinner=True)
def _comparison(scenario_id: str, controller_kind: str):
    return build_dashboard_comparison(scenario_id, controller_kind)


@st.cache_data(show_spinner=True)
def _catalog_summary(controller_kind: str):
    return build_dashboard_catalog_summary(controller_kind)


@st.cache_data(show_spinner=True)
def _controller_portfolio():
    return build_controller_portfolio_report()


@st.cache_data(show_spinner=True)
def _controller_robustness_portfolio():
    return build_controller_robustness_portfolio_report()


@st.cache_data(show_spinner=True)
def _sensitivity_summary(scenario_id: str, controller_kind: str):
    return build_dashboard_sensitivity(scenario_id, controller_kind)


@st.cache_data(show_spinner=True)
def _track_lap_report(controller_kind: str):
    return run_track_lap_comparison(controller_kind)


def _records_frame(comparison) -> pd.DataFrame:
    return pd.DataFrame((*comparison.conventional_records, *comparison.adds_records))


def _track_lap_records_frame(report) -> pd.DataFrame:
    conventional = records_for_dashboard(report.comparison.conventional_result, "Conventional")
    adds = records_for_dashboard(report.comparison.adds_result, "ADDS")
    return pd.DataFrame((*conventional, *adds))


def _track_lap_stats_frame(report) -> pd.DataFrame:
    return pd.DataFrame(asdict(stat) for stat in report.stats)


def _catalog_frame(controller_kind: str) -> pd.DataFrame:
    return pd.DataFrame(asdict(row) for row in _catalog_summary(controller_kind))


def _controller_portfolio_frame() -> pd.DataFrame:
    report = _controller_portfolio()
    return pd.DataFrame(asdict(row) for row in report.rows)


def _controller_portfolio_insights():
    return _controller_portfolio().insights


def _controller_robustness_portfolio_frame() -> pd.DataFrame:
    report = _controller_robustness_portfolio()
    return pd.DataFrame(asdict(row) for row in report.rows)


def _controller_robustness_aggregate_frame() -> pd.DataFrame:
    report = _controller_robustness_portfolio()
    return pd.DataFrame(asdict(aggregate) for aggregate in report.aggregates)


def _controller_robustness_failure_frame() -> pd.DataFrame:
    report = _controller_robustness_portfolio()
    return pd.DataFrame(asdict(summary) for summary in report.failure_summaries)


def _controller_robustness_rejection_frame() -> pd.DataFrame:
    report = _controller_robustness_portfolio()
    return pd.DataFrame(asdict(item) for item in report.rejection_breakdown)


def _controller_robustness_recommendation_frame() -> pd.DataFrame:
    report = _controller_robustness_portfolio()
    return pd.DataFrame(asdict(item) for item in report.recommendations)


def _controller_robustness_insights():
    return _controller_robustness_portfolio().insights


def _mode_duration_frame(comparison) -> pd.DataFrame:
    return pd.DataFrame(asdict(row) for row in comparison.mode_durations)


def _mode_transition_frame(comparison) -> pd.DataFrame:
    return pd.DataFrame(asdict(row) for row in comparison.mode_transitions)


def _sensitivity_frame(sensitivity) -> pd.DataFrame:
    return pd.DataFrame(asdict(row) for row in sensitivity.rows)


def _metric_value(card: dict[str, object]) -> str:
    value = card["value"]
    unit = str(card["unit"])
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, int):
        return f"{value} {unit}".strip()
    return f"{float(value):.3f} {unit}".strip()


def _line_chart(df: pd.DataFrame, y: str, title: str, y_title: str):
    fig = px.line(
        df,
        x="time",
        y=y,
        color="vehicle",
        title=title,
        labels={"time": "Time [s]", y: y_title, "vehicle": "Vehicle"},
    )
    fig.update_layout(legend_title_text="", margin=dict(l=10, r=10, t=50, b=10))
    return fig


def _speed_tracking_chart(df: pd.DataFrame):
    fig = px.line(
        df,
        x="time",
        y="speed_kmh",
        color="vehicle",
        title="Vehicle Speed vs Target",
        labels={"time": "Time [s]", "speed_kmh": "Speed [km/h]", "vehicle": "Vehicle"},
    )
    target = df[df["vehicle"] == "Conventional"]
    fig.add_trace(
        go.Scatter(
            x=target["time"],
            y=target["target_speed_kmh"],
            mode="lines",
            line=dict(color="black", dash="dash", width=2),
            name="Target speed",
            hovertemplate="Time=%{x:.2f}s<br>Target=%{y:.2f} km/h<extra></extra>",
        )
    )
    fig.update_layout(legend_title_text="", margin=dict(l=10, r=10, t=50, b=10))
    return fig


def _mode_chart(df: pd.DataFrame):
    adds = df[df["vehicle"] == "ADDS"]
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=adds["time"],
            y=adds["coupling_mode_index"],
            mode="lines",
            line=dict(width=3),
            name="ADDS coupling mode",
            customdata=adds["coupling_mode"],
            hovertemplate="Time=%{x:.2f}s<br>Mode=%{customdata}<extra></extra>",
        )
    )
    fig.update_yaxes(
        tickmode="array",
        tickvals=list(range(len(MODE_ORDER))),
        ticktext=list(MODE_ORDER),
        title="Mode",
    )
    fig.update_xaxes(title="Time [s]")
    fig.update_layout(title="ADDS Coupling Mode Timeline", margin=dict(l=10, r=10, t=50, b=10))
    return fig


def _catalog_fuel_chart(summary_df: pd.DataFrame):
    fig = px.bar(
        summary_df,
        x="scenario_id",
        y="relative_fuel_change",
        color="split",
        title="Relative Fuel Change Across Catalog",
        labels={
            "scenario_id": "Scenario",
            "relative_fuel_change": "Relative fuel change [%]",
            "split": "Split",
        },
    )
    fig.add_hline(y=0.0, line_dash="dash", line_color="black")
    fig.update_layout(margin=dict(l=10, r=10, t=50, b=10), xaxis_tickangle=-30)
    return fig


def _controller_portfolio_fuel_chart(portfolio_df: pd.DataFrame):
    fig = px.bar(
        portfolio_df,
        x="scenario_id",
        y="relative_fuel_change",
        color="controller_label",
        barmode="group",
        title="Controller Portfolio Fuel Change",
        labels={
            "scenario_id": "Scenario",
            "relative_fuel_change": "Relative fuel change [%]",
            "controller_label": "ADDS controller",
        },
    )
    fig.add_hline(y=0.0, line_dash="dot", line_color="black")
    fig.add_hline(y=-1.0, line_dash="dash", line_color="green")
    fig.update_layout(margin=dict(l=10, r=10, t=50, b=10), xaxis_tickangle=-30)
    return fig


def _controller_portfolio_acceptance_chart(portfolio_df: pd.DataFrame):
    acceptance_df = (
        portfolio_df.groupby("controller_label", as_index=False)
        .agg(
            accepted_runs=("efficiency_claim_accepted", "sum"),
            total_runs=("scenario_id", "count"),
        )
        .assign(
            acceptance_rate_percent=lambda df: 100.0
            * df["accepted_runs"]
            / df["total_runs"]
        )
    )
    fig = px.bar(
        acceptance_df,
        x="controller_label",
        y="acceptance_rate_percent",
        text="accepted_runs",
        title="Accepted Efficiency Claims By Controller",
        labels={
            "controller_label": "ADDS controller",
            "acceptance_rate_percent": "Acceptance rate [%]",
            "accepted_runs": "Accepted runs",
        },
    )
    fig.update_yaxes(range=[0, 100])
    fig.update_traces(texttemplate="%{text} accepted", textposition="outside")
    fig.update_layout(margin=dict(l=10, r=10, t=50, b=10), xaxis_tickangle=-20)
    return fig


def _controller_robustness_acceptance_chart(aggregate_df: pd.DataFrame):
    fig = px.bar(
        aggregate_df,
        x="controller_label",
        y="acceptance_rate_percent",
        text="accepted_efficiency_claims",
        title="Robustness Acceptance Rate By Controller",
        labels={
            "controller_label": "ADDS controller",
            "acceptance_rate_percent": "Acceptance rate [%]",
            "accepted_efficiency_claims": "Accepted runs",
        },
    )
    fig.update_yaxes(range=[0, 100])
    fig.update_traces(texttemplate="%{text} accepted", textposition="outside")
    fig.update_layout(margin=dict(l=10, r=10, t=50, b=10), xaxis_tickangle=-20)
    return fig


def _controller_robustness_heatmap(robustness_df: pd.DataFrame):
    heatmap_df = (
        robustness_df.groupby(["scenario_id", "controller_label"], as_index=False)
        .agg(acceptance_rate_percent=("efficiency_claim_accepted", "mean"))
    )
    heatmap_df["acceptance_rate_percent"] *= 100.0
    matrix = heatmap_df.pivot(
        index="scenario_id",
        columns="controller_label",
        values="acceptance_rate_percent",
    )
    fig = px.imshow(
        matrix,
        aspect="auto",
        color_continuous_scale="Greens",
        zmin=0.0,
        zmax=100.0,
        title="Per-Scenario Robustness Acceptance Rate",
        labels={
            "x": "ADDS controller",
            "y": "Scenario",
            "color": "Acceptance [%]",
        },
    )
    fig.update_layout(margin=dict(l=10, r=10, t=50, b=10))
    return fig


def _controller_robustness_fuel_chart(robustness_df: pd.DataFrame):
    summary_df = (
        robustness_df.groupby(["controller_label", "perturbation"], as_index=False)
        .agg(mean_relative_fuel_change=("relative_fuel_change", "mean"))
    )
    fig = px.bar(
        summary_df,
        x="perturbation",
        y="mean_relative_fuel_change",
        color="controller_label",
        barmode="group",
        title="Mean Fuel Change By Perturbation",
        labels={
            "perturbation": "Perturbation",
            "mean_relative_fuel_change": "Mean relative fuel change [%]",
            "controller_label": "ADDS controller",
        },
    )
    fig.add_hline(y=0.0, line_dash="dot", line_color="black")
    fig.add_hline(y=-1.0, line_dash="dash", line_color="green")
    fig.update_layout(margin=dict(l=10, r=10, t=50, b=10), xaxis_tickangle=-30)
    return fig


def _controller_robustness_rejection_chart(rejection_df: pd.DataFrame):
    fig = px.bar(
        rejection_df,
        x="controller_label",
        y="rejected_runs",
        color="verdict_code",
        title="Rejected Robustness Runs By Verdict",
        labels={
            "controller_label": "ADDS controller",
            "rejected_runs": "Rejected runs",
            "verdict_code": "Verdict",
        },
        color_discrete_map={
            "NO_MEANINGFUL_BENEFIT": "#6c757d",
            "TRADE_OFF_REQUIRES_REVIEW": "#d99000",
            "REJECTED_SAFETY": "#b22222",
        },
    )
    fig.update_layout(margin=dict(l=10, r=10, t=50, b=10), xaxis_tickangle=-20)
    return fig


def _mode_duration_chart(mode_duration_df: pd.DataFrame):
    fig = px.bar(
        mode_duration_df,
        x="mode",
        y="duration",
        title="ADDS Time Spent By Mode",
        labels={"mode": "Mode", "duration": "Duration [s]"},
        category_orders={"mode": list(MODE_ORDER)},
    )
    fig.update_layout(margin=dict(l=10, r=10, t=50, b=10), xaxis_tickangle=-30)
    return fig


def _sensitivity_fuel_chart(sensitivity_df: pd.DataFrame):
    fig = px.bar(
        sensitivity_df,
        x="perturbation",
        y="relative_fuel_change",
        color="verdict_code",
        title="Fuel Sensitivity Across Parameter Perturbations",
        labels={
            "perturbation": "Perturbation",
            "relative_fuel_change": "Relative fuel change [%]",
            "verdict_code": "Research verdict",
        },
        color_discrete_map={
            "ACCEPTABLE_BENEFIT": "#2e8b57",
            "NO_MEANINGFUL_BENEFIT": "#6c757d",
            "TRADE_OFF_REQUIRES_REVIEW": "#d99000",
            "REJECTED_SAFETY": "#b22222",
        },
    )
    fig.add_hline(y=-1.0, line_dash="dash", line_color="green")
    fig.add_hline(y=0.0, line_dash="dot", line_color="black")
    fig.update_layout(margin=dict(l=10, r=10, t=50, b=10), xaxis_tickangle=-30)
    return fig


def _sensitivity_tradeoff_chart(sensitivity_df: pd.DataFrame):
    fig = px.scatter(
        sensitivity_df,
        x="rms_speed_error_delta_kmh",
        y="relative_fuel_change",
        color="verdict_code",
        text="perturbation",
        size="adds_transitions",
        size_max=20,
        title="Fuel and Speed-Tracking Trade-off",
        labels={
            "rms_speed_error_delta_kmh": "RMS speed-error delta [km/h]",
            "relative_fuel_change": "Relative fuel change [%]",
            "verdict_code": "Research verdict",
            "adds_transitions": "ADDS transitions",
        },
        color_discrete_map={
            "ACCEPTABLE_BENEFIT": "#2e8b57",
            "NO_MEANINGFUL_BENEFIT": "#6c757d",
            "TRADE_OFF_REQUIRES_REVIEW": "#d99000",
            "REJECTED_SAFETY": "#b22222",
        },
    )
    fig.add_hline(y=-1.0, line_dash="dash", line_color="green")
    fig.add_vline(x=1.0, line_dash="dash", line_color="orange")
    fig.update_traces(textposition="top center")
    fig.update_layout(margin=dict(l=10, r=10, t=50, b=10))
    return fig


def _summary_json(comparison) -> str:
    payload = {
        "scenario": comparison.scenario.scenario_id,
        "adds_controller_kind": comparison.adds_controller_kind,
        "conventional_summary": comparison.comparison.conventional_summary,
        "adds_summary": comparison.comparison.adds_summary,
        "deltas": comparison.comparison.deltas,
        "verdict": asdict(comparison.verdict),
        "insights": [asdict(insight) for insight in comparison.insights],
        "mode_durations": [asdict(row) for row in comparison.mode_durations],
        "mode_transitions": [asdict(row) for row in comparison.mode_transitions],
    }
    return json.dumps(payload, indent=2, sort_keys=True)


def _track_lap_summary_json(report) -> str:
    payload = {
        "schema_version": report.schema_version,
        "track_name": report.track_name,
        "description": report.description,
        "adds_controller_kind": report.adds_controller_kind,
        "scenario": {
            "scenario_id": report.scenario.scenario_id,
            "initial_speed": report.scenario.initial_speed,
            "initial_gear": report.scenario.initial_gear,
            "time_limit": report.scenario.time_limit,
            "distance_limit": report.scenario.distance_limit,
        },
        "sections": [asdict(section) for section in report.sections],
        "conventional_summary": report.comparison.conventional_summary,
        "adds_summary": report.comparison.adds_summary,
        "deltas": report.comparison.deltas,
        "stats": [asdict(stat) for stat in report.stats],
    }
    return json.dumps(payload, indent=2, sort_keys=True)


def _track_lap_animation_payload(report) -> dict[str, object]:
    conventional = _animation_records(report.comparison.conventional_result.records)
    adds = _animation_records(report.comparison.adds_result.records)
    lap_distance = float(report.scenario.distance_limit or 1.0)
    return {
        "trackName": report.track_name,
        "controller": report.adds_controller_kind,
        "lapDistance": lap_distance,
        "conventional": conventional,
        "adds": adds,
        "maxTime": max(
            conventional[-1]["time"] if conventional else 0.0,
            adds[-1]["time"] if adds else 0.0,
        ),
        "stats": {stat.label: asdict(stat) for stat in report.stats},
    }


def _animation_records(records, sample_interval: float = 0.1) -> list[dict[str, float | str]]:
    sampled: list[dict[str, float | str]] = []
    next_sample_time = 0.0
    for record in records:
        time = float(record["time"])
        if time + 1e-9 < next_sample_time and record is not records[-1]:
            continue
        sampled.append(
            {
                "time": time,
                "distance": float(record["position"]),
                "speed": float(record["vehicle_speed"]) * 3.6,
                "targetSpeed": float(record["target_speed"]) * 3.6,
                "fuel": float(record["engine_fuel_used"]) * 1_000_000.0,
                "mode": str(record["coupling_mode"]),
                "engineRpm": float(record["engine_speed"]) * 60.0 / (2.0 * 3.141592653589793),
            }
        )
        next_sample_time = time + sample_interval
    if records and sampled[-1]["time"] != float(records[-1]["time"]):
        final = records[-1]
        sampled.append(
            {
                "time": float(final["time"]),
                "distance": float(final["position"]),
                "speed": float(final["vehicle_speed"]) * 3.6,
                "targetSpeed": float(final["target_speed"]) * 3.6,
                "fuel": float(final["engine_fuel_used"]) * 1_000_000.0,
                "mode": str(final["coupling_mode"]),
                "engineRpm": float(final["engine_speed"]) * 60.0 / (2.0 * 3.141592653589793),
            }
        )
    return sampled


def _track_lap_animation_html(report) -> str:
    payload = json.dumps(_track_lap_animation_payload(report))
    return f"""
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <style>
    :root {{
      --bg: #071018;
      --panel: rgba(10, 24, 36, 0.88);
      --panel-strong: rgba(16, 36, 54, 0.96);
      --border: rgba(136, 180, 210, 0.28);
      --text: #ecf7ff;
      --muted: #9db2c4;
      --conventional: #7dd3fc;
      --adds: #f8c14a;
      --good: #58d68d;
      --warn: #f4d03f;
      --track: #1e303d;
      --track-edge: #7894a8;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background:
        radial-gradient(circle at 18% 18%, rgba(48, 145, 190, 0.25), transparent 28%),
        radial-gradient(circle at 80% 22%, rgba(248, 193, 74, 0.16), transparent 30%),
        linear-gradient(135deg, #061019 0%, #0c1823 48%, #071018 100%);
      color: var(--text);
    }}
    .sim {{
      min-height: 690px;
      padding: 18px;
      border: 1px solid var(--border);
      border-radius: 18px;
      overflow: hidden;
      position: relative;
    }}
    .topbar {{
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 16px;
      margin-bottom: 14px;
    }}
    h2 {{
      margin: 0 0 5px;
      font-size: 21px;
      line-height: 1.2;
      letter-spacing: -0.02em;
    }}
    .subtitle {{
      color: var(--muted);
      font-size: 13px;
      line-height: 1.45;
    }}
    .controls {{
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      justify-content: flex-end;
    }}
    button {{
      border: 1px solid var(--border);
      background: rgba(255, 255, 255, 0.07);
      color: var(--text);
      border-radius: 999px;
      padding: 8px 12px;
      font-weight: 700;
      font-size: 12px;
      cursor: pointer;
    }}
    button:hover, button.active {{
      background: rgba(248, 193, 74, 0.18);
      border-color: rgba(248, 193, 74, 0.7);
    }}
    .layout {{
      display: grid;
      grid-template-columns: minmax(420px, 1fr) 320px;
      gap: 16px;
      align-items: stretch;
    }}
    .track-panel, .telemetry-panel {{
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 16px;
      box-shadow: 0 20px 60px rgba(0, 0, 0, 0.24);
    }}
    .track-panel {{
      min-height: 520px;
      padding: 12px;
      position: relative;
    }}
    svg {{
      display: block;
      width: 100%;
      height: 500px;
    }}
    .track-shadow {{
      fill: none;
      stroke: rgba(0, 0, 0, 0.36);
      stroke-width: 52;
      stroke-linecap: round;
      stroke-linejoin: round;
      transform: translate(0, 5px);
    }}
    .track-edge {{
      fill: none;
      stroke: var(--track-edge);
      stroke-width: 48;
      stroke-linecap: round;
      stroke-linejoin: round;
    }}
    .track {{
      fill: none;
      stroke: var(--track);
      stroke-width: 38;
      stroke-linecap: round;
      stroke-linejoin: round;
    }}
    .center-line {{
      fill: none;
      stroke: rgba(236, 247, 255, 0.42);
      stroke-width: 2;
      stroke-dasharray: 12 14;
      stroke-linecap: round;
    }}
    .sector-dot {{
      fill: rgba(236, 247, 255, 0.8);
      stroke: #061019;
      stroke-width: 2;
    }}
    .finish {{
      stroke: #ffffff;
      stroke-width: 4;
      stroke-dasharray: 5 5;
    }}
    .car {{
      filter: drop-shadow(0 8px 8px rgba(0,0,0,0.38));
      transition: opacity 0.2s ease;
    }}
    .car-body {{
      rx: 7;
      ry: 7;
      stroke: rgba(255,255,255,0.88);
      stroke-width: 2;
    }}
    .car-label {{
      font-size: 11px;
      font-weight: 800;
      fill: #061019;
      text-anchor: middle;
      dominant-baseline: central;
      pointer-events: none;
    }}
    .telemetry-panel {{
      padding: 14px;
      display: flex;
      flex-direction: column;
      gap: 12px;
    }}
    .time-box {{
      background: var(--panel-strong);
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 13px;
    }}
    .time-value {{
      font-size: 34px;
      font-weight: 850;
      letter-spacing: -0.04em;
    }}
    .progress {{
      height: 10px;
      border-radius: 999px;
      background: rgba(255,255,255,0.10);
      overflow: hidden;
      margin-top: 10px;
    }}
    .progress span {{
      display: block;
      height: 100%;
      width: 0%;
      background: linear-gradient(90deg, var(--conventional), var(--adds));
    }}
    .car-card {{
      border-radius: 14px;
      padding: 12px;
      background: rgba(255,255,255,0.055);
      border: 1px solid var(--border);
    }}
    .car-card h3 {{
      margin: 0 0 10px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      font-size: 14px;
    }}
    .pill {{
      border-radius: 999px;
      padding: 4px 8px;
      font-size: 11px;
      font-weight: 800;
      color: #061019;
    }}
    .pill.conventional {{ background: var(--conventional); }}
    .pill.adds {{ background: var(--adds); }}
    .grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 9px;
    }}
    .metric {{
      background: rgba(0,0,0,0.18);
      border-radius: 10px;
      padding: 9px;
    }}
    .label {{
      color: var(--muted);
      font-size: 10px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      margin-bottom: 4px;
    }}
    .value {{
      font-size: 16px;
      font-weight: 800;
      letter-spacing: -0.02em;
    }}
    .mode-value {{
      color: var(--adds);
      font-size: 13px;
      font-weight: 850;
    }}
    .gap {{
      border-radius: 14px;
      padding: 12px;
      border: 1px solid rgba(248, 193, 74, 0.32);
      background: rgba(248, 193, 74, 0.08);
    }}
    .legend {{
      position: absolute;
      left: 22px;
      bottom: 22px;
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      color: var(--muted);
      font-size: 12px;
      background: rgba(6, 16, 25, 0.72);
      border: 1px solid var(--border);
      border-radius: 999px;
      padding: 8px 11px;
      backdrop-filter: blur(10px);
    }}
    .key {{ display: inline-flex; align-items: center; gap: 6px; }}
    .swatch {{ width: 10px; height: 10px; border-radius: 50%; }}
    .note {{
      margin-top: 12px;
      color: var(--muted);
      font-size: 12px;
      line-height: 1.45;
    }}
    @media (max-width: 820px) {{
      .topbar, .layout {{ display: block; }}
      .controls {{ justify-content: flex-start; margin-top: 12px; }}
      .track-panel {{ margin-bottom: 14px; min-height: 430px; }}
      svg {{ height: 390px; }}
    }}
  </style>
</head>
<body>
  <div class="sim">
    <div class="topbar">
      <div>
        <h2>2D Live Track-Lap Simulator</h2>
        <div class="subtitle">Two simulated vehicles replay the same distance-limited lap. The ADDS marker changes behavior as the drivetrain connects, decouples, rev-matches, and re-engages.</div>
      </div>
      <div class="controls">
        <button id="play">Play</button>
        <button id="reset">Reset</button>
        <button class="speed active" data-speed="1">1x</button>
        <button class="speed" data-speed="2">2x</button>
        <button class="speed" data-speed="4">4x</button>
      </div>
    </div>
    <div class="layout">
      <div class="track-panel">
        <svg viewBox="0 0 760 520" role="img" aria-label="2D reference circuit animation">
          <path id="circuit-shadow" class="track-shadow"></path>
          <path id="circuit-edge" class="track-edge"></path>
          <path id="circuit" class="track"></path>
          <path id="circuit-center" class="center-line"></path>
          <line id="finish" class="finish" x1="126" y1="302" x2="176" y2="342"></line>
          <circle class="sector-dot" cx="450" cy="88" r="6"></circle>
          <circle class="sector-dot" cx="642" cy="272" r="6"></circle>
          <circle class="sector-dot" cx="430" cy="470" r="6"></circle>
          <g id="car-conventional" class="car">
            <rect class="car-body" x="-19" y="-10" width="38" height="20" fill="var(--conventional)"></rect>
            <text class="car-label" x="0" y="0">C</text>
          </g>
          <g id="car-adds" class="car">
            <rect class="car-body" x="-19" y="-10" width="38" height="20" fill="var(--adds)"></rect>
            <text class="car-label" x="0" y="0">A</text>
          </g>
        </svg>
        <div class="legend">
          <span class="key"><span class="swatch" style="background: var(--conventional)"></span>Conventional</span>
          <span class="key"><span class="swatch" style="background: var(--adds)"></span>ADDS</span>
          <span class="key">Dashed line: racing reference centerline</span>
        </div>
      </div>
      <div class="telemetry-panel">
        <div class="time-box">
          <div class="label">Simulation time</div>
          <div id="time" class="time-value">0.00 s</div>
          <div class="progress"><span id="progress"></span></div>
        </div>
        <div class="car-card">
          <h3>Conventional <span class="pill conventional">baseline</span></h3>
          <div class="grid">
            <div class="metric"><div class="label">Speed</div><div id="c-speed" class="value">0.0 km/h</div></div>
            <div class="metric"><div class="label">Fuel</div><div id="c-fuel" class="value">0 ml</div></div>
            <div class="metric"><div class="label">Distance</div><div id="c-dist" class="value">0.00 km</div></div>
            <div class="metric"><div class="label">Engine</div><div id="c-rpm" class="value">0 rpm</div></div>
          </div>
        </div>
        <div class="car-card">
          <h3>ADDS <span class="pill adds">adaptive</span></h3>
          <div class="grid">
            <div class="metric"><div class="label">Speed</div><div id="a-speed" class="value">0.0 km/h</div></div>
            <div class="metric"><div class="label">Fuel</div><div id="a-fuel" class="value">0 ml</div></div>
            <div class="metric"><div class="label">Distance</div><div id="a-dist" class="value">0.00 km</div></div>
            <div class="metric"><div class="label">Engine</div><div id="a-rpm" class="value">0 rpm</div></div>
          </div>
          <div class="metric" style="margin-top:9px;"><div class="label">Coupling mode</div><div id="a-mode" class="mode-value">CONNECTED</div></div>
        </div>
        <div class="gap">
          <div class="label">Live comparison</div>
          <div class="value" id="gap">Gap: 0.00 s</div>
          <div class="note" id="fuel-gap">Fuel delta: 0 ml</div>
        </div>
      </div>
    </div>
  </div>
  <script>
    const payload = {payload};
    const points = [
      [150, 322], [170, 195], [292, 108], [456, 88], [620, 166],
      [662, 292], [590, 412], [442, 472], [265, 438], [128, 350], [150, 322]
    ];
    const pathD = "M " + points.map(p => p.join(" ")).join(" L ");
    for (const id of ["circuit-shadow", "circuit-edge", "circuit", "circuit-center"]) {{
      document.getElementById(id).setAttribute("d", pathD);
    }}

    const segmentLengths = [];
    let totalPathLength = 0;
    for (let i = 0; i < points.length - 1; i++) {{
      const dx = points[i + 1][0] - points[i][0];
      const dy = points[i + 1][1] - points[i][1];
      const length = Math.hypot(dx, dy);
      segmentLengths.push(length);
      totalPathLength += length;
    }}

    function trackPoint(progress, laneOffset) {{
      let distance = ((progress % 1) + 1) % 1 * totalPathLength;
      for (let i = 0; i < segmentLengths.length; i++) {{
        const length = segmentLengths[i];
        if (distance <= length || i === segmentLengths.length - 1) {{
          const t = length === 0 ? 0 : distance / length;
          const p0 = points[i];
          const p1 = points[i + 1];
          const x = p0[0] + (p1[0] - p0[0]) * t;
          const y = p0[1] + (p1[1] - p0[1]) * t;
          const angle = Math.atan2(p1[1] - p0[1], p1[0] - p0[0]);
          const normalX = -Math.sin(angle);
          const normalY = Math.cos(angle);
          return {{
            x: x + normalX * laneOffset,
            y: y + normalY * laneOffset,
            angle: angle * 180 / Math.PI
          }};
        }}
        distance -= length;
      }}
      return {{ x: points[0][0], y: points[0][1], angle: 0 }};
    }}

    function interpolate(records, time) {{
      if (!records.length) return null;
      if (time <= records[0].time) return records[0];
      if (time >= records[records.length - 1].time) return records[records.length - 1];
      let lo = 0;
      let hi = records.length - 1;
      while (hi - lo > 1) {{
        const mid = Math.floor((lo + hi) / 2);
        if (records[mid].time <= time) lo = mid; else hi = mid;
      }}
      const a = records[lo];
      const b = records[hi];
      const f = (time - a.time) / Math.max(b.time - a.time, 1e-9);
      return {{
        time,
        distance: a.distance + (b.distance - a.distance) * f,
        speed: a.speed + (b.speed - a.speed) * f,
        targetSpeed: a.targetSpeed + (b.targetSpeed - a.targetSpeed) * f,
        fuel: a.fuel + (b.fuel - a.fuel) * f,
        mode: f < 0.5 ? a.mode : b.mode,
        engineRpm: a.engineRpm + (b.engineRpm - a.engineRpm) * f
      }};
    }}

    let playing = false;
    let simTime = 0;
    let speed = 1;
    let lastTimestamp = null;
    const playButton = document.getElementById("play");
    const resetButton = document.getElementById("reset");
    const speedButtons = Array.from(document.querySelectorAll(".speed"));

    playButton.addEventListener("click", () => {{
      playing = !playing;
      playButton.textContent = playing ? "Pause" : "Play";
      lastTimestamp = null;
    }});
    resetButton.addEventListener("click", () => {{
      playing = false;
      simTime = 0;
      playButton.textContent = "Play";
      update();
    }});
    for (const button of speedButtons) {{
      button.addEventListener("click", () => {{
        speed = Number(button.dataset.speed);
        speedButtons.forEach(item => item.classList.remove("active"));
        button.classList.add("active");
      }});
    }}

    function setText(id, value) {{
      document.getElementById(id).textContent = value;
    }}
    function format(value, decimals = 1) {{
      return Number(value).toFixed(decimals);
    }}
    function updateCar(id, state, offset) {{
      const progress = Math.min(state.distance / payload.lapDistance, 1);
      const p = trackPoint(progress, offset);
      document.getElementById(id).setAttribute("transform", `translate(${{p.x}} ${{p.y}}) rotate(${{p.angle}})`);
    }}
    function update() {{
      const c = interpolate(payload.conventional, simTime);
      const a = interpolate(payload.adds, simTime);
      if (!c || !a) return;
      updateCar("car-conventional", c, -12);
      updateCar("car-adds", a, 12);
      setText("time", `${{format(simTime, 2)}} s`);
      document.getElementById("progress").style.width = `${{Math.min(100, 100 * simTime / payload.maxTime)}}%`;
      setText("c-speed", `${{format(c.speed, 1)}} km/h`);
      setText("c-fuel", `${{format(c.fuel, 0)}} ml`);
      setText("c-dist", `${{format(c.distance / 1000, 2)}} km`);
      setText("c-rpm", `${{format(c.engineRpm, 0)}} rpm`);
      setText("a-speed", `${{format(a.speed, 1)}} km/h`);
      setText("a-fuel", `${{format(a.fuel, 0)}} ml`);
      setText("a-dist", `${{format(a.distance / 1000, 2)}} km`);
      setText("a-rpm", `${{format(a.engineRpm, 0)}} rpm`);
      setText("a-mode", a.mode);
      const distanceGap = c.distance - a.distance;
      const roughGap = distanceGap / Math.max((c.speed + a.speed) / 7.2, 1);
      setText("gap", `Distance gap: ${{format(distanceGap, 1)}} m (${{format(roughGap, 2)}} s approx.)`);
      setText("fuel-gap", `Fuel delta: ${{format(a.fuel - c.fuel, 0)}} ml, target speed: ${{format(a.targetSpeed, 1)}} km/h`);
    }}
    function frame(timestamp) {{
      if (playing) {{
        if (lastTimestamp !== null) {{
          simTime += (timestamp - lastTimestamp) / 1000 * speed;
          if (simTime >= payload.maxTime) {{
            simTime = payload.maxTime;
            playing = false;
            playButton.textContent = "Play";
          }}
        }}
        lastTimestamp = timestamp;
        update();
      }} else {{
        lastTimestamp = null;
      }}
      requestAnimationFrame(frame);
    }}
    update();
    requestAnimationFrame(frame);
  </script>
</body>
</html>
"""


def _render_project_overview() -> None:
    st.subheader("Project Overview")
    st.write(
        "ADDS studies when a combustion-engine drivetrain should remain mechanically "
        "connected, when it can temporarily decouple for coasting, and how it should "
        "re-engage through rev-matching while respecting safety and drivability limits."
    )

    column_a, column_b, column_c = st.columns(3)
    with column_a:
        st.markdown("**Conventional baseline**")
        st.write("The engine remains connected whenever a gear is engaged.")
    with column_b:
        st.markdown("**Adaptive vehicle**")
        st.write("The drivetrain can open, coast, rev-match, and re-engage.")
    with column_c:
        st.markdown("**Fair comparison**")
        st.write("Both vehicles use the same scenario, parameters, and solver settings.")

    st.markdown("**Operating modes**")
    st.write(", ".join(f"`{mode}`" for mode in MODE_ORDER))

    st.markdown("**Current maturity**")
    st.write(
        "This is still a research simulator. The app is meant to inspect simulation "
        "behavior and compare baselines, not to claim real-vehicle performance."
    )


def _render_comparison_tab(comparison, df: pd.DataFrame) -> None:
    st.subheader("Comparison Summary")
    st.write(
        "Negative fuel delta means ADDS used less fuel than the conventional "
        "baseline for the same scenario. The mode timeline shows when ADDS "
        "moves through decoupling, coasting, rev-matching, and re-engagement."
    )
    verdict = comparison.verdict
    verdict_text = f"**{verdict.title}**  \n" + "  \n".join(
        f"- {reason}" for reason in verdict.reasons
    )
    if verdict.severity == "positive":
        st.success(verdict_text)
    elif verdict.severity in {"caution", "negative"}:
        st.warning(verdict_text)
    else:
        st.info(verdict_text)
    st.caption(
        "Initial acceptance gates: at least "
        f"{verdict.thresholds.minimum_fuel_reduction_percent:.1f}% fuel reduction, "
        "no more than "
        f"{verdict.thresholds.maximum_rms_speed_error_increase_kmh:.1f} km/h RMS "
        "speed-error increase, zero constraint regressions, and at most "
        f"{verdict.thresholds.maximum_safety_overrides} safety overrides."
    )
    card_columns = st.columns(4)
    for index, card in enumerate(comparison.metric_cards):
        with card_columns[index % len(card_columns)]:
            st.metric(str(card["label"]), _metric_value(card))
    if int(comparison.comparison.adds_summary["mode_transition_count"]) == 0:
        st.warning(
            "This run has no ADDS mode transitions. In that case the curves can "
            "look identical because the adaptive drivetrain stayed connected."
        )

    st.subheader("Decision Insights")
    for insight in comparison.insights:
        text = f"**{insight.title}**  \n{insight.message}"
        if insight.severity == "positive":
            st.success(text)
        elif insight.severity == "caution":
            st.warning(text)
        else:
            st.info(text)

    st.subheader("ADDS Event Analysis")
    mode_duration_df = _mode_duration_frame(comparison)
    mode_transition_df = _mode_transition_frame(comparison)
    left, right = st.columns(2)
    with left:
        st.plotly_chart(_mode_duration_chart(mode_duration_df), width="stretch")
    with right:
        st.dataframe(
            mode_duration_df,
            width="stretch",
            hide_index=True,
        )

    if mode_transition_df.empty:
        st.info("No ADDS mode transitions were detected for this run.")
    else:
        st.dataframe(
            mode_transition_df[
                [
                    "transition_index",
                    "time",
                    "from_mode",
                    "to_mode",
                    "speed_kmh",
                    "engine_speed_rpm",
                    "coupling_slip_speed",
                    "coupling_slip_energy",
                ]
            ],
            width="stretch",
            hide_index=True,
        )

    st.subheader("Trajectory Comparison")
    left, right = st.columns(2)
    with left:
        st.plotly_chart(_speed_tracking_chart(df), width="stretch")
    with right:
        st.plotly_chart(_line_chart(df, "fuel_used_ml", "Cumulative Fuel Used", "Fuel [ml]"), width="stretch")

    left, right = st.columns(2)
    with left:
        st.plotly_chart(_line_chart(df, "engine_speed_rpm", "Engine Speed", "Engine speed [rpm]"), width="stretch")
    with right:
        st.plotly_chart(_line_chart(df, "synchronous_engine_speed_rpm", "Synchronous Engine Speed", "Engine speed [rpm]"), width="stretch")

    left, right = st.columns(2)
    with left:
        st.plotly_chart(_mode_chart(df), width="stretch")
    with right:
        st.plotly_chart(
            _line_chart(df, "coupling_slip_energy", "Coupling Slip Energy", "Energy [J]"),
            width="stretch",
        )


def _render_catalog_tab(summary_df: pd.DataFrame) -> None:
    st.subheader("Scenario Catalog Summary")
    st.write(
        "This table runs every catalog scenario with the selected ADDS controller. "
        "It helps separate scenarios where adaptive decoupling is useful from "
        "scenarios where the system should stay connected."
    )
    st.plotly_chart(_catalog_fuel_chart(summary_df), width="stretch")
    st.dataframe(
        summary_df[
            [
                "scenario_id",
                "split",
                "fuel_delta_ml",
                "relative_fuel_change",
                "rms_speed_error_delta_kmh",
                "adds_transitions",
                "adds_safety_overrides",
                "constraint_regression",
                "verdict_code",
                "efficiency_claim_accepted",
            ]
        ],
        width="stretch",
        hide_index=True,
    )


def _render_track_lap_tab(report, lap_df: pd.DataFrame, stats_df: pd.DataFrame) -> None:
    st.subheader("Reference Track Lap")
    st.write(
        "This prototype compares the conventional baseline and ADDS over the same "
        "3 km distance-limited reference circuit. The lap is still longitudinal: "
        "it uses straights, lift-off sectors, minimum-speed holds, and "
        "reacceleration targets, but it does not yet model racing line, lateral "
        "load transfer, or combined-slip tire behavior."
    )

    st.iframe(_track_lap_animation_html(report), height=720)

    comparison = report.comparison
    metric_columns = st.columns(4)
    key_stats = {
        stat.label: stat
        for stat in report.stats
        if stat.label
        in {
            "Lap time",
            "Relative fuel change",
            "RMS speed error",
            "Decoupled duration",
        }
    }
    with metric_columns[0]:
        stat = key_stats["Lap time"]
        st.metric("ADDS lap time", f"{stat.adds_value:.2f} {stat.unit}", f"{stat.delta:.2f} {stat.unit}")
    with metric_columns[1]:
        stat = key_stats["Relative fuel change"]
        st.metric("Fuel change", f"{stat.adds_value:.3f} {stat.unit}", f"{stat.delta:.3f} {stat.unit}")
    with metric_columns[2]:
        stat = key_stats["RMS speed error"]
        st.metric("RMS speed error", f"{stat.adds_value:.3f} {stat.unit}", f"{stat.delta:.3f} {stat.unit}")
    with metric_columns[3]:
        stat = key_stats["Decoupled duration"]
        st.metric("Decoupled duration", f"{stat.adds_value:.2f} {stat.unit}")

    st.caption(
        "The current reference result terminates by distance limit for both vehicles. "
        f"Conventional: `{comparison.conventional_result.termination_reason}`; "
        f"ADDS: `{comparison.adds_result.termination_reason}`."
    )

    left, right = st.columns(2)
    with left:
        st.plotly_chart(_speed_tracking_chart(lap_df), width="stretch")
    with right:
        st.plotly_chart(_line_chart(lap_df, "fuel_used_ml", "Track Lap Cumulative Fuel", "Fuel [ml]"), width="stretch")

    left, right = st.columns(2)
    with left:
        st.plotly_chart(_mode_chart(lap_df), width="stretch")
    with right:
        st.plotly_chart(
            _line_chart(lap_df, "coupling_slip_energy", "Track Lap Coupling Slip Energy", "Energy [J]"),
            width="stretch",
        )

    st.subheader("Lap Statistics")
    st.dataframe(stats_df, width="stretch", hide_index=True)

    st.subheader("Reference Circuit Sections")
    st.dataframe(
        pd.DataFrame(asdict(section) for section in report.sections),
        width="stretch",
        hide_index=True,
    )

    left, right = st.columns(2)
    with left:
        st.download_button(
            label="Download track-lap summary JSON",
            data=_track_lap_summary_json(report),
            file_name=f"{report.scenario.scenario_id}_{report.adds_controller_kind}_track_lap.json",
            mime="application/json",
        )
    with right:
        st.download_button(
            label="Download track-lap trajectory CSV",
            data=lap_df.to_csv(index=False),
            file_name=f"{report.scenario.scenario_id}_{report.adds_controller_kind}_track_lap_trajectory.csv",
            mime="text/csv",
        )


def _render_controller_portfolio_tab(portfolio_df: pd.DataFrame) -> None:
    st.subheader("Controller Portfolio")
    st.write(
        "This view runs every catalog scenario across the available ADDS "
        "controller variants. It is useful for checking whether a new controller "
        "wins only in one hand-picked case or remains comparable across the "
        "full current catalog."
    )
    _render_insight_cards(_controller_portfolio_insights())
    left, right = st.columns(2)
    with left:
        st.plotly_chart(_controller_portfolio_fuel_chart(portfolio_df), width="stretch")
    with right:
        st.plotly_chart(_controller_portfolio_acceptance_chart(portfolio_df), width="stretch")

    st.dataframe(
        portfolio_df[
            [
                "scenario_id",
                "split",
                "controller_label",
                "relative_fuel_change",
                "rms_speed_error_delta_kmh",
                "adds_transitions",
                "adds_safety_overrides",
                "verdict_code",
                "efficiency_claim_accepted",
            ]
        ],
        width="stretch",
        hide_index=True,
    )


def _render_controller_robustness_portfolio_tab(
    robustness_df: pd.DataFrame,
    robustness_aggregate_df: pd.DataFrame,
    robustness_failure_df: pd.DataFrame,
    robustness_rejection_df: pd.DataFrame,
    robustness_recommendation_df: pd.DataFrame,
) -> None:
    st.subheader("Controller Robustness Portfolio")
    st.write(
        "This view repeats every catalog scenario across the default deterministic "
        "perturbation envelope for every ADDS controller. It checks whether a "
        "controller advantage survives payload, drag, rolling-resistance, grip, "
        "and grade shifts."
    )
    _render_insight_cards(_controller_robustness_insights())

    metric_columns = st.columns(3)
    with metric_columns[0]:
        st.metric("Robustness runs", f"{len(robustness_df)}")
    with metric_columns[1]:
        st.metric("Perturbations", f"{robustness_df['perturbation'].nunique()}")
    with metric_columns[2]:
        st.metric("Controllers", f"{robustness_df['controller_label'].nunique()}")

    left, right = st.columns(2)
    with left:
        st.plotly_chart(
            _controller_robustness_acceptance_chart(robustness_aggregate_df),
            width="stretch",
        )
    with right:
        st.plotly_chart(_controller_robustness_heatmap(robustness_df), width="stretch")

    st.plotly_chart(_controller_robustness_fuel_chart(robustness_df), width="stretch")

    st.dataframe(
        robustness_aggregate_df[
            [
                "controller_label",
                "run_count",
                "accepted_efficiency_claims",
                "acceptance_rate_percent",
                "mean_relative_fuel_change",
                "best_relative_fuel_change",
                "worst_relative_fuel_change",
                "maximum_rms_speed_error_delta_kmh",
                "total_mode_transitions",
                "maximum_safety_overrides",
                "constraint_regression_count",
            ]
        ],
        width="stretch",
        hide_index=True,
    )

    st.subheader("Most Fragile Cases")
    if robustness_failure_df.empty:
        st.success("No rejected controller-scenario robustness cases were detected.")
    else:
        st.dataframe(
            robustness_failure_df[
                [
                    "scenario_id",
                    "split",
                    "controller_label",
                    "rejected_runs",
                    "total_runs",
                    "rejection_rate_percent",
                    "worst_relative_fuel_change",
                    "maximum_rms_speed_error_delta_kmh",
                    "verdict_codes",
                    "rejected_perturbations",
                ]
            ].head(12),
            width="stretch",
            hide_index=True,
        )

    st.subheader("Rejection Breakdown")
    if robustness_rejection_df.empty:
        st.success("No rejected robustness verdicts were detected.")
    else:
        st.plotly_chart(
            _controller_robustness_rejection_chart(robustness_rejection_df),
            width="stretch",
        )
        st.dataframe(
            robustness_rejection_df[
                [
                    "controller_label",
                    "verdict_code",
                    "rejected_runs",
                    "controller_rejected_runs",
                    "rejection_share_percent",
                    "affected_scenarios",
                    "affected_perturbations",
                ]
            ],
            width="stretch",
            hide_index=True,
        )

    st.subheader("Recommended Next Actions")
    if robustness_recommendation_df.empty:
        st.info("No robustness recommendations were generated.")
    else:
        st.dataframe(
            robustness_recommendation_df[
                [
                    "priority",
                    "verdict_code",
                    "title",
                    "message",
                    "affected_controllers",
                    "affected_scenarios",
                ]
            ],
            width="stretch",
            hide_index=True,
        )

    with st.expander("Detailed robustness rows"):
        st.dataframe(
            robustness_df[
                [
                    "scenario_id",
                    "split",
                    "perturbation",
                    "controller_label",
                    "relative_fuel_change",
                    "rms_speed_error_delta_kmh",
                    "adds_transitions",
                    "adds_safety_overrides",
                    "verdict_code",
                    "efficiency_claim_accepted",
                ]
            ],
            width="stretch",
            hide_index=True,
        )


def _render_insight_cards(insights) -> None:
    for insight in insights:
        text = f"**{insight.title}**  \n{insight.message}"
        if insight.severity == "positive":
            st.success(text)
        elif insight.severity == "caution":
            st.warning(text)
        else:
            st.info(text)


def _render_robustness_tab(sensitivity, sensitivity_df: pd.DataFrame) -> None:
    st.subheader("Robustness And Sensitivity")
    st.write(
        "The selected scenario is repeated under deterministic changes to payload, "
        "aerodynamic drag, rolling resistance, tire grip, and road grade. A nominal "
        "benefit is robust only where the same fuel, mobility, and safety gates pass."
    )
    metric_columns = st.columns(4)
    with metric_columns[0]:
        st.metric(
            "Accepted perturbations",
            f"{sensitivity.accepted_runs}/{sensitivity.total_runs}",
        )
    with metric_columns[1]:
        st.metric("Acceptance rate", f"{sensitivity.acceptance_rate_percent:.1f} %")
    with metric_columns[2]:
        st.metric("Best fuel change", f"{sensitivity.best_relative_fuel_change:.3f} %")
    with metric_columns[3]:
        st.metric("Worst fuel change", f"{sensitivity.worst_relative_fuel_change:.3f} %")

    if sensitivity.accepted_runs == sensitivity.total_runs:
        st.success("The current simulated benefit passes all initial gates across the tested envelope.")
    elif sensitivity.accepted_runs > 0:
        st.warning(
            "The simulated benefit is condition-dependent. Review the rejected "
            "perturbations before generalizing the nominal result."
        )
    else:
        st.warning("No tested perturbation passes every initial research gate.")

    left, right = st.columns(2)
    with left:
        st.plotly_chart(_sensitivity_fuel_chart(sensitivity_df), width="stretch")
    with right:
        st.plotly_chart(_sensitivity_tradeoff_chart(sensitivity_df), width="stretch")

    st.dataframe(
        sensitivity_df[
            [
                "perturbation",
                "mass_scale",
                "drag_scale",
                "rolling_resistance_scale",
                "tire_friction_scale",
                "grade_offset_percent",
                "relative_fuel_change",
                "rms_speed_error_delta_kmh",
                "adds_transitions",
                "verdict_code",
                "efficiency_claim_accepted",
            ]
        ],
        width="stretch",
        hide_index=True,
    )


def _render_downloads_tab(
    comparison,
    df: pd.DataFrame,
    summary_df: pd.DataFrame,
    portfolio_df: pd.DataFrame,
    robustness_portfolio_df: pd.DataFrame,
    sensitivity_df: pd.DataFrame,
) -> None:
    st.subheader("Downloads")
    st.write("Export the current comparison or the full catalog summary for offline review.")
    st.download_button(
        label="Download current trajectory CSV",
        data=df.to_csv(index=False),
        file_name=f"{comparison.scenario.scenario_id}_{comparison.adds_controller_kind}_trajectory.csv",
        mime="text/csv",
    )
    st.download_button(
        label="Download current summary JSON",
        data=_summary_json(comparison),
        file_name=f"{comparison.scenario.scenario_id}_{comparison.adds_controller_kind}_summary.json",
        mime="application/json",
    )
    st.download_button(
        label="Download catalog summary CSV",
        data=summary_df.to_csv(index=False),
        file_name=f"adds_catalog_{comparison.adds_controller_kind}_summary.csv",
        mime="text/csv",
    )
    st.download_button(
        label="Download controller portfolio CSV",
        data=portfolio_df.to_csv(index=False),
        file_name="adds_controller_portfolio.csv",
        mime="text/csv",
    )
    st.download_button(
        label="Download controller robustness portfolio CSV",
        data=robustness_portfolio_df.to_csv(index=False),
        file_name="adds_controller_robustness_portfolio.csv",
        mime="text/csv",
    )
    st.download_button(
        label="Download selected sensitivity CSV",
        data=sensitivity_df.to_csv(index=False),
        file_name=(
            f"{comparison.scenario.scenario_id}_"
            f"{comparison.adds_controller_kind}_sensitivity.csv"
        ),
        mime="text/csv",
    )
    with st.expander("Raw comparison summaries"):
        st.json(json.loads(_summary_json(comparison)))


def main() -> None:
    st.title("ADDS: Adaptive Drivetrain Decoupling System")
    st.write(
        "A research dashboard for comparing a conventional connected drivetrain "
        "against an adaptive drivetrain decoupling strategy on identical scenarios."
    )
    st.info(
        "Start with `train_highway_lift_off`: it contains a lift-off/coasting "
        "opportunity, so ADDS should decouple, coast, rev-match, and re-engage. "
        "Flat cruise scenarios can look identical because there is no useful "
        "decoupling opportunity."
    )

    options = _scenario_options()
    option_by_label = {f"{option.scenario_id} ({option.split})": option for option in options}
    default_label = "train_highway_lift_off (train)"
    default_index = tuple(option_by_label).index(default_label) if default_label in option_by_label else 0

    with st.sidebar:
        st.header("Simulation Setup")
        selected_label = st.selectbox("Scenario", tuple(option_by_label), index=default_index)
        controller_label = st.radio(
            "ADDS controller",
            ("Rule-based ADDS", "Offline-optimized ADDS", "Learned ADDS"),
            help=(
                "Rule-based is the transparent initial baseline. Offline-optimized "
                "freezes the promoted C03 search candidate. Learned is a compact "
                "behavioral-cloning policy trained from the rule-based expert."
            ),
        )
        controller_kind_by_label = {
            "Rule-based ADDS": "rule_based",
            "Offline-optimized ADDS": "offline_optimized",
            "Learned ADDS": "learned",
        }
        controller_kind = controller_kind_by_label[controller_label]
        selected = option_by_label[selected_label]
        if controller_kind == "offline_optimized":
            st.caption(
                "The offline-optimized controller freezes candidate C03 from the "
                "train/validation/test policy-search audit."
            )
        if controller_kind == "learned":
            st.caption("The learned controller is an early conservative clone and may choose not to decouple.")
        st.caption(selected.description)
        st.caption("Tags: " + ", ".join(selected.tags))

    comparison = _comparison(selected.scenario_id, controller_kind)
    df = _records_frame(comparison)
    summary_df = _catalog_frame(controller_kind)
    portfolio_df = _controller_portfolio_frame()
    robustness_portfolio_df = _controller_robustness_portfolio_frame()
    robustness_aggregate_df = _controller_robustness_aggregate_frame()
    robustness_failure_df = _controller_robustness_failure_frame()
    robustness_rejection_df = _controller_robustness_rejection_frame()
    robustness_recommendation_df = _controller_robustness_recommendation_frame()
    sensitivity = _sensitivity_summary(selected.scenario_id, controller_kind)
    sensitivity_df = _sensitivity_frame(sensitivity)
    track_lap_report = _track_lap_report(controller_kind)
    track_lap_df = _track_lap_records_frame(track_lap_report)
    track_lap_stats_df = _track_lap_stats_frame(track_lap_report)

    (
        overview_tab,
        comparison_tab,
        track_lap_tab,
        catalog_tab,
        portfolio_tab,
        robustness_portfolio_tab,
        robustness_tab,
        downloads_tab,
    ) = st.tabs(
        (
            "Project Overview",
            "Scenario Comparison",
            "Track Lap",
            "Catalog Summary",
            "Controller Portfolio",
            "Robustness Portfolio",
            "Robustness",
            "Downloads",
        )
    )
    with overview_tab:
        _render_project_overview()
    with comparison_tab:
        _render_comparison_tab(comparison, df)
    with track_lap_tab:
        _render_track_lap_tab(track_lap_report, track_lap_df, track_lap_stats_df)
    with catalog_tab:
        _render_catalog_tab(summary_df)
    with portfolio_tab:
        _render_controller_portfolio_tab(portfolio_df)
    with robustness_portfolio_tab:
        _render_controller_robustness_portfolio_tab(
            robustness_portfolio_df,
            robustness_aggregate_df,
            robustness_failure_df,
            robustness_rejection_df,
            robustness_recommendation_df,
        )
    with robustness_tab:
        _render_robustness_tab(sensitivity, sensitivity_df)
    with downloads_tab:
        _render_downloads_tab(
            comparison,
            df,
            summary_df,
            portfolio_df,
            robustness_portfolio_df,
            sensitivity_df,
        )

    st.caption(
        "This prototype is for research visualization only. Simulation results "
        "do not imply real-vehicle efficiency or safety performance."
    )


if __name__ == "__main__":
    main()
