.. currentmodule:: hydroflows.workflow

A ``Rule`` instance contains the intelligence to connect inputs and outputs (from other rules) within a workflow and
run the method. It can also detect wildcards for expansion or reduction of a method. Rules have a logical order, stored in
a ``Rules`` instance

.. autosummary::
   :toctree: ../_generated

   rule.Rule
   rule.Rules
