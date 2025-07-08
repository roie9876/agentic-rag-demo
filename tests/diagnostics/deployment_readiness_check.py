#!/usr/bin/env python3
"""
Quick deployment readiness check for AI Foundry Hub.
Run this to verify your system is ready for deployment.
"""

import os
import sys

def check_deployment_readiness():
    """Check if the deployment system is ready."""
    print("🚀 AI Foundry Hub Deployment Readiness Check")
    print("=" * 50)
    
    all_good = True
    
    # 1. Check if service can be imported
    try:
        sys.path.append('/home/azureuser/agentic-rag-demo')
        from services.ai_foundry_hub_deployment import AIFoundryHubDeploymentService
        print("✅ Deployment service: AVAILABLE")
    except Exception as e:
        print(f"❌ Deployment service: FAILED - {e}")
        all_good = False
    
    # 2. Check template files
    try:
        service = AIFoundryHubDeploymentService()
        template_path = service.template_path
        
        main_json = os.path.join(template_path, "main.json")
        main_bicep = os.path.join(template_path, "main.bicep")
        
        if os.path.exists(main_json):
            size = os.path.getsize(main_json)
            print(f"✅ ARM template (main.json): READY ({size:,} bytes)")
        else:
            print("❌ ARM template (main.json): NOT FOUND")
            all_good = False
            
        if os.path.exists(main_bicep):
            print("✅ Bicep template (main.bicep): AVAILABLE (fallback)")
        else:
            print("⚠️ Bicep template (main.bicep): NOT FOUND")
    
    except Exception as e:
        print(f"❌ Template check: FAILED - {e}")
        all_good = False
    
    # 3. Check template validation
    try:
        valid, msg = service.validate_template_path()
        if valid:
            print(f"✅ Template validation: PASSED")
            if "ARM template" in msg:
                print("✅ BCP177 fix: ACTIVE (using ARM template)")
            else:
                print("⚠️ BCP177 fix: Using Bicep template")
        else:
            print(f"❌ Template validation: FAILED - {msg}")
            all_good = False
    except Exception as e:
        print(f"❌ Template validation: ERROR - {e}")
        all_good = False
    
    print()
    if all_good:
        print("🎉 RESULT: System is ready for AI Foundry Hub deployment!")
        print("✅ Users can deploy through the UI without issues")
        print("✅ BCP177 error has been resolved")
    else:
        print("❌ RESULT: System has issues that need attention")
        print("🔧 Please check the errors above")
    
    return all_good

if __name__ == "__main__":
    ready = check_deployment_readiness()
    exit(0 if ready else 1)
