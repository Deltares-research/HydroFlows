.. _intro_user_guide:

User guide
==========

HydroFlows currently consists of two main components: the workflow framework and the methods library.
The workflow framework is used to create workflows using python scripts and parse these to a workflow engine like Snakemake_.
The method library contains a collection of methods that can be used as building blocks in a workflow.

Creating workflows
------------------

In HydroFlows, a :term:`workflow` consists of methods that are chained together by connecting the file-based output of one method to the input of another.
Users can use one of the many methods available in the library or create methods of their own.
At initialization of a :term:`method` its input, output and parameters are validated.
Using the concept of :term:`wildcards`, a method can be applied to multiple input files in parallel or reduce over multiple input files.
When adding the method to the workflow, a :term:`rule` is created which evaluates all wildcards and sets up the connections between the methods.
In addition, some validation is done on the workflow to ensure it is correct.
At this point, the workflow can be test-run, executed or parsed to a workflow engine.
More information on how to use HydroFlows can be found in the :ref:`workflow_framework` section.

Methods library
---------------

Methods are the building blocks of a workflow in HydroFlows.
Users can use the methods available in the library or create their own methods.
Currently, the available methods in HydroFlows are focused on flood risk assessments.
An overview of the available methods can be found in the :ref:`method_library` section.


.. toctree::
   :maxdepth: 2

   workflow/intro
   method_library/intro
   examples/intro
