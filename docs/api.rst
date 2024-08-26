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

Hazzard related methods
-----------------------

.. autosummary::
   :toctree: _generated

   hydroflows.methods.HazardCatalog

Workflow related methods
------------------------

.. autosummary::
   :toctree: _generated

   hydroflows.events.Forcing
   hydroflows.events.Hazard
   hydroflows.events.Impact
   hydroflows.events.Event
   hydroflows.events.Roots
   hydroflows.events.EventCatalog
