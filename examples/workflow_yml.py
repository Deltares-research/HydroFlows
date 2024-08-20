"""Example of the Workflow class for two yml workflow examples."""
# %% Importing the Workflow class
from hydroflows import Workflow

# %% Create a workflow from a YAML file
wf_name = "sfincs_pluvial"
# wf_name = "sfincs_pluvial_regions"
wf = Workflow.from_yaml(f"{wf_name}.yml")
print(wf)

# %% Test the workflow
wf.run(dryrun=True)

# %% Write the workflow to a Snakefile
wf.to_snakemake(f"{wf_name}.smk")

# %%
