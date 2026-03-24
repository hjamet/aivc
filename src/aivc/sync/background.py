"""
BackgroundSyncer: Daemon thread to pull commits periodically (or at startup).
"""

import threading
import time
from pathlib import Path
from aivc.sync.sync import RcloneSyncManager

class BackgroundSyncer:
    """Daemon responsible for pulling distant commits at startup and potentially periodically."""
    
    def __init__(self, storage_root: Path):
        self.manager = RcloneSyncManager(storage_root)
        self._stop_event = threading.Event()
        self._thread = None

    def start(self):
        """Start the background pull thread."""
        if not self.manager.enabled:
            return
            
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self):
        """Single pull at startup (as requested in Phase 20)."""
        try:
            self.manager.pull_commits_from_others()
        except Exception as e:
            import sys
            print(f"Background pull failed: {e}", file=sys.stderr)

    def stop(self):
        """Stop the syncer."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2)
