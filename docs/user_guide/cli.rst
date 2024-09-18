.. _ug_cli:

Command-line interface
----------------------

The command line interface is meant to provide an easy, reproducible and streamlined approach to generate
simple workflows from the existing set of methods available in HydroFlows, and export these to a language of choice.
Setting up complex workflows with multiple wildcard permutations is not recommended with the CLI.
The CLI can also run a workflow, but is not meant to run these workflows at scale (i.e. using multiple process or HPC).
For this, the workflow should be exported to a language of choice (e.g. Snakemake) and run within the chosen scalable
environment using the language-specific options for scaling. For instance, Snakemake has many options to instruct
running rules on nodes within an HPC.

You can see the general `--help` information as follows:

.. code-block:: shell

    $ hydroflows --help

.. program-output:: hydroflows --help

As you can see, the `hydroflows` command has several subcommands. These are treated in later sections.
