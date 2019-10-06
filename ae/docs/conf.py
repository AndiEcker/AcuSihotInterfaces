# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# http://www.sphinx-doc.org/en/master/config

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import sys
from ae.setup import package_name, package_version

# -- Project information -----------------------------------------------------

project = 'python application environment'
# copyright = '2019, Andi Ecker'
author = 'Andi Ecker'
version = package_version

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    # 'sphinx.ext.autodoc',     # automatically added by autosummary
    'sphinx.ext.autosummary',
    'sphinx.ext.viewcode',  # include package module source code
    'sphinx.ext.intersphinx',
    # typehints extension does that already so no need to also include 'sphinx_autodoc_annotation',
    'sphinx_autodoc_typehints',
    # 'sphinx.ext.coverage',
    # 'sphinx.ext.graphviz',
    'sphinx_rtd_theme',
    'sphinx_paramlinks',
]
if package_name == 'ae_sys_data':
    extensions.append('sphinx.ext.graphviz')

# -- autodoc config
autodoc_default_options = {
    'members': True,
    'member-order': 'bysource',
    'private-members': True,
    'special-members': True,
    'undoc-members': True,
    'show-inheritance': True,
    'exclude-members': '__weakref__, __dict__, __module__',
    'autosummary_generate': True,
}

autosummary_generate = True
add_module_names = False
add_function_parentheses = True

# Add any paths that contain templates here, relative to this directory.
# templates_path = ['_templates', '_templates/autosummary']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
# exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# Example configuration for intersphinx: refer to the Python standard library
# - found at https://www.mankier.com/1/sphinx-all and https://github.com/traverseda/pycraft/blob/master/docs/conf.py.
# intersphinx_mapping = {'https://docs.python.org/3.6': None}
intersphinx_mapping = {
    'python': ('https://docs.python.org/' + '.'.join(map(str, sys.version_info[0:2])), None)
}

# -- Options for HTML output -------------------------------------------------º

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = 'sphinx_rtd_theme'  # 'alabaster'

# NEXT TWO VARIABLES TAKEN FROM https://github.com/romanvm/sphinx_tutorial/blob/master/docs/conf.py
# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
# alabaster theme options - DON'T WORK WITH sphinx_rtd_theme!!!
if html_theme == 'alabaster':
    html_theme_options = {
        'gitlab_button': True,
        'gitlab_type': 'star&v=2',  # use v2 button
        'gitlab_user': 'AndiEcker',
        'gitlab_repo': package_name,
        'gitlab_banner': True,
    }

    # Custom sidebar templates, maps document names to template names.
    # Sidebars configuration for alabaster theme
    html_sidebars = {
        '**': [
            'about.html',
            'navigation.html',
            'searchbox.html',
        ]
    }

elif html_theme == 'sphinx_rtd_theme':
    html_theme = "sphinx_rtd_theme"
    html_theme_path = ["_themes", ]
    html_theme_options = {
        'collapse_navigation': False,
        'prev_next_buttons_location': 'both',
        'style_external_links': False,
    }

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
# html_static_path = ['_static']
