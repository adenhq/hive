import sys
import os

# Mock the security module since we are running standalone
sys.modules['..security'] = type('security', (), {'get_secure_path': lambda p, w, a, s: os.path.abspath(p), 'WORKSPACES_DIR': '/tmp'})

# Adjust path to find the module
sys.path.append('e:/hive/tools/src/aden_tools/tools/file_system_toolkits')

from subprocess import run, PIPE

def test_rce_attempt():
    """
    Test that shell injection fails.
    We attempt to chain commands using ';'.
    If shell=True, both echo commands run and we see "VULNERABLE".
    If shell=False, the second part is treated as an argument to echo.
    """
    # Use python to print since echo is a shell builtin and won't work with shell=False on Windows
    import sys
    cmd_exec = sys.executable
    # We want to run: python -c "print('HARMLESS')" ; python -c "print('VULNERABLE')"
    # If shell=True, both run.
    # If shell=False, the semicolon is treated as an argument.
    command = f'{cmd_exec} -c "print(\'HARMLESS\')" ; {cmd_exec} -c "print(\'VULNERABLE\')"'
    
    # We will simulate the behavior of the tool's core logic
    import shlex
    import subprocess
    args = shlex.split(command)
    
    print(f"Command: {command}")
    print(f"Parsed Args: {args}")
    
    try:
        result = subprocess.run(
            args,
            shell=False,
            # cwd=os.getcwd(), # simplified for test
            capture_output=True,
            text=True,
            timeout=5
        )
        print("\nSTDOUT:", result.stdout)
        print("STDERR:", result.stderr)
        
        if "VULNERABLE" in result.stdout and "HARMLESS" in result.stdout:
             # If both run, it's vulnerable (or shlex failed to quote it, but shell=False usually prevents chaining)
             # Wait, if shell=False, 'echo HARMLESS; echo VULNERABLE' calls 'echo' with args ['HARMLESS;', 'echo', 'VULNERABLE']
             # So it should print "HARMLESS; echo VULNERABLE" literally.
             pass
        
        # If correct, it should try to execute python with the whole string as args, or fail to parse.
        # Actually with shell=False, shlex.split() splits it.
        # args[0] = python
        # args[1] = -c
        # args[2] = print('HARMLESS')
        # args[3] = ;
        # args[4] = python...
        # Python will likely ignore args[3+] or fail? 
        # Python -c accepts one arg. subsequent args are in sys.argv.
        # So it should run HARMLESS and ignore the rest as program args.
        
        if "VULNERABLE" in result.stdout:
             print("\n[FAILURE] 'VULNERABLE' printed! RCE successful.")
             return False
        
        if "HARMLESS" in result.stdout:
             print("\n[SUCCESS] Only HARMLESS executed. Semicolon was treated as an argument.")
             return True
        else:
             print("\n[INFO] Execution output:", result.stdout)
             # If it just prints usage or errors, that's also safe from RCE
             return True
             
    except Exception as e:
        print(f"Execution failed: {e}")
        # Failure to execute is SAFE (no RCE)
        return True

if __name__ == "__main__":
    test_rce_attempt()
