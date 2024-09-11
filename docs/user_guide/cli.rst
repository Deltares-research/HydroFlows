.. _ug_cli:

Command-line interface
----------------------

The command line interface is meant to provide an easy, reproducible and streamlined approach to generate
simple workflows from the existing set of methods available in HydroFlows, and export these to a language of choice.
Complex workflows with multiple wildcard permutations are not recommended to create with CLI in mind.
The CLI can also run a workflow, but is not meant to run these workflows at scale (i.e. using multiple process or HPC).
For this, the chosen export workflow management approach should be used, and an environment must be set up that
scales your workflow.

You can see the general `--help` information as follows:

.. code-block:: shell

    $ hydroflows --help

.. program-output:: hydroflows --help

As you can see, the `hydroflows` command has several subcommands. These are treated in later sections.
