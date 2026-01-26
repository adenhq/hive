#!/usr/bin/env python3
"""
Automated fixes for the 12 manual issues identified
Run after fix_types.py
"""

from pathlib import Path
import re


def fix_anthropic_provider(filepath: Path):
    """Add response_format parameter to anthropic.py"""
    content = filepath.read_text(encoding='utf-8')
    
    # Find the complete method definition
    pattern = r'(def complete\(\s*self,\s*messages: list\[dict\[str, Any\]\],\s*system: str = "",\s*tools: list\[Tool\] \| None = None,\s*max_tokens: int = \d+,)\s*(json_mode: bool = False,\s*\) -> LLMResponse:)'
    
    replacement = r'\1\n        response_format: dict[str, Any] | None = None,\n        \2'
    
    new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)
    
    if new_content != content:
        filepath.write_text(new_content, encoding='utf-8')
        print(f"✅ Fixed: {filepath}")
        return True
    else:
        print(f"⚠️  Manual fix needed: {filepath} (pattern not matched)")
        return False


def fix_litellm_provider(filepath: Path):
    """Add response_format parameter to litellm.py"""
    content = filepath.read_text(encoding='utf-8')
    
    # Find the complete method
    pattern = r'(def complete\(\s*self,\s*messages: list\[dict\[str, Any\]\],\s*system: str = "",\s*tools: list\[Tool\] \| None = None,\s*max_tokens: int = \d+,)\s*(json_mode: bool = False,\s*\) -> LLMResponse:)'
    
    replacement = r'\1\n        response_format: dict[str, Any] | None = None,\n        \2'
    
    new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)
    
    if new_content != content:
        filepath.write_text(new_content, encoding='utf-8')
        print(f"✅ Fixed: {filepath}")
        return True
    else:
        print(f"⚠️  Manual fix needed: {filepath} (pattern not matched)")
        return False


def fix_base_provider(filepath: Path):
    """Add response_format parameter to base provider.py"""
    content = filepath.read_text(encoding='utf-8')
    
    # Find the abstract method
    pattern = r'(@abstractmethod\s+def complete\(\s*self,\s*messages: list\[dict\[str, Any\]\],\s*system: str = "",\s*tools: list\[Tool\] \| None = None,\s*max_tokens: int = \d+,)\s*(json_mode: bool = False,?\s*\) -> LLMResponse:)'
    
    replacement = r'\1\n        response_format: dict[str, Any] | None = None,\n        \2'
    
    new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)
    
    if new_content != content:
        filepath.write_text(new_content, encoding='utf-8')
        print(f"✅ Fixed: {filepath}")
        return True
    else:
        print(f"⚠️  Manual fix needed: {filepath} (pattern not matched)")
        return False


def fix_validate_method(filepath: Path):
    """Rename validate method to validate_graph"""
    content = filepath.read_text(encoding='utf-8')
    original = content
    
    # Find and rename the validate method definition
    content = re.sub(
        r'def validate\(self\) -> list\[str\]:',
        'def validate_graph(self) -> list[str]:',
        content
    )
    
    # Find and rename calls to validate
    content = re.sub(
        r'\.validate\(\)',
        '.validate_graph()',
        content
    )
    
    if content != original:
        filepath.write_text(content, encoding='utf-8')
        print(f"✅ Fixed: {filepath}")
        return True
    else:
        print(f"⚠️  No changes made: {filepath}")
        return False


def fix_decorator_order(filepath: Path):
    """Fix @property and @computed_field decorator order"""
    content = filepath.read_text(encoding='utf-8')
    lines = content.split('\n')
    new_lines = []
    
    i = 0
    changes = 0
    while i < len(lines):
        # Look for @computed_field followed by @property
        if i < len(lines) - 1:
            if '@computed_field' in lines[i] and '@property' in lines[i + 1]:
                # Swap them
                new_lines.append(lines[i + 1])  # @property first
                new_lines.append(lines[i])      # @computed_field second
                i += 2
                changes += 1
                continue
        
        new_lines.append(lines[i])
        i += 1
    
    if changes > 0:
        filepath.write_text('\n'.join(new_lines), encoding='utf-8')
        print(f"✅ Fixed: {filepath} ({changes} decorator swaps)")
        return True
    else:
        print(f"⚠️  No decorator issues found: {filepath}")
        return False


def fix_signal_alarm(filepath: Path):
    """Add platform check for signal.alarm"""
    content = filepath.read_text(encoding='utf-8')
    
    # Check if platform is already imported
    if 'import platform' not in content:
        # Add import after other imports
        lines = content.split('\n')
        import_idx = 0
        for i, line in enumerate(lines):
            if line.startswith('import ') or line.startswith('from '):
                import_idx = i + 1
        lines.insert(import_idx, 'import platform')
        content = '\n'.join(lines)
    
    # Find signal.alarm usage and wrap it
    lines = content.split('\n')
    new_lines = []
    i = 0
    changes = 0
    
    while i < len(lines):
        line = lines[i]
        
        # Look for signal.alarm
        if 'signal.alarm(' in line and 'if platform.system()' not in line:
            indent = len(line) - len(line.lstrip())
            indent_str = ' ' * indent
            
            # Look back for signal.signal
            signal_line_idx = None
            for j in range(i - 1, max(0, i - 5), -1):
                if 'signal.signal' in lines[j]:
                    signal_line_idx = j
                    break
            
            if signal_line_idx is not None:
                # Add all lines before signal.signal
                for k in range(len(new_lines), signal_line_idx):
                    if k < len(lines):
                        new_lines.append(lines[k])
                
                # Add platform check
                new_lines.append(f'{indent_str}if platform.system() != "Windows":')
                
                # Add indented signal.signal line
                signal_line = lines[signal_line_idx]
                new_lines.append(f'    {signal_line}')
                
                # Add indented signal.alarm line
                new_lines.append(f'    {line}')
                
                changes += 1
                i += 1
                continue
        
        new_lines.append(line)
        i += 1
    
    if changes > 0:
        filepath.write_text('\n'.join(new_lines), encoding='utf-8')
        print(f"✅ Fixed: {filepath} ({changes} platform checks added)")
        return True
    else:
        print(f"⚠️  Could not auto-fix signal.alarm: {filepath}")
        return False


def main():
    print("🔧 Applying Manual Fixes for Aden Agent Framework")
    print("="*80)
    
    base_path = Path('core/framework')
    
    fixes = [
        (base_path / 'llm' / 'provider.py', fix_base_provider),
        (base_path / 'llm' / 'anthropic.py', fix_anthropic_provider),
        (base_path / 'llm' / 'litellm.py', fix_litellm_provider),
        (base_path / 'graph' / 'edge.py', fix_validate_method),
        (base_path / 'builder' / 'workflow.py', fix_validate_method),
        (base_path / 'schemas' / 'decision.py', fix_decorator_order),
        (base_path / 'schemas' / 'run.py', fix_decorator_order),
        (base_path / 'graph' / 'code_sandbox.py', fix_signal_alarm),
    ]
    
    print("\n📝 Applying fixes...\n")
    
    success_count = 0
    for filepath, fix_func in fixes:
        if filepath.exists():
            if fix_func(filepath):
                success_count += 1
        else:
            print(f"❌ File not found: {filepath}")
    
    print("\n" + "="*80)
    print(f"✅ Successfully applied {success_count}/{len(fixes)} fixes")
    print("="*80)
    print("\n💡 Next steps:")
    print("   1. Run: mypy core/framework/ --strict")
    print("   2. Check for remaining errors")
    print("   3. Manually fix any remaining issues")
    print("\n")


if __name__ == '__main__':
    main()