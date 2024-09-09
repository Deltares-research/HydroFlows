.. _ug_cli:

Command-line interface
----------------------

The command line interface is meant to provide an easy, reproducible and streamlined approach to generate
entire workflows from the existing set of methods available in HydroFlows, and export these to a language of choice.
The interface is not meant to run these workflows at scale (i.e. using multiple process or HPC). For this, the chosen
export workflow management approach should be used, and an environment must be set up that scales your workflow.

You can see the general `--help` information as follows:

.. code-block:: shell

    $ hydroflows --help

.. program-output:: hydroflows --help

As you can see, the `hydroflows` command has several subcommands. These are treated in later sections.
