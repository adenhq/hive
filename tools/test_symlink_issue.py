#!/usr/bin/env python3
"""
Test: list_dir tool crashes on broken symlinks

This demonstrates the bug where list_dir crashes when encountering
a broken symlink instead of handling it gracefully.
"""

import tempfile
import os
from pathlib import Path

def demo_broken_symlink_crash():
    """Demonstrate the crash when listing directory with broken symlink."""
    print("="*60)
    print("ISSUE: list_dir crashes on broken symlinks")
    print("="*60)
    
    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        
        # Create a normal file
        (tmpdir / "normal_file.txt").write_text("content")
        
        # Create a symlink to a file that exists
        target = tmpdir / "target.txt"
        target.write_text("target content")
        (tmpdir / "good_link").symlink_to(target)
        
        # Create a broken symlink (target doesn't exist)
        (tmpdir / "broken_link").symlink_to(tmpdir / "nonexistent.txt")
        
        print(f"\nTest directory: {tmpdir}")
        print("Contents:")
        print("  - normal_file.txt (regular file)")
        print("  - good_link -> target.txt (valid symlink)")
        print("  - broken_link -> nonexistent.txt (BROKEN symlink)")
        
        # Simulate list_dir behavior
        print("\n❌ CURRENT BEHAVIOR (crashes):")
        items = os.listdir(tmpdir)
        for item in items:
            full_path = tmpdir / item
            is_dir = os.path.isdir(full_path)
            try:
                if not is_dir:
                    size = os.path.getsize(full_path)
                    print(f"   ✓ {item}: {size} bytes")
                else:
                    print(f"   ✓ {item}: directory")
            except OSError as e:
                print(f"   ✗ {item}: CRASH! {e}")
                print(f"      Error: os.path.getsize() fails on broken symlink")
        
        print("\n✅ EXPECTED BEHAVIOR (graceful):")
        print("   ✓ normal_file.txt: 7 bytes")
        print("   ✓ good_link: symlink (19 bytes)")
        print("   ✓ broken_link: symlink (broken)")
        print("   All entries listed without crash!")

if __name__ == "__main__":
    demo_broken_symlink_crash()
