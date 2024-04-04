import pytest

from hydroflows.methods._validators import ParamsHydromt


@pytest.mark.parametrize(
    ("data_libs", "data_libs_list"),
    [
        ("", []),
        (["a", "b"], ["a", "b"]),
        ("a,b, c", ["a", "b", "c"]),
        ("a", ["a"]),
        ("a b", ["a", "b"]),
        ("a, 'b'", ["a", "b"]),
        # comma seperated, comma and space in quotes
        ("a, 'a/b/, c.yml'", ["a", "a/b/, c.yml"]),
        # space seperated, comma and space in quotes
        ("a 'a/b/, c.yml'", ["a", "a/b/, c.yml"]),
    ],

)
def test_hydromt_params(data_libs, data_libs_list):
    """Test ParamsHydromt."""
    params = ParamsHydromt(data_libs=data_libs)
    assert params.data_libs == data_libs_list
