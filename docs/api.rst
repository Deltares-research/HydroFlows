.. currentmodule:: hydroflows

.. _api_reference:

#############
API reference
#############

.. _api_model:

Methods
=================
FIAT related methods
----------

.. autosummary::
   :toctree: _generated

   hydroflows.methods.FIATBuild

SFINCS related methods
----------

.. autosummary::
   :toctree: _generated

   hydroflows.methods.SfincsBuild
   hydroflows.methods.SfincsPostprocess
   hydroflows.methods.SfincsUpdateForcing
   hydroflows.methods.SfincsRun

Wflow related methods
----------

.. autosummary::
   :toctree: _generated

   hydroflows.methods.WflowBuild
   hydroflows.methods.WflowUpdateForcing
   hydroflows.methods.wflow.wflow_update_forcing.Input
   hydroflows.methods.wflow.wflow_update_forcing.Params
   hydroflows.methods.wflow.wflow_update_forcing.Output
   hydroflows.methods.WflowDesignHydro
   hydroflows.methods.WflowRun

Rainfall related methods
----------

.. autosummary::
   :toctree: _generated

   hydroflows.methods.GetERA5Rainfall
   hydroflows.methods.PluvialDesignEvents

Hazzard methods
----------

.. autosummary::
   :toctree: _generated

   hydroflows.methods.HazardCatalog
