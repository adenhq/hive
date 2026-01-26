from pathlib import Path
import re


def fix_mypy_ini():
    """Remove the problematic pattern from mypy.ini"""
    filepath = Path('mypy.ini')
    
    if not filepath.exists():
        print("❌ mypy.ini not found")
        return False
    
    content = filepath.read_text(encoding='utf-8')
    original = content
    
    # Remove the problematic pattern lines
    lines = content.split('\n')
    new_lines = []
    
    for line in lines:
        # Skip lines with the bad patterns
        if '[mypy-*.test_*]' in line or '[mypy-*tests.*]' in line:
            continue
        new_lines.append(line)
    
    content = '\n'.join(new_lines)
    
    if content != original:
        filepath.write_text(content, encoding='utf-8')
        print("✅ Fixed mypy.ini pattern errors")
        return True
    
    print("ℹ️  mypy.ini already correct")
    return False


def fix_output_cleaner_import():
    """Fix the import error in output_cleaner.py"""
    filepath = Path('core/framework/graph/output_cleaner.py')
    
    if not filepath.exists():
        print("❌ output_cleaner.py not found")
        return False
    
    content = filepath.read_text(encoding='utf-8')
    original = content
    
    # Fix the wrong import
    content = re.sub(
        r'from provider import',
        'from framework.llm.provider import',
        content
    )
    
    if content != original:
        filepath.write_text(content, encoding='utf-8')
        print("✅ Fixed output_cleaner.py import error")
        return True
    
    print("ℹ️  output_cleaner.py import already correct")
    return False


def fix_validate_calls():
    """Fix remaining .validate() calls that should be .validate_graph()"""
    base = Path('core/framework')
    
    # Files that might have validate() calls to GraphSpec
    files_to_check = [
        base / 'graph' / 'executor.py',
        base / 'builder' / 'workflow.py',
        base / 'runtime' / 'tests' / 'test_agent_runtime.py',
        base / 'runner' / 'runner.py',
    ]
    
    fixed_count = 0
    
    for filepath in files_to_check:
        if not filepath.exists():
            continue
        
        content = filepath.read_text(encoding='utf-8')
        original = content
        
        # Look for GraphSpec().validate() or graph_spec.validate() patterns
        # Be careful not to replace Pydantic's validate
        
        # Pattern 1: graph_spec.validate() or spec.validate()
        content = re.sub(
            r'(graph_spec|spec|graph|builder)\.validate\(\)',
            r'\1.validate_graph()',
            content
        )
        
        # Pattern 2: GraphSpec.validate(value) -> Keep this as is (it's Pydantic)
        # We only want to change instance method calls
        
        if content != original:
            filepath.write_text(content, encoding='utf-8')
            print(f"✅ Fixed validate() calls in: {filepath.name}")
            fixed_count += 1
    
    if fixed_count == 0:
        print("ℹ️  No validate() calls to fix")
    
    return fixed_count > 0


def add_return_none_annotations():
    """Add -> None to functions that clearly don't return values"""
    base = Path('core/framework')
    
    files_to_fix = [
        base / 'llm' / 'mock_provider.py',
        base / 'runtime' / 'shared_state.py',
        base / 'runtime' / 'stream_runtime.py',
        base / 'graph' / 'code_sandbox.py',
        base / 'runner' / 'tool_registry.py',
        base / 'runner' / 'mcp_client.py',
        base / 'testing' / 'llm_judge.py',
        base / 'mcp' / 'agent_builder_server.py',
    ]
    
    fixed_count = 0
    
    for filepath in files_to_fix:
        if not filepath.exists():
            continue
        
        content = filepath.read_text(encoding='utf-8')
        lines = content.split('\n')
        new_lines = []
        changes = 0
        
        i = 0
        while i < len(lines):
            line = lines[i]
            
            # Look for function definitions without return type
            func_match = re.match(r'^(\s*)(def\s+\w+\s*\([^)]*\))(\s*):(\s*)$', line)
            
            if func_match and '-> ' not in line:
                indent = func_match.group(1)
                func_sig = func_match.group(2)
                
                # Check if function has a return statement with value in next 30 lines
                has_return_value = False
                for j in range(i + 1, min(i + 30, len(lines))):
                    # Check for 'return something' (not just 'return')
                    if re.search(r'^\s+return\s+[^\s]', lines[j]):
                        has_return_value = True
                        break
                    # Stop at next function
                    if re.match(r'^\s*def\s+', lines[j]) and j > i + 1:
                        break
                
                # Only add -> None if no return value found
                if not has_return_value:
                    new_lines.append(f'{indent}{func_sig} -> None:')
                    changes += 1
                    i += 1
                    continue
            
            new_lines.append(line)
            i += 1
        
        if changes > 0:
            filepath.write_text('\n'.join(new_lines), encoding='utf-8')
            print(f"✅ Added {changes} return type annotations to: {filepath.name}")
            fixed_count += changes
    
    if fixed_count == 0:
        print("ℹ️  No return type annotations to add")
    
    return fixed_count > 0


def add_missing_type_params():
    """Add missing type parameters that the first script missed"""
    base = Path('core/framework')
    
    files_to_fix = list(base.rglob('*.py'))
    
    patterns = [
        (r':\s*dict\s*=', ': dict[str, Any] ='),
        (r':\s*Callable\s*=', ': Callable[..., Any] ='),
        (r':\s*Queue\s*\)', ': Queue[Any])'),
        (r':\s*Task\s*\)', ': Task[Any])'),
    ]
    
    fixed_count = 0
    
    for filepath in files_to_fix:
        if 'test_' in filepath.name or filepath.suffix != '.py':
            continue
        
        try:
            content = filepath.read_text(encoding='utf-8')
            original = content
            
            for pattern, replacement in patterns:
                content = re.sub(pattern, replacement, content)
            
            if content != original:
                filepath.write_text(content, encoding='utf-8')
                print(f"✅ Added type parameters to: {filepath.relative_to(base)}")
                fixed_count += 1
        except Exception as e:
            pass
    
    if fixed_count == 0:
        print("ℹ️  No missing type parameters found")
    
    return fixed_count > 0


def fix_isinstance_with_generics():
    """Fix isinstance checks with parameterized generics"""
    base = Path('core/framework')
    
    # This is a more complex fix - we'll add get_origin imports where needed
    files_with_isinstance = [
        base / 'runner' / 'tool_registry.py',
        base / 'graph' / 'judge.py',
        base / 'graph' / 'worker_node.py',
        base / 'graph' / 'validator.py',
        base / 'graph' / 'output_cleaner.py',
        base / 'graph' / 'node.py',
    ]
    
    fixed_count = 0
    
    for filepath in files_with_isinstance:
        if not filepath.exists():
            continue
        
        content = filepath.read_text(encoding='utf-8')
        original = content
        
        # Check if file has isinstance with list[...] or dict[...]
        if re.search(r'isinstance\([^,]+,\s*(list\[|dict\[)', content):
            # Add get_origin import if not present
            if 'from typing import' in content and 'get_origin' not in content:
                content = re.sub(
                    r'from typing import ([^\n]+)',
                    r'from typing import \1, get_origin',
                    content,
                    count=1
                )
            elif 'from typing import' not in content:
                # Add new import at top
                lines = content.split('\n')
                insert_idx = 0
                for i, line in enumerate(lines):
                    if line.startswith('import ') or line.startswith('from '):
                        insert_idx = i + 1
                    elif line.strip() and not line.startswith('#'):
                        break
                lines.insert(insert_idx, 'from typing import get_origin')
                content = '\n'.join(lines)
            
            # Replace isinstance(x, list[...]) with isinstance(x, list)
            content = re.sub(
                r'isinstance\(([^,]+),\s*list\[[^\]]+\]\)',
                r'isinstance(\1, list)',
                content
            )
            
            # Replace isinstance(x, dict[...]) with isinstance(x, dict)
            content = re.sub(
                r'isinstance\(([^,]+),\s*dict\[[^\]]+\]\)',
                r'isinstance(\1, dict)',
                content
            )
        
        if content != original:
            filepath.write_text(content, encoding='utf-8')
            print(f"✅ Fixed isinstance checks in: {filepath.name}")
            fixed_count += 1
    
    if fixed_count == 0:
        print("ℹ️  No isinstance checks to fix")
    
    return fixed_count > 0


def main():
    print("🔧 Quick Fix Script - Round 2")
    print("="*80)
    print("\n📝 Applying fixes...\n")
    
    fixes_applied = 0
    
    # Fix 1: mypy.ini pattern error
    if fix_mypy_ini():
        fixes_applied += 1
    
    # Fix 2: output_cleaner.py import
    if fix_output_cleaner_import():
        fixes_applied += 1
    
    # Fix 3: validate() calls
    if fix_validate_calls():
        fixes_applied += 5  # Estimate multiple calls fixed
    
    # Fix 4: Add -> None annotations
    if add_return_none_annotations():
        fixes_applied += 15  # Estimate
    
    # Fix 5: Missing type parameters
    if add_missing_type_params():
        fixes_applied += 5
    
    # Fix 6: isinstance with generics
    if fix_isinstance_with_generics():
        fixes_applied += 10  # Estimate ~30 errors
    
    print("\n" + "="*80)
    print(f"✅ Applied fixes (estimated ~{fixes_applied} errors fixed)")
    print("="*80)
    
    print("\n💡 Next Steps:")
    print("   1. Run: mypy core/framework/ --strict")
    print("   2. Expected: ~180-200 errors remaining")
    print("   3. Major remaining issues:")
    print("      - Union attribute access (Anthropic blocks)")
    print("      - None safety guards")
    print("      - Untyped function calls")
    print("\n")


if __name__ == '__main__':
    main()