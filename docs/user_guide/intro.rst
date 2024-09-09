.. _intro_user_guide:

User guide
==========

The user guide describes all approaches available to a user of HydroFlows to go from a set of pre-stored and described
environmental datasets, to workflows that translate these datasets into interconnected models, forecast products,
risk calculations and outputs and so on. A "workflow" is an interconnected set of operations, also called "rules"
that individually take one step in the translation from one or several input datasets into a certain output dataset.

This can be done using a command-line interface (CLI), or a application programming interface (API). The CLI is more
easy to use and does not require extensive programming experience, the API offers more flexibility, but does require
Python programming experience. In many places in this user guide you can navigate between CLI instructions and API
instructions by selecting one of two tabs. In this way, as a user, you are not bothered by details that you are not
interested in. Try it out below!

.. tab-set::

    .. tab-item:: CLI

        In this tab, you will be able to read and find examples of the usage of the command-line interface.

    .. tab-item:: API

        In this tab, you will be able to read and find examples of the usage of the Application Programming Interface
        (API).

From here onwards, we will dive into the details. We first give a general description of the CLI and API, and then go
into the different functionalities for workflows, events, and detailed available methods.

.. toctree::
   :caption: Contents:
   :maxdepth: 2

   cli.rst
   api.rst
   create.rst
