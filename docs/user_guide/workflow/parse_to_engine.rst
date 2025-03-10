.. _parse_to_engine:

Export to Workflow Engine
=========================


.. figure:: ../../_static/hydroflows_framework_snake.png
    :alt: Parse to SnakeMake and execute
    :align: center



.. _cli:

Command-line Interface
======================

The command line interface  (CLI) is meant to provide an generic interface to run methods within the HydroFlows framework.
Almost any workflow engine support CLI commands which makes it possible to run the workflows from external workflows engines.
Note that a users typically does not need to use the CLI directly, but rather uses the Python API to create and export workflows
which contain the CLI commands.

The CLI is available as the `hydroflows` command after installation of the HydroFlows package.
The main subcommand is `method` which serves as a generic CLI to any Hydroflows `Method` subclass.
The `method` subcommand first validates the parameters by initializing the method ``Method(**kwargs)`` and then calls the ``run()`` method to execute the method.
You can find the syntax of the subcommand using the `--help` flag:

.. code-block:: shell

    $ hydroflows method --help

.. program-output:: hydroflows method --help
