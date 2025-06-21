#!/usr/bin/env python3
import os
import sys
from pathlib import Path

# Minimal test for Document Intelligence
print("🚀 Starting Document Intelligence test...")

# Load environment manually
env_file = Path(__file__).resolve().parent / ".env"
if env_file.exists():
    with open(env_file, 'r') as f:
        for line in f:
            if '=' in line and not line.startswith('#'):
                key, value = line.strip().split('=', 1)
                # Handle variable expansion like ${OTHER_VAR}
                while '${' in value and '}' in value:
                    start = value.find('${')
                    end = value.find('}', start)
                    if start != -1 and end != -1:
                        var_name = value[start+2:end]
                        var_value = os.environ.get(var_name, '')
                        value = value[:start] + var_value + value[end+1:]
                    else:
                        break
                os.environ[key] = value
    print("✅ Environment loaded manually")

endpoint = os.getenv("DOCUMENT_INTEL_ENDPOINT")
key = os.getenv("DOCUMENT_INTEL_KEY")
print(f"🌐 Endpoint: {endpoint}")
print(f"🔑 Key: {'*' * 10 if key else 'None'}")

# Test PDF exists
pdf_path = "/Users/robenhai/Downloads/תעשייה אווירית – ויקיפדיה.pdf"
print(f"📁 PDF exists: {os.path.exists(pdf_path)}")

if os.path.exists(pdf_path):
    with open(pdf_path, 'rb') as f:
        file_bytes = f.read()
    print(f"📊 File size: {len(file_bytes):,} bytes")

print("✅ Basic test completed")
