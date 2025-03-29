# patch_undetected.py
import os
import re
from pathlib import Path

def patch_undetected():
    import undetected_chromedriver
    base_dir = Path(undetected_chromedriver.__file__).parent
    patcher_path = base_dir / "patcher.py"
    text = patcher_path.read_text()

    # Replace 'from distutils.version import LooseVersion' with packaging
    text = re.sub(r"from distutils\.version import LooseVersion",
                  "from packaging.version import Version as LooseVersion",
                  text)

    # Also replace 'LooseVersion(...)' calls if needed
    # Usually a direct rename is enough if 'LooseVersion(...)' is used like a function

    patcher_path.write_text(text)
    print("Patched undetected_chromedriver to remove distutils usage.")

if __name__ == "__main__":
    patch_undetected()
