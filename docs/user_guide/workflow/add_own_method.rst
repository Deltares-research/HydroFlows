.. _add_own_methods:

Defining custom methods (advanced)
==================================

A method is a python class that inherits from the :class:`~hydroflows.workflow.Method` class.
The input, output and params attributes should inherit from the the :class:`~hydroflows.workflow.Parameters` class which is a subclass of the `pydantic.BaseModel` class.

To define a custom method, the following attributes and methods need to be defined:

- `input`: all input files (should be of type `Path`). Optional input files can be defined as `None`.
- `output`: all output files (should be of type `Path`). Optional output files can be defined as `None`.
- `params`: method parameters (can be of any serializable type) with default values if applicable.
- `__init__`: initialization method that defines the output files based on the input files and params.
- `run`: method execution method that generates the output files based on the input files and params. This is where the intelligence of the method is defined.
