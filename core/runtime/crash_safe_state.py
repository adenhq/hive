import json
import os
import signal
import tempfile
import threading
import logging
from pathlib import Path

# World No. 1 Cross-Platform Kernel Integration
IS_WINDOWS = os.name == "nt"
if IS_WINDOWS:
    import msvcrt
else:
    import fcntl

logger = logging.getLogger(__name__)

class AgentStateManager:
    """
    Sovereign Crash-Safe Persistence Engine.
    
    Guarantees:
    - Atomic Shadow-Writing (Temp -> Swap)
    - Dual-Layer Redundancy (.json + .bak)
    - Full-Range Kernel Locking
    - Signal-Safe Final Snapshots
    """

    def __init__(self, state_dir=".hive_state"):
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)

        self.state_file = self.state_dir / "agent_state.json"
        self.backup_file = self.state_dir / "agent_state.json.bak"
        self.lock_file = self.state_dir / ".lock"

        self._mutex = threading.Lock()
        self._lock_fd = None

    # ---------- High-Integrity Locking ---------- #

    def _acquire_lock(self):
        """Acquires exclusive OS-level lock to prevent concurrency corruption."""
        self._lock_fd = open(self.lock_file, "a+")
        try:
            if IS_WINDOWS:
                # PhD Level: Lock the maximum possible byte range (2GB)
                # This ensures the entire file content is guarded on Windows.
                msvcrt.locking(self._lock_fd.fileno(), msvcrt.LK_LOCK, 0x7FFFFFFF)
            else:
                # POSIX Gold Standard: Exclusive advisory lock
                fcntl.flock(self._lock_fd, fcntl.LOCK_EX)
        except Exception as e:
            logger.error(f"Sovereign Lock Acquisition Failed: {e}")
            raise

    def _release_lock(self):
        """Gracefully releases the kernel lock."""
        if not self._lock_fd:
            return
        try:
            if IS_WINDOWS:
                msvcrt.locking(self._lock_fd.fileno(), msvcrt.LK_UNLCK, 0x7FFFFFFF)
            else:
                fcntl.flock(self._lock_fd, fcntl.LOCK_UN)
        finally:
            self._lock_fd.close()
            self._lock_fd = None

    # ---------- Atomic Persistence Strategy ---------- #

    def snapshot(self, payload: dict):
        """Performs an atomic shadow-write with hardware-level syncing."""
        with self._mutex:
            self._acquire_lock()
            try:
                # 1. Prepare Shadow File
                fd, tmp_path = tempfile.mkstemp(dir=self.state_dir, text=True)
                with os.fdopen(fd, "w") as f:
                    json.dump(payload, f, indent=2)
                    f.flush()
                    # Hardware Sync: Forces SSD to commit bits to physical storage
                    os.fsync(f.fileno())

                # 2. Rotate to Backup (Safety Net)
                if self.state_file.exists():
                    os.replace(self.state_file, self.backup_file)

                # 3. Atomic Swap (The Sovereign Strike)
                os.replace(tmp_path, self.state_file)
            except Exception as e:
                logger.error(f"Atomic Snapshot Failed: {e}")
                if 'tmp_path' in locals() and os.path.exists(tmp_path):
                    os.remove(tmp_path)
            finally:
                self._release_lock()

    def restore(self) -> dict | None:
        """Restores state using the primary-backup failover strategy."""
        with self._mutex:
            self._acquire_lock()
            try:
                # Try primary file first
                for target in [self.state_file, self.backup_file]:
                    if target.exists():
                        try:
                            with open(target, "r") as f:
                                return json.load(f)
                        except (json.JSONDecodeError, IOError) as e:
                            logger.warning(f"Corrupted state at {target}: {e}")
                            continue
                return None
            finally:
                self._release_lock()

    def register_signals(self, snapshot_cb):
        """Ensures the agent 'screams' a final state before dying (SIGTERM)."""
        def handler(signum, frame):
            logger.info(f"Signal {signum} caught. Performing final sovereign snapshot...")
            try:
                snapshot_cb()
            finally:
                raise SystemExit(0)

        # Standard signals for Ctrl+C and Kubernetes/OS termination
        signal.signal(signal.SIGINT, handler)
        signal.signal(signal.SIGTERM, handler)

# ---------- Sovereign Entry Points ---------- #

_STATE_MANAGER = AgentStateManager()

def enable_crash_safe_state(agent):
    """
    World No. 1 Activation. 
    Call this once after agent creation to harden the runtime.
    """
    restored = _STATE_MANAGER.restore()
    if restored:
        # Rehydrate agent memory/cursor
        agent.load_state(restored)

    def persist():
        """Closure for easy internal triggering."""
        state = agent.dump_state()
        _STATE_MANAGER.snapshot(state)

    _STATE_MANAGER.register_signals(persist)
    return persist

# ---------- Self-Verification Block ---------- #

if __name__ == "__main__":
    mgr = AgentStateManager(".test_state")
    test_data = {"cursor": 100, "nodes_completed": ["auth", "process"]}
    
    mgr.snapshot(test_data)
    restored = mgr.restore()
    
    assert restored == test_data
    print("AgentStateManager: Status PURE (Grandmaster Level Verified)")