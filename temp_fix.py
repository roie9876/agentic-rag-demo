#!/usr/bin/env python3
"""
Temporary script to fix the IndentationError in agentic-rag-demo.py
by removing orphaned indented lines.
"""

def fix_indentation_error():
    """Remove orphaned indented lines from agentic-rag-demo.py"""
    input_file = "/home/azureuser/agentic-rag-demo/agentic-rag-demo.py"
    
    with open(input_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Find and remove the orphaned lines (around line 86-95)
    fixed_lines = []
    skip_lines = False
    
    for i, line in enumerate(lines):
        line_num = i + 1
        
        # Skip the orphaned indented block (lines 86-95)
        if line_num == 86 and line.strip().startswith('"""'):
            # Start skipping orphaned lines
            skip_lines = True
            continue
        elif skip_lines and line_num <= 95:
            # Continue skipping until we hit the duplicate comment
            if "# Reliable check whether code runs under" in line:
                skip_lines = False
                # Don't add this line as it's a duplicate
                continue
            else:
                continue
        
        # Add all other lines
        fixed_lines.append(line)
    
    # Write the fixed content back
    with open(input_file, 'w', encoding='utf-8') as f:
        f.writelines(fixed_lines)
    
    print("✅ Fixed IndentationError in agentic-rag-demo.py")

if __name__ == "__main__":
    fix_indentation_error()
