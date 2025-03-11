.. _workflow_framework:

Creating workflows
==================

HydroFlows provides a framework that allows users to define methods, compose workflows,
and execute them within HydroFlows or with supported workflow engines.
It is designed to simplify the process of creating complex model and data pipelines by providing an
interactive environment to define methods and compose workflows.
By defining workflows in HydroFlows and exported these to supported workflow engines,
users can take advantage of the capabilities of these engines,
while saving time and effort to learn the sometimes complicated syntax of a workflow engines.

The framework is built around the following components as shown in the diagram below:

.. figure:: ../../_static/hydroflows_framework_diagram.png
    :alt: HydroFlows Workflows
    :align: center


This section provides an overview of the HydroFlows framework and its components. It includes the following subsections:

- **Terminology**: This section provides definitions of key terms used throughout the HydroFlows framework.
- **Define Method**: This section provides instructions on how to create methods and highlights some special methods.
- **Compose Workflow**: This section guides users on how to compose workflows by linking methods defined in the previous section, including wildcards to ot generalize rules to different input files.
- **Execute Workflow**: This section explains the steps to execute workflows within HydroFlows or with supported workflow engines.
- **Add Own Method**: This section describes how users can add their own custom methods to the HydroFlows framework.

.. toctree::
   :maxdepth: 2

   terminology
   define_method
   compose_workflow
   execute_workflow
   add_own_method
