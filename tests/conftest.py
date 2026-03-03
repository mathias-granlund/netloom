import sys
import types

# Ensure importing arapy.main doesn't fail if arapy.gui isn't present.
if "arapy.gui" not in sys.modules:
    m = types.ModuleType("arapy.gui")
    def run_gui():
        raise RuntimeError("GUI not available in unit test environment")
    m.run_gui = run_gui
    sys.modules["arapy.gui"] = m
