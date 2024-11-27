"""Logging module of HydroFlows."""
import logging
import logging.handlers
import os

from hydroflows import __version__

FMT = "%(levelname)s - %(module)s - %(message)s"


def setuplog(
    path: str = None,
    level: int = 20,
    fmt: str = FMT,
    append: bool = False,
) -> logging.Logger:
    """Create the logging on sys.stdout and file if path is given.

    Parameters
    ----------
    name : str, optional
        logger name, by default "hydromt"
    path : str, optional
        path to logfile, by default None
    level : int, optional
        Log level [0-50], by default 20 (info)
    fmt : str, optional
        log message formatter, by default FMT
    append : bool, optional
        Wether to append (True) or overwrite (False) to a logfile at path, \
by default True

    Returns
    -------
    logging.Logger
        _description_
    """
    logger = logging.getLogger(__package__)
    for _ in range(len(logger.handlers)):
        logger.handlers.pop().close()  # remove and close existing handlers
    logging.captureWarnings(True)
    logging.basicConfig(level=level, format=FMT)
    if path is not None:
        if append is False and os.path.isfile(path):
            os.unlink(path)
        add_filehandler(logger, path, level=level, fmt=fmt)
    logger.info(f"hydroflows version: {__version__}")
    return logger


def add_filehandler(logger, path, level=20, fmt=FMT):
    """Add file handler to logger."""
    if not os.path.isdir(os.path.dirname(path)):
        os.makedirs(os.path.dirname(path))
    isfile = os.path.isfile(path)
    ch = logging.FileHandler(path)
    ch.setFormatter(logging.Formatter(fmt))
    ch.setLevel(level)
    logger.addHandler(ch)
    if isfile:
        logger.debug(f"Appending log messages to file {path}.")
    else:
        logger.debug(f"Writing log messages to new file {path}.")
