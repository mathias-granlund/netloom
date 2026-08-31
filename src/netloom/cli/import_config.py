from __future__ import annotations

import sys

from netloom.core import import_config as _import_config

sys.modules[__name__] = _import_config
