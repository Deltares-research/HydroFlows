## How to run an example

### create and run a snakemake workflow

**General steps:**

```bash
hydroflows create <workflow>.yaml
snakemake -s <workflow>.smk -c <n_cores>
```

**Example:**

```bash
hydroflows create examples/sfincs_pluvial.yaml
snakemake -s examples/sfincs_pluvial.smk -n # dry run as we don't have the sfincs model
```
