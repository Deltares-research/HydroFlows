.. _add_own_methods:

Create a custom methods (advanced)
==================================

To define a custom method, the following steps are required:

1. Define the `input`, `output`, and `params` classes as subclasses of the :class:`~hydroflows.workflow.Parameters` class.
   This allows for type checking, validation, and referencing of the input, output, and parameters of the method.
2. Set the ``input``, ``output``, ``params``, and ``name`` attributes of the method class, which should be a subclass of the :class:`~hydroflows.workflow.Method` class.
3. Implement the ``__init__`` method to initialize the input, output, and params attributes.
4. Implement the ``_run`` method to define the logic of the method.
5. Register the method using entry points.

Using the ``Method.test_method()`` method on your initialized method, some basic tests are performed to check if the method complies with the HydroFlows framework.
Specifically, it tests if the ``input``, ``output``, and ``params`` fields are serializable and match the arguments of the ``__init__`` method.
It does not test if the method is correct, i.e., if the logic of the ``_run`` is valid and the output files are generated correctly.


Creating a basic method
-----------------------

A basic method is a method that generates a single output file based on a single input file.
The method can be repeated if the same wildcard is present both in the input and output files.

The following steps are required to define a basic method:

1. Define the `input`, `output`, and `params` classes as subclasses of the ``Parameters`` class as follows:
    - Ensure that the fields of all `input`, `output`, and `params` classes are **unique**.
    - The fields of the `input` and `output` classes should be of type `Path` or `None`.
    - To parse lists of integers, floats, strings, or paths, use the ``ListOfInt``, ``ListOfFloat``, ``ListOfStr``, or ``ListOfPath`` types to work with Snakemake.
    - Make sure the output directory (or filename) can be set by the user to allow for adding repeat wildcards and for flexibility in folder structure.
      Typically, the output directory is set as a parameter in the `params` class if multiple output files are generated.

2. Define the method class as a subclass of the ``Method`` class and set the `input`, `output`, `params`, and `names` attributes.
    - The `name` attribute should be set to a unique name for the method and is used to identify the method when run from CLI.
    - The `input`, `output`, and `params` attributes types should be set to get the correct type hints in the method class.

3. Implement the ``__init__`` method:
    - Ensure that the argument names match the field names of the `input`, `params`, and `output` fields.
    - Typically, the `input` and `params` are initialized first, after which the `output` is derived from these attributes.
    - Do not use the arguments of the ``__init__`` method directly; instead, assign them to the `input` and `params` attributes before using them.
    - Add any additional logic needed, such as setting default values or defining output files based on the input files and method knowledge.

4. Implement the ``_run`` method to define the logic of the method.
    - Note that the HydroFlows framework handles the creation of the output directory and checks on the input files.

Below is an example of a basic method that runs a dummy event with some model.

.. code-block:: python

    from pathlib import Path
    from typing import Literal
    from hydroflows.workflow import Method, Parameters

    class RunDummyEventInput(Parameters):
        """Input files for the RunDummyEvent method."""

        event_csv: Path
        """Event csv file"""

        settings_toml: Path
        """Model settings file"""

        model_exe: Path | None = None
        """Model executable, required if run_method is 'exe'"""

    class RunDummyEventOutput(Parameters):
        """Output files for the RunDummyEvent method."""

        model_out_nc: Path
        """Model output netcdf file"""

    class RunDummyEventParams(Parameters):
        """Parameters for the RunDummyEvent method."""

        run_method: Literal["exe", "docker"] = "exe"
        """How to run the model"""

        output_dir: Path
        """The output directory"""

        event_name: str
        """The event name"""

    class RunDummyEvent(Method):
        """Run an event with some model."""

        input: RunDummyEventInput
        output: RunDummyEventOutput
        params: RunDummyEventParams
        name = "run_dummy_event"

        def __init__(
            self,
            event_csv: Path,
            settings_toml: Path,
            output_dir: Path,
            event_name: str | None = None,
            model_exe: Path | None = None,
            **params,
        ):
            """Create a RunDummyEvent instance."""
            self.input = RunDummyEventInput(
                event_csv=event_csv, settings_toml=settings_toml, model_exe=model_exe
            )
            if event_name is None:
                event_name = self.input.event_csv.stem
            self.params = RunDummyEventParams(output_dir=output_dir, event_name=event_name, **params)
            if self.params.run_method == "exe" and model_exe is None:
                raise ValueError("Model executable is required for run_method 'exe'")
            self.output = RunDummyEventOutput(
                model_out_nc=self.params.output_dir / f"event_{event_name}_result.nc"
            )

        def _run(self):
            # Dummy run model and save output
            self.output.model_out_nc.touch()


Creating an expand method
-------------------------

An expand method is a method that generates multiple of the same output files based on a single input file.
This type of method has a wildcard in the output files but not in the input files.
This is useful when subsequent rules need to be executed for each of the output files.

Compared to a basic method, an expand method has the following additional attributes and methods:

- :meth:`~hydroflows.workflow.ExpandMethod.set_expand_wildcard`: This method sets the wildcard name and values that are used to expand the method.
- :meth:`~hydroflows.workflow.ExpandMethod.get_output_for_wildcards`: This method returns the output files for a specific wildcard value.
- :attr:`~hydroflows.workflow.ExpandMethod.expand_wildcards`: This attribute stores the wildcard name and values that are used to expand the method.
- :attr:`~hydroflows.workflow.ExpandMethod.output_expanded`: This attribute stores the output files for all wildcard values.

For the implementation of an expand method, the following additional requirements apply:

1. At least one of the output files should contain a wildcard in the file path and is typed as a `WildcardPath`.
   The `WildcardPath` type is a subclass of the `Path` type and is used to validate that the output file path contains a wildcard.

2. The method should be a subclass of the `ExpandMethod` class.

3. In the ``__init__`` method, the wildcard name and values should be set using the ``set_expand_wildcard`` method.

4. In the implementation of the ``_run`` method, the output file paths should be generated for each of the wildcard values, using the ``get_output_for_wildcards`` method.
   The `output` attribute should not be used directly for output files over which the expands, as these still contain the output file paths with wildcards.

Below is an example of an expand method that prepares events for some model.


.. code-block:: python

    from pathlib import Path
    from hydroflows._typing import ListOfInt, WildcardPath
    from hydroflows.workflow import ExpandMethod, Parameters

    class PrepareDummyEventsInput(Parameters):
        """Input files for the PrepareDummyEvents method."""

        timeseries_csv: Path
        """Input timeseries csv file"""

    class PrepareDummyEventsOutput(Parameters):
        """Output files for the PrepareDummyEvents method."""

        event_csv: WildcardPath  # this output is expanded
        """Event csv file"""

        event_set_yaml: Path
        """Overview of all events"""

    class PrepareDummyEventsParams(Parameters):
        """Parameters for the PrepareDummyEvents method."""

        output_dir: Path
        """Output directory"""

        index_col: int = 0
        """Index column"""

        wildcard: str = "return_period"
        """Wildcard for expanding"""

        rps: ListOfInt = [1, 10, 100, 1000]
        """Return periods [years]"""

    class PrepareDummyEvents(ExpandMethod):
        """Prepare events for some model."""

        input: PrepareDummyEventsInput
        output: PrepareDummyEventsOutput
        params: PrepareDummyEventsParams
        name = "prepare_dummy_events"

        def __init__(
            self,
            timeseries_csv: Path,
            output_dir: Path,
            rps: list[int] = [1, 10, 100, 1000],  # noqa: B006
            **params,
        ):
            self.input = PrepareDummyEventsInput(timeseries_csv=timeseries_csv)
            self.params = PrepareDummyEventsParams(output_dir=output_dir, rps=rps, **params)
            wc = "{" + self.params.wildcard + "}"
            self.output = PrepareDummyEventsOutput(
                event_csv=self.params.output_dir / f"event_rp{wc}.csv",
                event_set_yaml=self.params.output_dir / "event_set.yml",
            )

            self.set_expand_wildcard(self.params.wildcard, [f"{rp:04d}" for rp in self.params.rps])

        def _run(self):
            # Read the data
            # Save the outputs
            for rp in self.params.rps:
                # Do some processing per return period
                # Save the event
                output = self.get_output_for_wildcards({self.params.wildcard: f"{rp:04d}"})
                output["event_csv"].touch()
            # Save the event set
            self.output.event_set_yaml.touch()


Creating a reduce method
------------------------

A reduce method is a method that generates a single output file based on multiple of the same input files.
This type of method has a wildcard in the input files which does not appear in the output files.
Compared to a basic method, a reduce method has no additional attributes or methods, but for the implementation of a reduce method, the following requirements apply:

1. At least one of the input files should contain a wildcard in the file path and is typed as a ``WildcardPath | ListOfPath``.
   The ``WildcardPath`` type is a subclass of the ``Path`` type and is used to validate that the input file path contains a wildcard.
   This field will contain a wildcard in the file path at validation, but the wildcard will be replaced by the actual list of file paths at runtime.

2. The method should be a subclass of the ``ReduceMethod`` class.

Below is an example of a reduce method that combines events for some model.


.. code-block:: python

    from pathlib import Path
    from hydroflows._typing import ListOfPath, WildcardPath
    from hydroflows.workflow import Parameters, ReduceMethod

    class CombineDummyEventsInput(Parameters):
        """Input files for the CombineDummyEvents method."""

        model_out_ncs: ListOfPath | WildcardPath
        """Model output netcdf files"""

    class CombineDummyEventsOutput(Parameters):
        """Output files for the CombineDummyEvents method."""

        combined_out_nc: Path
        """Combined model output netcdf file"""

    class CombineDummyEventsParams(Parameters):
        """Parameters for the CombineDummyEvents method."""

        output_dir: Path | None = None
        """Output directory"""

    class CombineDummyEvents(ReduceMethod):
        """Combine the model outputs for all events."""

        input: CombineDummyEventsInput
        output: CombineDummyEventsOutput
        params: CombineDummyEventsParams
        name = "combine_dummy_events"

        def __init__(
            self,
            model_out_ncs: ListOfPath | WildcardPath,
            output_dir: Path | None = None,
            **params,
        ):
            """Create a CombineDummyEvents instance.

            Parameters
            ----------
            model_out_ncs : List[Path] | WildcardPath
                List of model output netcdf files or a wildcard path
            output_dir : Path, optional
                The output directory, by default None
            **params
                Additional parameters to pass to the CombineDummyEvents Params instance.
                See :py:class:`~hydroflows.methods.dummy.CombineDummyEvents
            """
            self.params = CombineDummyEventsParams(output_dir=output_dir, **params)
            self.input = CombineDummyEventsInput(model_out_ncs=model_out_ncs)
            self.output = CombineDummyEventsOutput(
                combined_out_nc=self.params.output_dir / "events_combined.nc"
            )

        def _run(self):
            # Combine the model outputs
            self.output.combined_out_nc.touch()


Registering the method
----------------------

To use the method in a workflow, the method should be registered using entry points.
The entry point should be defined in the `hydoflows.methods` group and should point to a dictionary
with the method name as key and the method entrypoint as value, as shown below.

The following code should be part of your package:

.. code-block:: python

    MY_METHODS = {
        "combine_dummy_events": "hydroflows.methods.dummy.combine_dummy_events:CombineDummyEvents",
        "prepare_dummy_events": "hydroflows.methods.dummy.prepare_dummy_events:PrepareDummyEvents",
        "run_dummy_event":  "hydroflows.methods.dummy.run_dummy_event:RunDummyEvent",
        "postprocess_dummy_event": "hydroflows.methods.dummy.postprocess_dummy_event:PostprocessDummyEvent",
    }


The entry point should be defined in the `pyproject.toml` file as follows:

.. code-block:: toml

    [project.entry-points."hydroflows.methods"]
    my_methods = "my_package.my_module:MY_METHODS"


.. Note::
    This approach might change in the future, as the HydroFlows framework is still under development.
