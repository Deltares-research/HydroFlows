.. currentmodule:: hydroflows

.. _api_reference:

#############
API reference
#############

=======
Methods
=======

FIAT related methods
--------------------

.. autosummary::
   :toctree: _generated

   hydroflows.methods.FIATBuild
   hydroflows.methods.FIATRun
   hydroflows.methods.FIATUpdateHazard

SFINCS related methods
----------------------

.. autosummary::
   :toctree: _generated

   hydroflows.methods.SfincsBuild
   hydroflows.methods.SfincsPostprocess
   hydroflows.methods.SfincsUpdateForcing
   hydroflows.methods.SfincsRun

Wflow related methods
---------------------

.. autosummary::
   :toctree: _generated

   hydroflows.methods.WflowBuild
   hydroflows.methods.WflowUpdateForcing
   hydroflows.methods.WflowDesignHydro
   hydroflows.methods.WflowRun

Rainfall related methods
------------------------

.. autosummary::
   :toctree: _generated

   hydroflows.methods.GetERA5Rainfall
   hydroflows.methods.PluvialDesignEvents

Hazzard methods
---------------

.. autosummary::
   :toctree: _generated

   hydroflows.methods.HazardCatalog

Workflow related methods
---------------

.. autosummary::
   :toctree: _generated

   hydroflows.workflows.events.Forcing
   hydroflows.workflows.events.Hazard
   hydroflows.workflows.events.Impact
   hydroflows.workflows.events.Event
   hydroflows.workflows.events.Roots
   hydroflows.workflows.events.EventCatalog
