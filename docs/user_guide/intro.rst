.. _intro_user_guide:

User guide
==========

The user guide describes all approaches available to a user of HydroFlows to go from a set of pre-stored and described
environmental datasets, to workflows that translate these datasets into interconnected models, forecast products,
risk calculations and outputs and so on. A "workflow" is an interconnected set of operations, also called "rules"
that individually take one step in the translation from one or several input datasets into a certain output dataset.

This can be done using a command-line interface (CLI), or a application programming interface (API). We strongly
recommend to use the API, and write your workflows in scripts. The CLI is more easy to use and does not require
extensive programming experience, but does not offer flexibility.

In some places in this user guide you can navigate between API and CLI instructions by selecting one of two tabs. In
this way, as a user, you are not bothered by details that you are not interested in. Try it out below!

.. tab-set::

    .. tab-item:: API

        In this tab, you will be able to read and find examples of the usage of the Application Programming Interface
        (API).

    .. tab-item:: CLI

        In this tab, you will be able to read and find examples of the usage of the command-line interface.

From here onwards, we will dive into the details. We first give a general description of the CLI and API, and then go
into the different functionalities for workflows, events, and detailed available methods.

.. toctree::
   :caption: Contents:
   :maxdepth: 2

   api.rst
   cli.rst
   create.rst
