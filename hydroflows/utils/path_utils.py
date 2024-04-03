"""Utils for model path operations."""

import os
from os.path import isfile, join


def make_relative_paths(config, model_root, new_root):
    """Return dict with paths to the new model new root."""
    config_kwargs = dict()
    commonpath = ''
    if os.path.splitdrive(model_root)[0] == os.path.splitdrive(new_root)[0]:
        commonpath = os.path.commonpath([model_root, new_root])
    if os.path.basename(commonpath) == '':
        raise ValueError("model_root and new_root must have a common path")
    relpath = os.path.relpath(commonpath, new_root)
    for k, v in config.items():
        if (
            isinstance(v, str) and
            isfile(join(model_root, v)) and
             not isfile((join(new_root, v)))
        ):
            config_kwargs[k] = join(relpath, v)
    return config_kwargs
