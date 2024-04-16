# large test data

Large test data is not included in the repository. It is stored as artifact data to the [test-data release](https://github.com/Deltares-research/HydroFlows/releases/tag/test-data) on GitHub. The large test data is downloaded automatically using fixtures when running the tests and stored in the `tests/_remote_data/data` directory. This directory is ignored by git.

## update large test data

To update the large test data, first make sure that the `tests/_remote_data/data` directory is up to date. You can do this by running:

```bash
python fetch_remote_data.py
```

Then, you can modify and/or add data to the `tests/_remote_data/data` directory.
After that, create a new `tests/_remote_data/registry.txt` file by running:

```bash
python make_registry.py
```

Finally, update the added/modified data, including the registry.txt file in the artifact data of the [test-data release](https://github.com/Deltares-research/HydroFlows/releases/tag/test-data).
This can be done by pressing the "Edit" button on the release page and uploading the new data.
