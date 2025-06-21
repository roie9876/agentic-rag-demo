#!/usr/bin/env python3
"""
Quick debug to test Document Intelligence URL resolution
"""
import os
from dotenv import load_dotenv
load_dotenv()

print("=== Environment Variables ===")
print(f"DOCUMENT_INTEL_ENDPOINT: {repr(os.getenv('DOCUMENT_INTEL_ENDPOINT'))}")
print(f"AZURE_FORMREC_ENDPOINT: {repr(os.getenv('AZURE_FORMREC_ENDPOINT'))}")
print(f"AZURE_FORMREC_SERVICE: {repr(os.getenv('AZURE_FORMREC_SERVICE'))}")

print("\n=== Testing DocumentIntelligenceClient ===")
try:
    from tools.document_intelligence_client import DocumentIntelligenceClientWrapper
    wrapper = DocumentIntelligenceClientWrapper()
    print(f"DocumentIntelligenceClientWrapper created successfully")
    print(f"Client: {wrapper.client}")
except Exception as e:
    print(f"Error creating DocumentIntelligenceClientWrapper: {e}")

print("\n=== Testing DocumentIntelligenceProcessor ===")
try:
    from tools.doc_intelligence import DocumentIntelligenceProcessor
    processor = DocumentIntelligenceProcessor()
    print(f"DocumentIntelligenceProcessor created successfully")
    print(f"Endpoint: {processor.endpoint}")
    print(f"Service name: {processor.service_name}")
except Exception as e:
    print(f"Error creating DocumentIntelligenceProcessor: {e}")
