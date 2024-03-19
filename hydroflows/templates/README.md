# run a workflow

from the project root folder using

    ```bash
    snakemake -s workflow/setup_models.smk --configfile workflow/snake_config/setup_models.yaml -c 1
    ```

# HydroFlows project template

├── README.md                               # this file
├── bin                                     # model binaries
|   ├── wflow
|   └── sfincs
├── data                                    # data files
│   ├── input                               # contains sfincs region file(s)
│   └── output
├── models                                  # model instances
│   ├── wflow                               # model instances
|   │   └── {region1}
|   │       ├── staticmaps.nc
|   │       ├── wflow_sbm_default.toml
|   │       ├── hydromt_wflow.yaml
|   │       └── simulations                 # model simulations
|   │           └── {sim1}
|   │               ├── wflow_sim1.toml
|   │               └── forcing.nc
│   ├── sfincs                              # model instances
|   │   └── {region1}
|   │       ├── sfincs.xxx
|   │       ├── sfincs.inp
|   │       └── simulations
|   │           └── {sim1}
|   │               ├── sfincs.xxx
|   │               └── sfincs.inp
│   └── fiat
├── results
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
