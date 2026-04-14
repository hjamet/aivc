"""
BackgroundSyncer: Daemon thread to pull commits periodically (or at startup).
"""

import sys
import threading
from pathlib import Path
from aivc.sync.drive import NativeDriveSyncManager

class BackgroundSyncer:
    """Daemon responsible for pulling distant commits at startup and potentially periodically."""
    
    def __init__(self, storage_root: Path):
        self.manager = NativeDriveSyncManager(storage_root)
        self._stop_event = threading.Event()
        self._thread = None

    def start(self):
        """Start the background pull thread."""
        if not self.manager.enabled:
            return
            
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self):
        """Sync pulls and pushes at startup."""
        try:
            # 1. Pull from others
            self.manager.pull_memories_from_others()

            # 2. Push missing local memories
            stats = self.manager.push_missing()
            pushed = stats.get("memories_pushed", 0)
            if pushed > 0:
                print(f"[AIVC Sync] Auto-pushed {pushed} local memories to Drive.", file=sys.stderr)

        except Exception as e:
            import sys
            print(f"Background sync failed: {e}", file=sys.stderr)

    def stop(self):
        """Stop the syncer."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2)
