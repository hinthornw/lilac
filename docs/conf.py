"""Configuration for sphinx."""
# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'Lilac'
copyright = '2023, Lilac AI Inc.'
author = 'Lilac AI Inc.'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
  'sphinx.ext.napoleon',  # support for Google and NumPy style docstrings.
  'sphinx.ext.autodoc',
  'sphinx.ext.coverage',
  'sphinx.ext.autodoc.typehints',
  'sphinx.ext.autosummary',
  'sphinxcontrib.autodoc_pydantic',
  'myst_parser',
  'enum_tools.autoenum',
]

myst_enable_extensions = ['attrs_block', 'attrs_inline']
myst_heading_anchors = 3

autodoc_pydantic_model_show_json = False
autodoc_pydantic_field_list_validators = False
autodoc_pydantic_config_members = False
autodoc_pydantic_model_show_field_summary = False
autodoc_pydantic_model_show_config_summary = False
autodoc_pydantic_model_show_validator_members = False
autodoc_pydantic_model_show_validator_summary = False
autodoc_pydantic_model_signature_prefix = 'class'
autodoc_pydantic_field_signature_prefix = 'param'
autodoc_typehints_format = 'short'

templates_path = ['_templates']
exclude_patterns = [
  '_build',
  'Thumbs.db',
  '.DS_Store',
  '.venv',
  'README.md',
  '.github/*',
]

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'furo'
html_theme_options = {
  'source_repository': 'https://github.com/lilacai/lilac',
  'source_branch': 'main',
  'source_directory': 'docs/',
  'footer_icons': [{
    'name': 'GitHub',
    'url': 'https://github.com/lilacai/lilac',
    'html': """
                <svg stroke="currentColor" fill="currentColor" stroke-width="0" viewBox="0 0 16 16">
                    <path fill-rule="evenodd" d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0 0 16 8c0-4.42-3.58-8-8-8z"></path>
                </svg>
            """,
    'class': '',
  },],
}
html_title = '🌸 Lilac'
html_static_path = ['_static']
html_css_files = ['styles/custom.css']
html_js_files = ['custom.js']
html_favicon = '../web/blueprint/static/favicon.ico'
