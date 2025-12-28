"""User interface modules.

The CLI is invoked directly via: python -m src.interface.cli
Importing here would cause RuntimeWarning when running as module.
"""

# Don't import cli module at package level to avoid:
# RuntimeWarning: 'src.interface.cli' found in sys.modules
