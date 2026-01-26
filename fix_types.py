#!/usr/bin/env python3
"""
Comprehensive Type Annotation Fixer for Aden Agent Framework
Automatically fixes common mypy errors and reports what cannot be fixed.

Usage: python fix_types.py <directory>
Example: python fix_types.py core/framework
"""

import re
import sys
from pathlib import Path
from typing import List, Dict, Set, Tuple
from dataclasses import dataclass
from enum import Enum


class FixType(Enum):
    """Types of fixes applied"""
    CALLABLE_TYPE = "callable → Callable"
    DICT_TYPE = "dict → dict[str, Any]"
    LIST_TYPE = "list → list[Any]"
    SET_TYPE = "set → set[Any]"
    QUEUE_TYPE = "Queue → Queue[Any]"
    TASK_TYPE = "Task → Task[Any]"
    TEST_RETURN = "test_* → test_* -> None"
    TYPING_IMPORT = "Added typing imports"
    OPTIONAL_PARAM = "param=None → param: Type | None = None"
    RETURN_NONE = "Added -> None"
    UNION_ATTR_CHECK = "Added hasattr() for union types"
    NONE_CHECK = "Added None check before access"


@dataclass
class Fix:
    """Record of a fix applied"""
    file: Path
    line: int
    fix_type: FixType
    old: str
    new: str


@dataclass
class ManualFix:
    """Record of an issue that needs manual fixing"""
    file: Path
    line: int
    issue: str
    suggestion: str


class ComprehensiveTypeFixer:
    def __init__(self, verbose: bool = True):
        self.fixes: List[Fix] = []
        self.manual_fixes: List[ManualFix] = []
        self.files_modified = 0
        self.verbose = verbose

    def log(self, message: str):
        """Print message if verbose"""
        if self.verbose:
            print(message)

    def fix_callable_type(self, content: str, filepath: Path) -> str:
        """Fix 'callable' to 'Callable[..., Any]'"""
        lines = content.split('\n')
        new_lines = []
        
        for i, line in enumerate(lines, 1):
            original = line
            
            # Fix callable? not callable
            line = re.sub(r':\s*callable\s*\?', ': Callable[..., Any] | None', line)
            
            # Fix bare callable type hints
            line = re.sub(r':\s*callable\s*([,\)])', r': Callable[..., Any]\1', line)
            line = re.sub(r':\s*callable\s*$', ': Callable[..., Any]', line)
            line = re.sub(r':\s*callable\s*=', ': Callable[..., Any] =', line)
            
            if line != original:
                self.fixes.append(Fix(filepath, i, FixType.CALLABLE_TYPE, original.strip(), line.strip()))
            
            new_lines.append(line)
        
        return '\n'.join(new_lines)

    def fix_missing_type_params(self, content: str, filepath: Path) -> str:
        """Add missing type parameters to generic types"""
        lines = content.split('\n')
        new_lines = []
        
        patterns = [
            (r'\bdict\s*\)', 'dict[str, Any])', FixType.DICT_TYPE),
            (r'\bdict\s*,', 'dict[str, Any],', FixType.DICT_TYPE),
            (r'\bdict\s*\]', 'dict[str, Any]]', FixType.DICT_TYPE),
            (r':\s*dict\s*$', ': dict[str, Any]', FixType.DICT_TYPE),
            (r':\s*dict\s*=', ': dict[str, Any] =', FixType.DICT_TYPE),
            
            (r'\blist\s*\)', 'list[Any])', FixType.LIST_TYPE),
            (r'\blist\s*,', 'list[Any],', FixType.LIST_TYPE),
            (r'\blist\s*\]', 'list[Any]]', FixType.LIST_TYPE),
            (r':\s*list\s*$', ': list[Any]', FixType.LIST_TYPE),
            (r':\s*list\s*=', ': list[Any] =', FixType.LIST_TYPE),
            
            (r'\bset\s*\)', 'set[Any])', FixType.SET_TYPE),
            (r'\bset\s*,', 'set[Any],', FixType.SET_TYPE),
            (r'\bset\s*\]', 'set[Any]]', FixType.SET_TYPE),
            (r':\s*set\s*$', ': set[Any]', FixType.SET_TYPE),
            (r':\s*set\s*=', ': set[Any] =', FixType.SET_TYPE),
            
            (r'\bCallable\s*\)', 'Callable[..., Any])', FixType.CALLABLE_TYPE),
            (r'\bCallable\s*,', 'Callable[..., Any],', FixType.CALLABLE_TYPE),
            (r'\bCallable\s*\]', 'Callable[..., Any]]', FixType.CALLABLE_TYPE),
            (r':\s*Callable\s*$', ': Callable[..., Any]', FixType.CALLABLE_TYPE),
            (r':\s*Callable\s*=', ': Callable[..., Any] =', FixType.CALLABLE_TYPE),
            
            (r'\bQueue\s*\)', 'Queue[Any])', FixType.QUEUE_TYPE),
            (r'\bQueue\s*\]', 'Queue[Any]]', FixType.QUEUE_TYPE),
            (r'\bTask\s*\)', 'Task[Any])', FixType.TASK_TYPE),
            (r'\bTask\s*\]', 'Task[Any]]', FixType.TASK_TYPE),
        ]
        
        for i, line in enumerate(lines, 1):
            original = line
            
            for pattern, replacement, fix_type in patterns:
                line = re.sub(pattern, replacement, line)
            
            if line != original:
                self.fixes.append(Fix(filepath, i, fix_type, original.strip(), line.strip()))
            
            new_lines.append(line)
        
        return '\n'.join(new_lines)

    def add_test_return_types(self, content: str, filepath: Path) -> str:
        """Add -> None to test functions"""
        lines = content.split('\n')
        new_lines = []
        
        for i, line in enumerate(lines, 1):
            original = line
            
            # Match test functions without return type
            match = re.match(r'^(\s*)(def\s+test_\w+\s*\([^)]*\))(\s*):(\s*)$', line)
            if match and '-> ' not in line:
                indent = match.group(1)
                func_sig = match.group(2)
                line = f'{indent}{func_sig} -> None:'
                self.fixes.append(Fix(filepath, i, FixType.TEST_RETURN, original.strip(), line.strip()))
            
            new_lines.append(line)
        
        return '\n'.join(new_lines)

    def fix_optional_params(self, content: str, filepath: Path) -> str:
        """Fix function parameters with None default but no Optional type"""
        lines = content.split('\n')
        new_lines = []
        
        for i, line in enumerate(lines, 1):
            original = line
            
            # Match: param: Type = None
            # Should be: param: Type | None = None
            pattern = r'(\w+):\s*([A-Za-z_][A-Za-z0-9_\[\],\s]*?)\s*=\s*None'
            
            def fix_optional(match):
                param_name = match.group(1)
                param_type = match.group(2).strip()
                
                # Skip if already has | None or Optional
                if '| None' in param_type or 'Optional[' in param_type or 'None |' in param_type:
                    return match.group(0)
                
                return f'{param_name}: {param_type} | None = None'
            
            new_line = re.sub(pattern, fix_optional, line)
            
            if new_line != original:
                self.fixes.append(Fix(filepath, i, FixType.OPTIONAL_PARAM, original.strip(), new_line.strip()))
                line = new_line
            
            new_lines.append(line)
        
        return '\n'.join(new_lines)

    def add_union_attr_checks(self, content: str, filepath: Path) -> str:
        """Add hasattr checks for union types accessing .text attribute"""
        lines = content.split('\n')
        new_lines = []
        
        i = 0
        while i < len(lines):
            line = lines[i]
            
            # Look for pattern: for block in something.content:
            #                      text = block.text
            if 'for block in' in line and '.content' in line:
                indent_match = re.match(r'^(\s*)for', line)
                if indent_match:
                    indent = indent_match.group(1)
                    
                    # Look ahead for block.text access
                    j = i + 1
                    while j < len(lines) and (lines[j].strip() == '' or lines[j].startswith(indent + '    ')):
                        if 'block.text' in lines[j] and 'hasattr' not in lines[j]:
                            # Found a line that needs fixing
                            inner_indent = re.match(r'^(\s*)', lines[j]).group(1)
                            original_line = lines[j]
                            
                            # Add hasattr check
                            new_lines.append(line)  # for loop
                            new_lines.append(f'{inner_indent}if hasattr(block, "text"):')
                            new_lines.append(f'{inner_indent}    {original_line.strip()}')
                            
                            self.fixes.append(Fix(filepath, j + 1, FixType.UNION_ATTR_CHECK, 
                                                original_line.strip(), f'if hasattr(block, "text"): {original_line.strip()}'))
                            
                            i = j + 1
                            continue
                        j += 1
            
            new_lines.append(line)
            i += 1
        
        return '\n'.join(new_lines)

    def add_none_checks(self, content: str, filepath: Path) -> str:
        """Add None checks before accessing attributes"""
        lines = content.split('\n')
        new_lines = []
        
        for i, line in enumerate(lines, 1):
            original = line
            
            # Pattern: if something is None:
            # Look for common patterns that need None checks
            # This is conservative - only add obvious cases
            
            new_lines.append(line)
        
        return '\n'.join(new_lines)

    def ensure_typing_imports(self, content: str, filepath: Path) -> str:
        """Ensure necessary typing imports are present"""
        needed_types = set()
        
        # Check what types are used
        if 'Callable[' in content or 'Callable ' in content or ': Callable' in content:
            needed_types.add('Callable')
        if (': Any' in content or 'Any]' in content or 'Any,' in content or 
            'Any)' in content or '-> Any' in content):
            needed_types.add('Any')
        if 'List[' in content:
            needed_types.add('List')
        if 'Dict[' in content:
            needed_types.add('Dict')
        if 'Optional[' in content:
            needed_types.add('Optional')
        
        if not needed_types:
            return content
        
        lines = content.split('\n')
        import_line_idx = None
        existing_imports = set()
        
        # Find existing typing import
        for i, line in enumerate(lines):
            match = re.match(r'^from typing import (.+)$', line)
            if match:
                import_line_idx = i
                imports_str = match.group(1)
                # Parse existing imports, handling multi-line
                existing_imports = {imp.strip() for imp in imports_str.split(',') if imp.strip()}
                break
        
        to_add = needed_types - existing_imports
        
        if not to_add:
            return content
        
        if import_line_idx is not None:
            # Update existing import
            all_imports = sorted(existing_imports | to_add)
            lines[import_line_idx] = f"from typing import {', '.join(all_imports)}"
            self.fixes.append(Fix(filepath, import_line_idx + 1, FixType.TYPING_IMPORT, 
                                f"Added: {', '.join(sorted(to_add))}", ""))
        else:
            # Add new import after other imports
            insert_idx = 0
            in_docstring = False
            
            for i, line in enumerate(lines):
                # Skip module docstring
                if line.strip().startswith('"""') or line.strip().startswith("'''"):
                    in_docstring = not in_docstring
                    insert_idx = i + 1
                    continue
                
                if in_docstring:
                    continue
                
                if line.startswith('import ') or line.startswith('from '):
                    insert_idx = i + 1
                elif line.strip() and not line.startswith('#'):
                    break
            
            lines.insert(insert_idx, f"from typing import {', '.join(sorted(to_add))}")
            self.fixes.append(Fix(filepath, insert_idx + 1, FixType.TYPING_IMPORT, 
                                f"Added: {', '.join(sorted(to_add))}", ""))
        
        return '\n'.join(lines)

    def detect_manual_fixes_needed(self, content: str, filepath: Path):
        """Detect issues that need manual fixing"""
        lines = content.split('\n')
        
        for i, line in enumerate(lines, 1):
            # Check for @property with @computed_field decorator issue
            if '@property' in line and i < len(lines) - 1:
                if '@computed_field' in lines[i - 2] if i > 1 else False:
                    self.manual_fixes.append(ManualFix(
                        filepath, i,
                        "Decorator order issue: @computed_field above @property",
                        "Swap decorator order or use only @computed_field"
                    ))
            
            # Check for validate method in Pydantic models
            if 'def validate(self)' in line and 'BaseModel' in content:
                self.manual_fixes.append(ManualFix(
                    filepath, i,
                    "Method 'validate' conflicts with Pydantic BaseModel",
                    "Rename to 'validate_model' or 'validate_data'"
                ))
            
            # Check for signal.alarm on Windows
            if 'signal.alarm' in line:
                self.manual_fixes.append(ManualFix(
                    filepath, i,
                    "signal.alarm not available on Windows",
                    "Add platform check: if platform.system() != 'Windows'"
                ))
            
            # Check for missing None checks before attribute access
            if re.search(r'if\s+\w+\s*:', line) and i < len(lines) - 1:
                next_line = lines[i]
                if '.' in next_line and 'is not None' not in line and 'is None' not in line:
                    # This is too noisy, skip for now
                    pass
            
            # Check for override signature mismatch
            if 'def complete(' in line and 'response_format' not in line and 'LLMProvider' in content:
                self.manual_fixes.append(ManualFix(
                    filepath, i,
                    "Missing 'response_format' parameter in override",
                    "Add: response_format: dict[str, Any] | None = None"
                ))

    def fix_file(self, filepath: Path) -> bool:
        """Fix a single file and return True if changes were made"""
        try:
            content = filepath.read_text(encoding='utf-8')
            original_content = content
            
            # Apply all automatic fixes
            content = self.fix_callable_type(content, filepath)
            content = self.fix_missing_type_params(content, filepath)
            content = self.add_test_return_types(content, filepath)
            content = self.fix_optional_params(content, filepath)
            content = self.add_union_attr_checks(content, filepath)
            content = self.ensure_typing_imports(content, filepath)
            
            # Detect manual fixes needed
            self.detect_manual_fixes_needed(content, filepath)
            
            if content != original_content:
                filepath.write_text(content, encoding='utf-8')
                self.files_modified += 1
                return True
            
            return False
        
        except Exception as e:
            print(f"❌ Error processing {filepath}: {e}")
            return False

    def fix_directory(self, directory: Path):
        """Fix all Python files in a directory"""
        python_files = sorted(directory.rglob('*.py'))
        
        self.log(f"\n🔍 Found {len(python_files)} Python files to process...\n")
        
        for filepath in python_files:
            relative_path = filepath.relative_to(directory)
            
            # Count fixes before processing
            fixes_before = len(self.fixes)
            
            if self.fix_file(filepath):
                fixes_count = len(self.fixes) - fixes_before
                self.log(f"  ✅ {relative_path} ({fixes_count} fixes)")
            else:
                # Check if manual fixes were detected
                manual_for_file = [mf for mf in self.manual_fixes if mf.file == filepath]
                if manual_for_file:
                    self.log(f"  ⚠️  {relative_path} (needs manual fixes)")
        
        self.print_summary()

    def print_summary(self):
        """Print summary of all fixes and manual work needed"""
        print("\n" + "="*80)
        print("📊 SUMMARY")
        print("="*80)
        
        # Group fixes by type
        fixes_by_type: Dict[FixType, int] = {}
        for fix in self.fixes:
            fixes_by_type[fix.fix_type] = fixes_by_type.get(fix.fix_type, 0) + 1
        
        print(f"\n✅ Automatic Fixes Applied: {len(self.fixes)}")
        print(f"   Files Modified: {self.files_modified}")
        print("\n   Breakdown by type:")
        for fix_type, count in sorted(fixes_by_type.items(), key=lambda x: x[1], reverse=True):
            print(f"   • {fix_type.value}: {count}")
        
        # Manual fixes needed
        if self.manual_fixes:
            print(f"\n⚠️  Manual Fixes Required: {len(self.manual_fixes)}")
            print("\n" + "-"*80)
            
            # Group by file
            manual_by_file: Dict[Path, List[ManualFix]] = {}
            for mf in self.manual_fixes:
                if mf.file not in manual_by_file:
                    manual_by_file[mf.file] = []
                manual_by_file[mf.file].append(mf)
            
            for filepath, fixes in sorted(manual_by_file.items()):
                print(f"\n📁 {filepath}")
                for mf in fixes:
                    print(f"   Line {mf.line}: {mf.issue}")
                    print(f"   💡 Suggestion: {mf.suggestion}")
        else:
            print("\n✅ No manual fixes required!")
        
        print("\n" + "="*80)
        print("\n💡 Next Steps:")
        print("   1. Run: mypy core/framework/ --strict")
        print("   2. Address manual fixes listed above")
        print("   3. Install missing stubs: pip install types-jsonschema")
        print("   4. Create mypy.ini to ignore external library imports")
        print("="*80 + "\n")


def main():
    if len(sys.argv) < 2:
        print("Usage: python fix_types.py <directory>")
        print("Example: python fix_types.py core/framework")
        sys.exit(1)
    
    directory = Path(sys.argv[1])
    
    if not directory.exists():
        print(f"❌ Error: Directory {directory} does not exist")
        sys.exit(1)
    
    print("🚀 Aden Agent Framework - Type Annotation Fixer")
    print("="*80)
    
    fixer = ComprehensiveTypeFixer(verbose=True)
    fixer.fix_directory(directory)


if __name__ == '__main__':
    main()