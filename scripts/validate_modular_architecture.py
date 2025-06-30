#!/usr/bin/env python3
"""
Validate Modular Architecture Script
Purpose: Enforce modular development practices and prevent code bloat in agentic-rag-demo.py
"""

import ast
import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Set
import re

class ModularArchitectureValidator:
    """Validates adherence to modular architecture principles."""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.main_file = self.project_root / "agentic-rag-demo.py"
        self.max_main_file_lines = 500
        self.current_line_count = 0
        
        # Define what's allowed in main file
        self.allowed_in_main = {
            'imports', 'main', 'run_streamlit_ui', 'setup_logging',
            'init_session_state', 'load_config', '__name__', '__main__'
        }
        
        # Define prohibited patterns in main file
        self.prohibited_patterns = [
            r'def render_.*_tab\(',
            r'class.*Service\(',
            r'class.*Manager\(',
            r'def process_.*\(',
            r'def handle_.*\(',
            r'def analyze_.*\(',
            r'def extract_.*\(',
            r'def validate_.*\(',
            r'def upload_.*\(',
            r'def download_.*\(',
        ]

    def check_main_file_size(self) -> Tuple[bool, str]:
        """Check if main file exceeds size limit."""
        if not self.main_file.exists():
            return False, f"Main file {self.main_file} not found"
            
        with open(self.main_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            self.current_line_count = len(lines)
            
        if self.current_line_count > self.max_main_file_lines:
            return False, f"Main file has {self.current_line_count} lines, exceeds limit of {self.max_main_file_lines}"
        
        return True, f"Main file size OK: {self.current_line_count} lines"

    def check_prohibited_patterns(self) -> Tuple[bool, List[str]]:
        """Check for prohibited code patterns in main file."""
        if not self.main_file.exists():
            return False, ["Main file not found"]
            
        violations = []
        
        with open(self.main_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        for i, line in enumerate(content.split('\n'), 1):
            for pattern in self.prohibited_patterns:
                if re.search(pattern, line):
                    violations.append(f"Line {i}: {line.strip()}")
                    
        return len(violations) == 0, violations

    def check_function_complexity(self) -> Tuple[bool, List[str]]:
        """Check for overly complex functions in main file."""
        if not self.main_file.exists():
            return False, ["Main file not found"]
            
        violations = []
        max_function_lines = 50
        
        try:
            with open(self.main_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    if node.name in self.allowed_in_main:
                        continue
                        
                    # Calculate function length
                    if hasattr(node, 'end_lineno') and hasattr(node, 'lineno'):
                        func_lines = node.end_lineno - node.lineno + 1
                        if func_lines > max_function_lines:
                            violations.append(
                                f"Function '{node.name}' has {func_lines} lines, "
                                f"exceeds limit of {max_function_lines}"
                            )
                    
        except SyntaxError as e:
            violations.append(f"Syntax error in main file: {e}")
        except Exception as e:
            violations.append(f"Error analyzing main file: {e}")
            
        return len(violations) == 0, violations

    def check_module_structure(self) -> Tuple[bool, List[str]]:
        """Check if required module directories exist."""
        # Required directories that MUST exist
        required_dirs = [
            'app', 'core', 'utils', 'connectors'
        ]
        
        # Recommended directories that SHOULD exist but aren't critical
        recommended_dirs = [
            'app/ui/components', 'health_check', 'scripts', 'tests'
        ]
        
        missing_required = []
        missing_recommended = []
        
        for dir_name in required_dirs:
            dir_path = self.project_root / dir_name
            if not dir_path.exists():
                missing_required.append(str(dir_path))
                
        for dir_name in recommended_dirs:
            dir_path = self.project_root / dir_name
            if not dir_path.exists():
                missing_recommended.append(str(dir_path))
                
        # Only fail if required directories are missing
        all_dirs_ok = len(missing_required) == 0
        
        # Combine missing directories for reporting
        all_missing = missing_required + missing_recommended
                
        return all_dirs_ok, all_missing

    def generate_migration_suggestions(self) -> List[str]:
        """Generate suggestions for extracting code from main file."""
        suggestions = []
        
        if not self.main_file.exists():
            return ["Main file not found"]
            
        try:
            with open(self.main_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    if node.name.startswith('render_') and node.name.endswith('_tab'):
                        suggestions.append(
                            f"Extract function '{node.name}' to app/ui/ (or create app/tabs/{node.name}.py)"
                        )
                    elif 'process' in node.name.lower():
                        suggestions.append(
                            f"Extract function '{node.name}' to core/document_processor.py"
                        )
                    elif 'health' in node.name.lower():
                        suggestions.append(
                            f"Extract function '{node.name}' to health_check/ module"
                        )
                    elif 'service' in node.name.lower() or 'manager' in node.name.lower():
                        suggestions.append(
                            f"Extract function '{node.name}' to core/ or create new service module"
                        )
                elif isinstance(node, ast.ClassDef):
                    if 'Service' in node.name or 'Manager' in node.name:
                        suggestions.append(
                            f"Extract class '{node.name}' to core/ or create new service module"
                        )
                    elif 'Health' in node.name:
                        suggestions.append(
                            f"Extract class '{node.name}' to health_check/ module"
                        )
                        
        except Exception as e:
            suggestions.append(f"Error analyzing code: {e}")
            
        return suggestions

    def run_validation(self) -> Dict[str, any]:
        """Run complete validation suite."""
        results = {
            'passed': True,
            'violations': [],
            'warnings': [],
            'suggestions': []
        }
        
        # Check main file size
        size_ok, size_msg = self.check_main_file_size()
        if not size_ok:
            results['passed'] = False
            results['violations'].append(f"❌ SIZE: {size_msg}")
        else:
            results['warnings'].append(f"✅ SIZE: {size_msg}")
            
        # Check prohibited patterns
        patterns_ok, pattern_violations = self.check_prohibited_patterns()
        if not patterns_ok:
            results['passed'] = False
            results['violations'].extend([f"❌ PATTERN: {v}" for v in pattern_violations])
        else:
            results['warnings'].append("✅ PATTERNS: No prohibited patterns found")
            
        # Check function complexity
        complexity_ok, complexity_violations = self.check_function_complexity()
        if not complexity_ok:
            results['passed'] = False
            results['violations'].extend([f"❌ COMPLEXITY: {v}" for v in complexity_violations])
        else:
            results['warnings'].append("✅ COMPLEXITY: Functions within limits")
            
        # Check module structure
        structure_ok, missing_dirs = self.check_module_structure()
        if not structure_ok:
            results['warnings'].extend([f"⚠️  STRUCTURE: Missing directory {d}" for d in missing_dirs])
        else:
            results['warnings'].append("✅ STRUCTURE: Required directories exist")
            
        # Generate migration suggestions
        suggestions = self.generate_migration_suggestions()
        results['suggestions'] = suggestions
        
        return results

def main():
    """Main validation entry point."""
    print("🔍 Validating Modular Architecture...")
    print("=" * 60)
    
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    validator = ModularArchitectureValidator(project_root)
    
    results = validator.run_validation()
    
    # Print results
    print(f"\n📊 VALIDATION RESULTS")
    print(f"Main file: {validator.current_line_count} lines")
    print(f"Status: {'✅ PASSED' if results['passed'] else '❌ FAILED'}")
    
    if results['violations']:
        print(f"\n🚨 VIOLATIONS ({len(results['violations'])}):")
        for violation in results['violations']:
            print(f"  {violation}")
            
    if results['warnings']:
        print(f"\n📝 STATUS ({len(results['warnings'])}):")
        for warning in results['warnings']:
            print(f"  {warning}")
            
    if results['suggestions']:
        print(f"\n💡 MIGRATION SUGGESTIONS ({len(results['suggestions'])}):")
        for i, suggestion in enumerate(results['suggestions'][:10], 1):  # Limit to top 10
            print(f"  {i}. {suggestion}")
        if len(results['suggestions']) > 10:
            print(f"  ... and {len(results['suggestions']) - 10} more")
            
    print("\n" + "=" * 60)
    
    if results['passed']:
        print("✅ Modular architecture validation PASSED")
        return 0
    else:
        print("❌ Modular architecture validation FAILED")
        print("\n📋 NEXT STEPS:")
        print("1. Extract functions/classes to appropriate modules")
        print("2. Update imports in main file")
        print("3. Run validation again")
        return 1

if __name__ == "__main__":
    sys.exit(main())
