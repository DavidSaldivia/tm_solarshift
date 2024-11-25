# Configuration file for the Sphinx documentation builder.

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'Solarshift'
copyright = '2024, David Saldivia S.'
author = 'David Saldivia S.'
release = '0.1.0'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'sphinx.ext.duration',
    'sphinx.ext.doctest',
    "sphinx.ext.napoleon",
    'sphinx.ext.autodoc',
    'sphinx.ext.autosummary',
]

templates_path = ['_templates']
exclude_patterns = []


# --  Napoleon options--------------------------------------------------------
# use the :param directive
napoleon_use_param = True
napoleon_attr_attributes = True

# -- Autodoc options ---------------------------------------------------------

# Automatically extract typehints when specified and place them in
# descriptions of the relevant function/method.
autodoc_typehints = "both"

# Only insert class docstring
autoclass_content = "class"

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'bizstyle'
html_static_path = ['_static']
