===================
HydroFlows Examples
===================

This folder contains example scripts to create and execute workflows using HydroFlows.


How to install
==============

To run the examples, you first need the clone the repository and install HydroFlows first,
see the `README.rst` in the root folder for instructions.
Next you need to add the binaries of the models used in the examples to the `examples/bin` folder
in the root of the repository. You can copy these from `p:/11209169-003-up2030/bin`

We currently support the following model versions:
- SFINCS v2.1.1 (store in `examples/bin/sfincs_v2.1.1`)
- Delft-FIAT v0.2.0 (store in `examples/bin/delft-fiat_v0.2.0`)
- Wflow-SBM v0.8.1 (store in `examples/bin/wflow_v0.8.1`)


How to run an example
=====================

To create and run example workflow, simply run the script with python.

.. code-block:: bash

    conda activate hydroflows
    python pluvial_risk.py
