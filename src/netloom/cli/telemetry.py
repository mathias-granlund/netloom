from __future__ import annotations

import sys

from netloom.core import telemetry as _telemetry

sys.modules[__name__] = _telemetry
