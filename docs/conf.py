# -*- coding: utf-8 -*-
#
# HydroFlows documentation build configuration file, created by
# sphinx-quickstart on Tue Jun 11 15:19:00 2024.
#
# This file is execfile()d with the current directory set to its
# containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#

# -- Project information -----------------------------------------------------

project = "HydroFlows"
copyright = "Deltares"
author = "Deltares"

# -- General configuration ------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#
# needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "sphinx_design",
    "sphinx.ext.autodoc",
    "sphinx.ext.viewcode",
    "sphinx.ext.todo",
    "sphinx.ext.napoleon",
    "sphinx.ext.autosummary",
    "sphinx.ext.githubpages",
    "sphinx.ext.intersphinx",
    # "IPython.sphinxext.ipython_directive",
    # "IPython.sphinxext.ipython_console_highlighting",
    "sphinxcontrib.autodoc_pydantic",
    "sphinxcontrib.programoutput",
    # "nbsphinx",
]

autosummary_generate = True
# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]
# The suffix(es) of source filenames.
# You can specify multiple suffix as a list of string:
#
# source_suffix = ['.rst', '.md']
source_suffix = ".rst"
# The master toctree document.
master_doc = "index"

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#
# This is also used if you do content translation via gettext catalogs.
# Usually you set "language" from the command line for these cases.
language = "en"

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This patterns also effect to html_static_path and html_extra_path
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = "sphinx"

# If true, `todo` and `todoList` produce output, else they produce nothing.
todo_include_todos = False


# -- Options for HTML output ----------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "pydata_sphinx_theme"
html_logo = "_static/hydromt-icon.svg"
html_favicon = "_static/hydromt-icon.svg"
autodoc_member_order = "bysource"  # overwrite default alphabetical sort
autoclass_content = "both"

# -- Options for autodoc_pydantic ------------------------------------------
autodoc_pydantic_model_show_json = False
autodoc_pydantic_model_show_config_summary = False
autodoc_pydantic_model_show_validator_members = False

autodoc_pydantic_model_show_validator_summary = False
autodoc_pydantic_model_show_config_summary = False
autodoc_pydantic_model_members = True
autodoc_pydantic_field_list_validators = False
autodoc_pydantic_field_show_constraints = False

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]
html_css_files = ["theme-deltares.css"]
html_theme_options = {
    "show_nav_level": 2,
    "navbar_align": "content",
    "use_edit_page_button": True,
    "icon_links": [
        {
            "name": "GitHub",
            "url": "https://github.com/Deltares-research/HydroFlows",  # required
            "icon": "fab fa-github",
            "type": "fontawesome",
        },
        {
            "name": "Deltares",
            "url": "https://www.deltares.nl/en/",
            "icon": "_static/deltares-blue.svg",
            "type": "local",
        },
    ],
    "logo": {
        "text": "HydroFlows",
    },
    "navbar_end": ["navbar-icon-links"],  # remove dark mode switch
}

html_context = {
    "github_url": "https://github.com",  # or your GitHub Enterprise interprise
    "github_user": "Deltares",
    "github_repo": "HydroFlows",
    "github_version": "main",  # FIXME
    "doc_path": "docs",
    "default_mode": "light",
}

remove_from_toctrees = ["_generated/*"]

# -- Options for HTMLHelp output ------------------------------------------

# Output file base name for HTML help builder.
htmlhelp_basename = "hydroflows_doc"

# -- INTERSPHINX -----------------------------------------------------------

intersphinx_mapping = {
    "python": ("https://docs.python.org/3/", None),
    "pandas": ("https://pandas.pydata.org/pandas-docs/stable", None),
    # "numpy": ("https://numpy.org/doc/stable", None),
    "scipy": ("https://docs.scipy.org/doc/scipy", None),
    # "numba": ("https://numba.pydata.org/numba-doc/latest", None),
    # "matplotlib": ("https://matplotlib.org/stable/", None),
    # "dask": ("https://docs.dask.org/en/latest", None),
    "rasterio": ("https://rasterio.readthedocs.io/en/latest", None),
    "geopandas": ("https://geopandas.org/en/stable", None),
    "xarray": ("https://xarray.pydata.org/en/stable", None),
    "hydromt": ("https://deltares.github.io/hydromt/latest/", None),
    "hydromt_wflow": ("https://deltares.github.io/hydromt_wflow/latest/", None),
    "hydromt_sfincs": ("https://deltares.github.io/hydromt_sfincs/latest/", None),
    "hydromt_fiat": ("https://deltares.github.io/hydromt_fiat/latest/", None),
}
