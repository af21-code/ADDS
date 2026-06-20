"""Streamlit prototype for visual ADDS simulation comparisons."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from adds_sim.visualization import MODE_ORDER, available_dashboard_scenarios, build_dashboard_comparison


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


def _records_frame(comparison) -> pd.DataFrame:
    return pd.DataFrame((*comparison.conventional_records, *comparison.adds_records))


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


def main() -> None:
    st.title("ADDS: Adaptive Drivetrain Decoupling System")
    st.write(
        "A research dashboard for comparing a conventional connected drivetrain "
        "against an adaptive drivetrain decoupling strategy on identical scenarios."
    )

    options = _scenario_options()
    option_by_label = {f"{option.scenario_id} ({option.split})": option for option in options}

    with st.sidebar:
        st.header("Simulation Setup")
        selected_label = st.selectbox("Scenario", tuple(option_by_label))
        controller_label = st.radio(
            "ADDS controller",
            ("Rule-based ADDS", "Learned ADDS"),
            help="The learned controller is a compact behavioral-cloning policy trained from the rule-based expert.",
        )
        controller_kind = "learned" if controller_label == "Learned ADDS" else "rule_based"
        selected = option_by_label[selected_label]
        st.caption(selected.description)
        st.caption("Tags: " + ", ".join(selected.tags))

    comparison = _comparison(selected.scenario_id, controller_kind)
    df = _records_frame(comparison)

    st.subheader("Comparison Summary")
    card_columns = st.columns(4)
    for index, card in enumerate(comparison.metric_cards):
        with card_columns[index % len(card_columns)]:
            st.metric(str(card["label"]), _metric_value(card))

    st.subheader("Trajectory Comparison")
    left, right = st.columns(2)
    with left:
        st.plotly_chart(_line_chart(df, "speed_kmh", "Vehicle Speed", "Speed [km/h]"), use_container_width=True)
    with right:
        st.plotly_chart(_line_chart(df, "target_speed_kmh", "Target Speed Reference", "Target speed [km/h]"), use_container_width=True)

    left, right = st.columns(2)
    with left:
        st.plotly_chart(_line_chart(df, "fuel_used_ml", "Cumulative Fuel Used", "Fuel [ml]"), use_container_width=True)
    with right:
        st.plotly_chart(_line_chart(df, "engine_speed_rpm", "Engine Speed", "Engine speed [rpm]"), use_container_width=True)

    left, right = st.columns(2)
    with left:
        st.plotly_chart(_mode_chart(df), use_container_width=True)
    with right:
        st.plotly_chart(
            _line_chart(df, "coupling_slip_energy", "Coupling Slip Energy", "Energy [J]"),
            use_container_width=True,
        )

    with st.expander("Raw comparison summaries"):
        st.json(
            {
                "scenario": comparison.scenario.scenario_id,
                "adds_controller_kind": comparison.adds_controller_kind,
                "conventional_summary": comparison.comparison.conventional_summary,
                "adds_summary": comparison.comparison.adds_summary,
                "deltas": comparison.comparison.deltas,
            }
        )

    st.caption(
        "This prototype is for research visualization only. Simulation results "
        "do not imply real-vehicle efficiency or safety performance."
    )


if __name__ == "__main__":
    main()
