from __future__ import annotations

import sys

from netloom.core import diff as _diff

sys.modules[__name__] = _diff
