"""Configuration file for the Sphinx documentation builder.

For the full list of built-in configuration values, see the documentation:
https://www.sphinx-doc.org/en/master/usage/configuration.html
"""

from importlib.metadata import version as _version

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'MASAFI Sim Petri'
copyright = '2026, Jaume Figueras'
author = 'Jaume Figueras'

# Single source of truth: the installed distribution metadata, which setuptools
# fills in from ``pyproject.toml``. Building the docs therefore requires the
# package to be installed (``pip install -e ".[docs]"``).
release = _version('masafi-sim-petri')
version = '.'.join(release.split('.')[:2])

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.ext.apidoc',
    'sphinx.ext.doctest',
    'sphinx.ext.viewcode',
]

templates_path = ['_templates']
exclude_patterns = []

# -- API generation ----------------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/extensions/apidoc.html
#
# The ``api/`` stubs are regenerated on every build and are not tracked in git.

apidoc_modules = [
    {
        'path': '../../src/masafi_sim_petri',
        'destination': 'api',
        'separate_modules': True,
        'automodule_options': {'members', 'undoc-members', 'show-inheritance'},
    },
]

# -- autodoc -----------------------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/extensions/autodoc.html

autodoc_member_order = 'bysource'
# The package ``__init__`` files re-export the public API. Without
# 'ignore-module-all' autodoc follows their ``__all__`` and documents e.g.
# ``Place`` under both ``masafi_sim_petri`` and
# ``masafi_sim_petri.petri_net.place``, which Sphinx reports as a duplicate
# object description. Each class is documented once, in the module that
# defines it.
autodoc_default_options = {
    'ignore-module-all': True,
}
# Types stay in the rendered signature. NumPy-style docstrings already spell
# the types out in their ``Parameters`` section, so moving annotations into the
# description would render every parameter type twice.
autodoc_typehints = 'signature'

# -- napoleon ----------------------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/extensions/napoleon.html
#
# NumPy syntax only: Google-style parsing is off so that a malformed NumPy
# docstring fails loudly instead of being silently reinterpreted.

napoleon_numpy_docstring = True
napoleon_google_docstring = False
napoleon_include_init_with_doc = True
napoleon_use_rtype = True

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']
