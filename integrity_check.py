import os
import sys
import platform

def audit_system():
    print("🚀 --- SUHAS HIVE: SYSTEM INTEGRITY AUDIT ---")
    print(f"OS: {platform.system()} {platform.release()}")
    print(f"Python Version: {sys.version}")

    # Check for Virtual Environment
    venv_active = os.getenv('VIRTUAL_ENV')
    if venv_active:
        print(f"✅ VIRTUAL_ENV ACTIVE: {venv_active}")
    else:
        print("⚠️  WARNING: Running outside a virtual environment.")

    # Check for the Core directory
    if os.path.exists('core'):
        print("✅ CORE DIRECTORY: Located")
    else:
        print("❌ ERROR: Core directory missing. Repository integrity compromised.")

if __name__ == "__main__":
    audit_system()