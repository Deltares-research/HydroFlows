# tests typical input/output related things
from pathlib import Path
from hydroflows.templates import create_folders


def test_create_folders(tmpdir):
    # FIXME: this test is not complete
    # test if deepest folder is created
    root_folder = Path(tmpdir, "test")
    create_folders(root_folder)
    assert root_folder.exists()
