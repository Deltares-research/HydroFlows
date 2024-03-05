# tests typical input/output related things
import os
import hydroflows


def test_create_folders(root_folder):

    # test if deepest folder is created
    hydroflows.create_folders(root_folder)
    assert(os.path.isdir(root_folder))
