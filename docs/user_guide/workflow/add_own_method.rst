.. _add_own_methods:

Add your own methods
=====================

Simple scripts can directly be added to a workflow using the `ScriptMethod` method, however this does not provide any validation of the input, output, or parameters.
To develop your own methods which do get validated, users should use the HydroFlows `Method` class.
This class uses the `pydantic`_ library to validate the `input`, `output`, and `params` of the method.
Users need to subclass the `Method` class and define the `input`, `output`, and `params` of the method as pydantic models.
Each method should also have a `run` method where the actual processing is done.
For more information on how to create your own methods, see the :ref:`add_own_methods` section.
