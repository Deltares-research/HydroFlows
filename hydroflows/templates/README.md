# Running the HydroFlows project template

To create a project folder and execute a workflow, run the following steps:

    ```bash
    hydroflows init <root>
    cd <root>
    snakemake -s workflow/setup_models.smk --configfile .\workflow\snake_config\setup_models_config.yml -c 1
    ```


# HydroFlows project template

├── README.md                               # this file
├── bin                                     # model binaries
|   ├── wflow
|   └── sfincs
├── data                                    # data files
│   ├── input                               # all raw input data
|   |   |── static_data                     # folder for local static data
|   |   |   ├── dem.tif
|   |   ├── forcing_data                    # folder for downloaded forcings data
|   |   |   ├── era5_rainfall.nc
|   |   |   ├── gtsm_waterlevels.nc
│   ├── interim                             # all preprocessed data and intermediate results
|   |   |── {region1}
|   |       |── rainfall
|   |       |   ├── {scenario}              # e.g. historical
|   |       |       ├── rainfall_rpXXX.csv
|   |       |       └── design_events.yml
|   |       |── discharge
|   |       |   ├── {scenario}              # e.g. historical
|   |       |       ├── discharge_rpXXX.csv
|   |       |       └── design_events.yml
|   |       |── coastal_waterlevels
|   |           ├── {scenario}              # e.g. historical
|   |               ├── waterlevels_rpXXX.csv
|   |               └── design_events.yml
│   └── output                              # model output data (not sure we need this as we save output with simulations?)
├── models                                  # model instances
│   ├── wflow                               # model instances
|   │   └── {region1}
|   │       ├── staticmaps.nc
|   │       ├── wflow_sbm_default.toml
|   │       ├── hydromt_wflow.yaml
|   │       └── simulations                 # model simulations
|   │           └── {scenario}
|   │               ├── wflow_sim1.toml
|   │               ├── forcing.nc
|   │               └── output.nc
│   ├── sfincs                              # model instances
|   │   └── {region1}
|   │       ├── sfincs.xxx
|   │       ├── sfincs.inp
|   │       └── simulations
|   │           └── {scenario}
|   │               └── {event1}
|   │                   ├── sfincs.xxx
|   │                   └── sfincs.inp
│   └── fiat
|       └── {region1}
|           ├── exposure
|           ├── vulnerability
|           ├── settings.toml
|           └── {scenario}
|               |── hazard.nc
|               |── settings.toml
|               └── output
|                   |── impact
|                   └── risk
├── results                                 # postprocessed model end results
|   └── {region1}
|       |── hazard
|       |   ├── {scenario}              # e.g. historical
|       |       |── flood_depth_pluvial_rpXXX.tif
|       |── impacts
|       |── risk
|       |   ├── {scenario}
|       |       |── risk.tif
|       |       |── risk.gpkg
├── workflow
│   ├── envs
|   │   ├── tool1.yaml
|   │   └── tool2.yaml
│   ├── hydromt_config
|   │   ├── fiat_build.yaml
|   │   └── wflow_build.yaml
│   ├── methods
|   │   ├── module1.smk
|   │   └── module2.smk
│   ├── notebooks
|   │   ├── notebook1.py.ipynb
|   │   └── notebook2.r.ipynb
│   ├── snake_config
|   │   ├── setup_models.yaml
|   │   └── run_wflow.yaml
│   ├── scripts
|   │   ├── script1.py
|   │   └── script2.R
|   ├── run_wflow.smk
|   └── setup_models.smk
