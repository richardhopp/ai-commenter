# patch_undetected.py

import re
from pathlib import Path
import undetected_chromedriver

def patch_undetected():
    """
    Instead of rewriting the file (which can cause permission errors), 
    we patch the module in memory by overriding the LooseVersion attribute.
    """
    try:
        import undetected_chromedriver.patcher as patcher
        from packaging.version import Version as LooseVersion
        patcher.LooseVersion = LooseVersion
        print("Patched undetected_chromedriver.patcher in memory to use packaging.version.")
    except Exception as e:
        print("Error patching undetected_chromedriver in memory:", e)

def patch_setuptools():
    import importlib.util
    spec = importlib.util.find_spec("setuptools")
    if spec is None:
        print("Warning: setuptools module not found.")
    else:
        print("setuptools found.")

if __name__ == "__main__":
    patch_setuptools()
    patch_undetected()
