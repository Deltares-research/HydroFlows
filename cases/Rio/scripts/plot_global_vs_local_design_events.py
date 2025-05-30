""""Script to plot the differences between the derived global and local pluvial design events."""

import glob
import os
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from hydroflows.methods.events import Event


def load_event_files(
    root: Path | str,
):
    """Load event files function."""
    global_design_events_root = os.path.join(
        root,
        "global",
        "events",
    )

    local_design_events_root = os.path.join(
        root,
        "local",
        "events",
    )

    event_yaml_files_global = glob.glob(
        os.path.join(global_design_events_root, "p_event*.yml")
    )

    return global_design_events_root, local_design_events_root, event_yaml_files_global


def plot_global_vs_local_hyetographs(
    global_design_events_root, local_design_events_root, event_yaml_files_global
):
    """Plot global vs local hyetographs function."""
    colors = plt.rcParams["axes.prop_cycle"].by_key()["color"]

    fig, axes = plt.subplots(3, 3, figsize=(7, 7), sharey=True)
    axes = axes.flatten()

    for i, event_yaml_file in enumerate(event_yaml_files_global):
        event = Event.from_yaml(event_yaml_file)

        global_event_df = pd.read_csv(
            Path(global_design_events_root, f"{event.name}.csv")
        )
        global_event_df["time"] = pd.to_datetime(global_event_df["time"])

        midpoint = len(global_event_df) // 2
        global_event_df["relative_time"] = (
            global_event_df["time"] - global_event_df["time"].iloc[midpoint]
        ).dt.total_seconds() / 3600

        local_event_df = pd.read_csv(
            Path(local_design_events_root, f"{event.name}.csv")
        )

        ax = axes[i]

        ax.step(
            global_event_df["relative_time"],
            global_event_df["0"],
            where="mid",
            label="Global",
            color=colors[i],
            linestyle="--",
        )

        ax.step(
            global_event_df["relative_time"],
            local_event_df["0"],
            where="mid",
            color=colors[i],
            linestyle="-",
            label="Local",
        )

        if i == 0:
            ax.legend()
        ax.set_title(f" RP {1/event.probability} years")
        ax.grid(True, alpha=0.3)
        ax.set_xlabel("Time [hour]")

        if i % 3 == 0:
            ax.set_ylabel("Intensity [mm/hour]")

    for j in range(len(event_yaml_files_global), len(axes)):
        fig.delaxes(axes[j])

    fig.tight_layout()

    plot_dir = Path(os.getcwd(), "figs")
    plot_dir.mkdir(exist_ok=True)

    fig.savefig(
        Path(plot_dir, "global_vs_local_hyetographs.png"), dpi=150, bbox_inches="tight"
    )


def plot_global_vs_local_idfs(global_design_events_root, local_design_events_root):
    """Plot global vs local idfs function."""
    df_idf_global = pd.read_csv(
        os.path.join(global_design_events_root, "idf.csv"), index_col=0
    )
    df_idf_local = pd.read_csv(
        os.path.join(local_design_events_root, "idf.csv"), index_col=0
    )

    colors = plt.rcParams["axes.prop_cycle"].by_key()["color"]

    fig, axes = plt.subplots(3, 3, figsize=(7, 7), sharey=True)
    axes = axes.flatten()

    for i, period in enumerate(df_idf_local.columns):
        ax = axes[i]
        df_idf_global[period].plot(
            ax=ax, legend=False, color=colors[i], linestyle="--", label="Global"
        )
        df_idf_local[period].plot(
            ax=ax, legend=False, color=colors[i], linestyle="-", label="Local"
        )
        if period == "1.0":
            ax.set_title(f"RP {period} year")
        else:
            ax.set_title(f"RP {period} years")

        ax.grid(True, alpha=0.3)
        ax.set_xlabel("Event duration [hour]")
        if i % 3 == 0:
            ax.set_ylabel("Intensity [mm/hour]")
        if i == 0:
            ax.legend()

    for j in range(len(df_idf_local.columns), len(axes)):
        fig.delaxes(axes[j])

    fig.tight_layout()

    plot_dir = Path(os.getcwd(), "figs")
    plot_dir.mkdir(exist_ok=True)

    fig.savefig(
        Path(plot_dir, "global_vs_local_idfs.png"), dpi=150, bbox_inches="tight"
    )


def main():
    """__summary__."""
    root = "p:/11209169-003-up2030/cases/rio_new/setups"

    (
        global_design_events_root,
        local_design_events_root,
        event_yaml_files_global,
    ) = load_event_files(root)

    plot_global_vs_local_hyetographs(
        global_design_events_root, local_design_events_root, event_yaml_files_global
    )
    plot_global_vs_local_idfs(global_design_events_root, local_design_events_root)


if __name__ == "__main__":
    main()
