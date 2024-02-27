"""This script contains the Rule class, which is the main class for
defining rules in HydroFlows. A rule the basic unit in a workflow 
and should have a name, inputs, and outputs, and optionally params.
The goal of the Rule class is to validate these and hold the intelligence 
for running the rule. 

All HydroFlow rules should inherit from this class and implement specific
validators and a run method.

Later we may want to add common methods to parse rules to certain formats, e.g. smk, or cwl.
"""