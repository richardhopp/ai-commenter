# patch_undetected.py

import re
from pathlib import Path
import undetected_chromedriver

def patch_undetected():
    """
    Replaces 'from distutils.version import LooseVersion' with
    'from packaging.version import Version as LooseVersion' in undetected_chromedriver's patcher.py.
    """
    base_dir = Path(undetected_chromedriver.__file__).parent
    patcher_path = base_dir / "patcher.py"
    text = patcher_path.read_text()
    text = re.sub(
        r"from distutils\.version import LooseVersion",
        "from packaging.version import Version as LooseVersion",
        text
    )
    patcher_path.write_text(text)
    print("Patched undetected_chromedriver to remove distutils usage.")

def patch_setuptools():
    """
    Check if setuptools is available. If not, print a warning.
    """
    import importlib.util
    spec = importlib.util.find_spec("setuptools")
    if spec is None:
        print("Warning: setuptools module not found.")
    else:
        print("setuptools found.")

if __name__ == "__main__":
    patch_setuptools()
    patch_undetected()
