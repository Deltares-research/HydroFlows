==================
Rio case structure
==================

.. code-block:: text

    rio
    ├── bin
    │   ├── fiat_v0.2.1
    │   └── sfincs_v0.2.1
    ├── data
    │   ├── global-data
    │   │   └── data_catalog.yml
    │   ├── local-data
    │   │   └── data_catalog.yml
    │   └── preprocessed-data
    │       └── data_catalog.yml
    ├── scripts
    │   ├── clip_exposure.py
    │   ├── preprocess_exposure.py
    │   ├── plot_global_vs_local_design_events.py
    │   └── preprocess_local_precip.py
    ├── setups
    │   ├── global
    │   │   ├── hydromt_config
    │   │   ├── events
    │   │   ├── models
    │   │   ├── output
    │   │   ├── Snakefile.smk
    │   │   └── Snakefile.config.yml
    │   └── local
    │       ├── hydromt_config
    │       ├── events
    │       ├── models
    │       ├── output
    │       ├── Snakefile-risk.smk
    │       ├── Snakefile-risk.config.smk
    │       ├── Snakefile-validation.smk
    │       └── Snakefile-validation.config.yml
    ├── global-workflow-risk.py
    ├── global-workflow-risk-climate
    ├── local-workflow-risk.py
    ├── local-workflow-risk-climate-strategies.py
    └── local-workflow-validation.py
