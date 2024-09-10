.. _api_reference:

=============
API reference
=============

HydroFlows' API consists of several classes, that can be programmatically called, and used to implement workflows
with python language. As a programmer, you may also decide to extend the methods, for instance if you require an
additional preprocessing method, want to run other hydrological, hydraulic or impact models, or require a new
postprocessing method.

In this API section we describe the following classes in turn:

* ``Workflow``: describes and offers methods to establish entire workflows, containing several interconnected rules.
  Is responsible for the logic between these rules and the intelligence of expanding and reducing rules where one rule
  provides multiple instances for a next rule, or vice versa.
* ``Event``: describes an event, including paths to input and output files such as forcing data. Rules can expand over
  multiple events.
* ``EventSet``: describes multiple events that belong together. This can for instance be a set with historical events,
  or a set that together estimates a probability density function of events.
* Several methods, that are subclassed from the base ``Method` class: an implementation of a ``Method`` defines inputs,
  outputs and parameters for a certain activity to run. This activity can be anything that creates output files from
  certain input files.

Workflow
========

A workflow consists of several rules, with each rule consisting of a method and the method's keyword arguments.

.. include:: workflow_methods.rst

Event and EventSet
==================

.. include:: events.rst

Rule
====

.. include:: rule.rst

Methods
=======
Rules inherit a certain method, which in turn contains the intelligence to produce certain output(s) from certain
input(s) and parameters. A method can for instance produce a set of forcing data for events, build or run a model, or
postprocess a result in a graph.

Any new method proposed should follow the structure of the base ``Method`` class

General method
--------------

.. currentmodule:: hydroflows.workflow

.. autosummary::
   :toctree: ../_generated

   method.Method


.. include:: rainfall_methods.rst

.. include:: wflow_methods.rst

.. include:: sfincs_methods.rst

.. include:: fiat_methods.rst
