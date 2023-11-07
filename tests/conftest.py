# fixtures with input and output files and folders
import pytest
import shutil

@pytest.fixture
def root_folder():
    folder = "example_domain"
    yield folder
    shutil.rmtree(folder)


