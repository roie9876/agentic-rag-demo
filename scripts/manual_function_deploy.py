#!/usr/bin/env python3
"""
Manual Function Deployment Script
---------------------------------
Use this script when the UI deployment fails due to SSL certificate issues.
This script provides multiple deployment methods to work around network restrictions.
"""

import os
import sys
import subprocess
import tempfile
from pathlib import Path

def deploy_with_ssl_bypass(resource_group: str, function_name: str):
    """Deploy function with SSL certificate bypass for private networks."""
    
    func_dir = Path.cwd() / "function"
    if not func_dir.exists():
        print(f"❌ Local 'function' folder not found: {func_dir}")
        return False
    
    print(f"🚀 Deploying to Function App: {function_name}")
    print(f"📁 Source directory: {func_dir}")
    
    # Method 1: Try with SSL bypass environment variables
    print("\n🔄 Method 1: Attempting deployment with SSL bypass...")
    
    try:
        # Create deployment zip
        with tempfile.TemporaryDirectory() as td:
            zip_path = Path(td) / "function.zip"
            
            # Zip the function directory
            import zipfile
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in func_dir.rglob('*'):
                    if file_path.is_file():
                        arcname = file_path.relative_to(func_dir)
                        zipf.write(file_path, arcname)
            
            print(f"📦 Created deployment package: {zip_path}")
            
            # Set environment variables to bypass SSL verification
            env = os.environ.copy()
            env['AZURE_CLI_DISABLE_CONNECTION_VERIFICATION'] = '1'
            env['PYTHONHTTPSVERIFY'] = '0'
            env['REQUESTS_CA_BUNDLE'] = ''
            env['CURL_CA_BUNDLE'] = ''
            
            cmd = [
                "az", "functionapp", "deployment", "source", "config-zip",
                "-g", resource_group,
                "-n", function_name,
                "--src", str(zip_path),
                "--verbose"
            ]
            
            print(f"🔧 Running command: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=300,  # 5 minutes
                env=env
            )
            
            if result.returncode == 0:
                print("✅ Deployment successful!")
                print(f"📋 Output: {result.stdout}")
                return True
            else:
                print(f"❌ Deployment failed: {result.stderr}")
                
    except Exception as e:
        print(f"❌ Error during deployment: {e}")
    
    # Method 2: Try with curl if available
    print("\n🔄 Method 2: Attempting deployment with curl...")
    return deploy_with_curl(resource_group, function_name)

def deploy_with_curl(resource_group: str, function_name: str):
    """Alternative deployment using curl with SSL bypass."""
    
    try:
        # Get publishing profile
        cmd_profile = [
            "az", "functionapp", "deployment", "list-publishing-profiles",
            "-g", resource_group,
            "-n", function_name,
            "--query", "[?publishMethod=='ZipDeploy'].{publishUrl:publishUrl,userName:userName,userPWD:userPWD}",
            "--output", "json"
        ]
        
        result = subprocess.run(cmd_profile, capture_output=True, text=True, check=True)
        
        import json
        profiles = json.loads(result.stdout)
        
        if not profiles:
            print("❌ No ZipDeploy profile found")
            return False
        
        profile = profiles[0]
        publish_url = profile['publishUrl']
        username = profile['userName']
        password = profile['userPWD']
        
        # Create zip file
        func_dir = Path.cwd() / "function"
        with tempfile.TemporaryDirectory() as td:
            zip_path = Path(td) / "function.zip"
            
            import zipfile
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in func_dir.rglob('*'):
                    if file_path.is_file():
                        arcname = file_path.relative_to(func_dir)
                        zipf.write(file_path, arcname)
            
            # Use curl with SSL bypass
            curl_cmd = [
                "curl", "-X", "POST",
                "-u", f"{username}:{password}",
                "--data-binary", f"@{zip_path}",
                "-H", "Content-Type: application/octet-stream",
                "-k",  # Ignore SSL certificate errors
                "--connect-timeout", "60",
                "--max-time", "300",
                f"{publish_url}/api/zipdeploy"
            ]
            
            print(f"🔧 Using curl deployment...")
            result = subprocess.run(curl_cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                print("✅ Curl deployment successful!")
                return True
            else:
                print(f"❌ Curl deployment failed: {result.stderr}")
                
    except Exception as e:
        print(f"❌ Curl deployment error: {e}")
    
    return False

def main():
    """Main deployment script."""
    if len(sys.argv) != 3:
        print("Usage: python3 manual_function_deploy.py <resource_group> <function_name>")
        print("Example: python3 manual_function_deploy.py myResourceGroup myFunctionApp")
        sys.exit(1)
    
    resource_group = sys.argv[1]
    function_name = sys.argv[2]
    
    print("🔧 Manual Function Deployment Tool")
    print("=" * 50)
    print(f"Resource Group: {resource_group}")
    print(f"Function Name: {function_name}")
    print("=" * 50)
    
    # Check if function directory exists
    func_dir = Path.cwd() / "function"
    if not func_dir.exists():
        print(f"❌ Function directory not found: {func_dir}")
        print("Make sure you're running this script from the agentic-rag-demo directory")
        sys.exit(1)
    
    success = deploy_with_ssl_bypass(resource_group, function_name)
    
    if success:
        print("\n🎉 Deployment completed successfully!")
    else:
        print("\n❌ All deployment methods failed.")
        print("\n💡 Alternative solutions:")
        print("1. Deploy using Azure Portal (upload zip file)")
        print("2. Use Visual Studio Code Azure Functions extension")
        print("3. Configure your network proxy to trust Azure certificates")
        print("4. Contact your network administrator")

if __name__ == "__main__":
    main()
