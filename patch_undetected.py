# patch_undetected.py
import re
from pathlib import Path
import undetected_chromedriver

def patch_undetected():
    """
    Replaces 'from distutils.version import LooseVersion' with
    'from packaging.version import Version as LooseVersion' in undetected_chromedriver's patcher.py.
    This removes the dependency on distutils which is missing in Python 3.12+.
    """
    base_dir = Path(undetected_chromedriver.__file__).parent
    patcher_path = base_dir / "patcher.py"
    text = patcher_path.read_text()
    # Replace the import line for distutils.version
    text = re.sub(
        r"from distutils\.version import LooseVersion",
        "from packaging.version import Version as LooseVersion",
        text
    )
    patcher_path.write_text(text)
    print("Patched undetected_chromedriver to remove distutils usage.")

if __name__ == "__main__":
    patch_undetected()
