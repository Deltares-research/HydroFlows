""""Script to preprocess the local precipitation time series."""

import os
from pathlib import Path

import pandas as pd
import xarray as xr


def main(
    precip_raw_root: Path | str,
    precip_raw_fn: str,
    station_to_export: int,
    time_start: str,
    time_end: str,
):
    """__summary__."""
    df = pd.read_csv(os.path.join(precip_raw_root, precip_raw_fn))
    df_split = df.primary_key.str.split("_", expand=True).rename(
        columns={0: "Station_ID", 1: "time"}
    )
    df_split["precipitation"] = df["acumulado_chuva_1_h"]
    df_split["time"] = pd.to_datetime(df_split["time"], format="mixed")

    df_split["Station_ID"] = pd.to_numeric(df_split["Station_ID"])

    df_station = df_split[df_split["Station_ID"] == station_to_export].sort_values(
        by="time"
    )
    df_station.set_index("time", inplace=True)

    df_station = df_station[["precipitation"]]
    df_station = df_station.loc[time_start:time_end]

    duplicated_index = df_station.index.duplicated(keep="first")
    df_station_res = df_station[~duplicated_index].resample("1H").mean()

    ds_station_res = xr.Dataset.from_dataframe(df_station_res)

    out_root = os.getcwd()
    parent_dir = os.path.dirname(out_root)
    new_folder = os.path.join(parent_dir, "preprocessed_data")

    if not os.path.exists(new_folder):
        os.makedirs(new_folder)

    out_fn = f"output_scalar_resampled_precip_station{station_to_export}.nc"
    ds_station_res.to_netcdf(os.path.join(new_folder, out_fn))


if __name__ == "__main__":
    precip_raw_root = "p:/11209169-003-up2030/data/PRECIPITATION/rio"
    precip_raw_fn = "bq-results-20240701-123456-1719837312017.csv"
    station_to_export = 11
    time_start = "1997-01-01"
    time_end = "2024-01-01"

    main(precip_raw_root, precip_raw_fn, station_to_export, time_start, time_end)
