"""
Test harness guardrail.

Some Python environments have globally installed pytest plugins that can break
this project's test runs due to unrelated dependency conflicts.

Setting PYTEST_DISABLE_PLUGIN_AUTOLOAD prevents pytest from auto-loading
third-party plugins via setuptools entry points.
"""

import os

# Disable auto-loading of globally installed pytest plugins.
# This keeps this repo's tests isolated from unrelated, system-wide plugins.
os.environ.setdefault("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")

