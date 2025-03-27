"""Some utils for running containers."""
import os
import sys
from typing import Tuple, Union

try:
    import pwd
except ImportError:
    pass

__all__ = ["fetch_docker_uid"]


def fetch_docker_uid() -> Tuple[Union[str, None], Union[str, None]]:
    """Fetch uid to use in docker run cmd.

    Returns
    -------
    Union[Tuple[str,str], None]
        returns uid,gid tuple or None depending on whether pwd package exists.
    """
    if "pwd" not in sys.modules:
        return (None, None)
    else:
        uid = os.getuid()
        user = pwd.getpwuid(uid)
        gid = user.pw_gid
        return (uid, gid)
