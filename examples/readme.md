## How to run an example

### create and run a snakemake workflow

**General steps:**

1. `cd` to the workflow directory
2. `hydroflows create <workflow>.yml`
3. `snakemake -s <workflow>.smk -c <n_cores>`

**Example CLI:**

```bash
hydroflows create sfincs_pluvial.yaml
snakemake -s sfincs_pluvial.smk -n # dry run as we don't have the sfincs model
```

**Example create snakemake workflow Python API**

```python
from hydroflows import Workflow

workflow = Workflow('sfincs_pluvial.yaml')
workflow.to_snakemake('sfincs_pluvial.smk')
```

## run a workflows with hydroflows

**Example CLI**

```bash
hydroflows run sfincs_pluvial.yaml
```

**Example Python API**

```python
from hydroflows import Workflow

workflow = Workflow('sfincs_pluvial.yaml')
workflow.run()
```
