"""
Centralized configuration management for AIVC.
"""

import os
import sys
from pathlib import Path

_STORAGE_ROOT_ENV = "AIVC_STORAGE_ROOT"

def get_storage_root(allow_fallback: bool = False) -> Path:
    """Retrieve and validate the AIVC storage root directory.

    Args:
        allow_fallback: If True, defaults to ~/.aivc/storage if the env var is missing.
                        If False, exits the process (or raises ValueError).

    Returns:
        Path object pointing to the storage root.

    Raises:
        ValueError: If AIVC_STORAGE_ROOT is not set and allow_fallback is False
                    (only when not running in a CLI-like exit context).
    """
    path_str = os.environ.get(_STORAGE_ROOT_ENV)
    
    if not path_str:
        if allow_fallback:
            path = Path.home() / ".aivc" / "storage"
            return path
        else:
            # For CLI and Server, we want a hard exit with a clear message.
            print(
                f"\033[31m[aivc] ERROR:\033[0m Environment variable {_STORAGE_ROOT_ENV!r} is not set.\n"
                "Cannot proceed. Please run install.sh or export the variable.",
                file=sys.stderr
            )
            sys.exit(1)
            
    return Path(path_str)
