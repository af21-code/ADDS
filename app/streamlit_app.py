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

from adds_sim.visualization import (
    MODE_ORDER,
    available_dashboard_scenarios,
    build_dashboard_catalog_summary,
    build_dashboard_comparison,
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


def _records_frame(comparison) -> pd.DataFrame:
    return pd.DataFrame((*comparison.conventional_records, *comparison.adds_records))


def _catalog_frame(controller_kind: str) -> pd.DataFrame:
    return pd.DataFrame(asdict(row) for row in _catalog_summary(controller_kind))


def _mode_duration_frame(comparison) -> pd.DataFrame:
    return pd.DataFrame(asdict(row) for row in comparison.mode_durations)


def _mode_transition_frame(comparison) -> pd.DataFrame:
    return pd.DataFrame(asdict(row) for row in comparison.mode_transitions)


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


def _render_downloads_tab(comparison, df: pd.DataFrame, summary_df: pd.DataFrame) -> None:
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
            ("Rule-based ADDS", "Learned ADDS"),
            help="The learned controller is a compact behavioral-cloning policy trained from the rule-based expert.",
        )
        controller_kind = "learned" if controller_label == "Learned ADDS" else "rule_based"
        selected = option_by_label[selected_label]
        if controller_kind == "learned":
            st.caption("The learned controller is an early conservative clone and may choose not to decouple.")
        st.caption(selected.description)
        st.caption("Tags: " + ", ".join(selected.tags))

    comparison = _comparison(selected.scenario_id, controller_kind)
    df = _records_frame(comparison)
    summary_df = _catalog_frame(controller_kind)

    overview_tab, comparison_tab, catalog_tab, downloads_tab = st.tabs(
        ("Project Overview", "Scenario Comparison", "Catalog Summary", "Downloads")
    )
    with overview_tab:
        _render_project_overview()
    with comparison_tab:
        _render_comparison_tab(comparison, df)
    with catalog_tab:
        _render_catalog_tab(summary_df)
    with downloads_tab:
        _render_downloads_tab(comparison, df, summary_df)

    st.caption(
        "This prototype is for research visualization only. Simulation results "
        "do not imply real-vehicle efficiency or safety performance."
    )


if __name__ == "__main__":
    main()
