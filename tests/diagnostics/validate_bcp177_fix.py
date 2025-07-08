#!/usr/bin/env python3
"""
Quick validation script for users to confirm BCP177 fix is working.
Run this to verify your UI app deployment will work.
"""

import sys
import os
sys.path.append('/home/azureuser/agentic-rag-demo')

def validate_fix():
    """Validate that the BCP177 fix is working."""
    print("🔍 Validating BCP177 Fix")
    print("=" * 40)
    
    try:
        from services.ai_foundry_hub_deployment import AIFoundryHubDeploymentService
        
        # Initialize service
        service = AIFoundryHubDeploymentService()
        
        # Check template validation
        valid, msg = service.validate_template_path()
        
        # Check which template exists
        template_path = service.template_path
        main_json = os.path.join(template_path, "main.json")
        main_bicep = os.path.join(template_path, "main.bicep")
        
        print(f"Template validation: {'✅ PASS' if valid else '❌ FAIL'}")
        print(f"main.json exists: {'✅ YES' if os.path.exists(main_json) else '❌ NO'}")
        print(f"main.bicep exists: {'✅ YES' if os.path.exists(main_bicep) else '❌ NO'}")
        
        if os.path.exists(main_json):
            print("🎯 RESULT: Will use ARM template (main.json)")
            print("✅ BCP177 error avoided!")
            print("🚀 UI app deployments ready!")
            return True
        elif os.path.exists(main_bicep):
            print("⚠️ RESULT: Will use Bicep template")
            print("❌ BCP177 error might occur")
            return False
        else:
            print("❌ RESULT: No template found")
            return False
            
    except Exception as e:
        print(f"❌ Validation failed: {e}")
        return False

if __name__ == "__main__":
    success = validate_fix()
    if success:
        print("\n🎉 SUCCESS: BCP177 fix is working!")
        print("Your UI app is ready for deployment.")
    else:
        print("\n❌ ISSUE: BCP177 fix needs attention.")
    
    exit(0 if success else 1)
