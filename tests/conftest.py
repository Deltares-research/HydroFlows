# fixtures with input and output files and folders

from pathlib import Path

import pytest

from hydroflows.workflows.events import EventCatalog


@pytest.fixture()
def tmp_csv(tmpdir):
    """Create a temporary csv file."""
    csv_file = tmpdir.join('file.csv')
    csv_file.write('')
    return csv_file

@pytest.fixture(scope='session')
def test_data_dir() -> Path:
    return Path(__file__).parent / 'data'

@pytest.fixture()
def event_catalog(test_data_dir) -> EventCatalog:
    return EventCatalog.from_yaml(test_data_dir / 'events.yml')
