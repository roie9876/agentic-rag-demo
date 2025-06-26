#!/usr/bin/env python3
"""
M365 Agent Deployment Test Suite
===============================
Comprehensive test script to verify M365 app registration setup and test deployment.
This script will help you identify and fix issues before attempting actual deployment.
"""

import os
import requests
import json
import tempfile
import zipfile
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict, Any, Tuple, Optional

# Load environment variables
load_dotenv()

class M365TestSuite:
    def __init__(self):
        self.tenant_id = os.getenv('M365_TENANT_ID')
        self.client_id = os.getenv('M365_CLIENT_ID')
        self.client_secret = os.getenv('M365_CLIENT_SECRET')
        self.access_token = None
        
    def print_header(self, title: str):
        """Print a formatted header"""
        print("\n" + "=" * 60)
        print(f"🧪 {title}")
        print("=" * 60)
    
    def print_step(self, step: str, status: str = ""):
        """Print a test step"""
        if status == "PASS":
            print(f"✅ {step}")
        elif status == "FAIL":
            print(f"❌ {step}")
        elif status == "WARN":
            print(f"⚠️ {step}")
        else:
            print(f"🔍 {step}")
    
    def test_environment_variables(self) -> bool:
        """Test 1: Check if all required environment variables are set"""
        self.print_header("Test 1: Environment Variables")
        
        all_good = True
        
        if self.tenant_id:
            self.print_step(f"M365_TENANT_ID: {self.tenant_id}", "PASS")
        else:
            self.print_step("M365_TENANT_ID: NOT SET", "FAIL")
            all_good = False
            
        if self.client_id:
            self.print_step(f"M365_CLIENT_ID: {self.client_id}", "PASS")
        else:
            self.print_step("M365_CLIENT_ID: NOT SET", "FAIL")
            all_good = False
            
        if self.client_secret:
            masked_secret = "*" * len(self.client_secret)
            self.print_step(f"M365_CLIENT_SECRET: {masked_secret}", "PASS")
        else:
            self.print_step("M365_CLIENT_SECRET: NOT SET", "FAIL")
            all_good = False
            
        return all_good
    
    def test_authentication(self) -> bool:
        """Test 2: Test authentication with Microsoft Graph"""
        self.print_header("Test 2: Authentication")
        
        if not all([self.tenant_id, self.client_id, self.client_secret]):
            self.print_step("Skipping authentication test - missing credentials", "FAIL")
            return False
        
        token_url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
        
        data = {
            'grant_type': 'client_credentials',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'scope': 'https://graph.microsoft.com/.default'
        }
        
        try:
            self.print_step("Requesting access token from Microsoft Graph...")
            response = requests.post(token_url, data=data)
            
            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data.get('access_token')
                
                if self.access_token:
                    self.print_step("Authentication successful", "PASS")
                    
                    # Show token info
                    expires_in = token_data.get('expires_in', 0)
                    token_type = token_data.get('token_type', 'Unknown')
                    self.print_step(f"Token type: {token_type}, expires in: {expires_in}s", "PASS")
                    return True
                else:
                    self.print_step("No access token in response", "FAIL")
                    return False
            else:
                error_data = response.json() if response.content else {}
                error_desc = error_data.get('error_description', 'Unknown error')
                
                self.print_step(f"Authentication failed: HTTP {response.status_code}", "FAIL")
                self.print_step(f"Error: {error_desc}", "FAIL")
                
                # Provide specific troubleshooting
                if 'invalid_client' in error_desc:
                    self.print_step("💡 Fix: Check M365_CLIENT_ID and M365_CLIENT_SECRET values", "WARN")
                elif 'invalid_request' in error_desc:
                    self.print_step("💡 Fix: Check M365_TENANT_ID value", "WARN")
                
                return False
                
        except Exception as e:
            self.print_step(f"Authentication error: {e}", "FAIL")
            return False
    
    def test_permissions(self) -> bool:
        """Test 3: Check app permissions"""
        self.print_header("Test 3: Application Permissions")
        
        if not self.access_token:
            self.print_step("Skipping permissions test - no access token", "FAIL")
            return False
        
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        
        try:
            # Get service principal information
            sp_url = f"https://graph.microsoft.com/v1.0/servicePrincipals?$filter=appId eq '{self.client_id}'"
            sp_response = requests.get(sp_url, headers=headers)
            
            if sp_response.status_code == 200:
                sp_data = sp_response.json()
                if sp_data.get('value'):
                    sp = sp_data['value'][0]
                    app_name = sp.get('displayName', 'Unknown')
                    self.print_step(f"Found app registration: {app_name}", "PASS")
                    
                    # Get app role assignments
                    sp_id = sp.get('id')
                    ara_url = f"https://graph.microsoft.com/v1.0/servicePrincipals/{sp_id}/appRoleAssignments"
                    ara_response = requests.get(ara_url, headers=headers)
                    
                    if ara_response.status_code == 200:
                        assignments = ara_response.json().get('value', [])
                        
                        required_permissions = ['AppCatalog.Submit', 'AppCatalog.ReadWrite.All']
                        found_permissions = []
                        
                        for assignment in assignments:
                            resource_id = assignment.get('resourceId')
                            if resource_id:
                                # Get role details
                                role_url = f"https://graph.microsoft.com/v1.0/servicePrincipals/{resource_id}"
                                role_response = requests.get(role_url, headers=headers)
                                
                                if role_response.status_code == 200:
                                    role_data = role_response.json()
                                    if role_data.get('displayName') == 'Microsoft Graph':
                                        app_roles = role_data.get('appRoles', [])
                                        role_id = assignment.get('appRoleId')
                                        
                                        for role in app_roles:
                                            if role.get('id') == role_id:
                                                permission_name = role.get('value')
                                                found_permissions.append(permission_name)
                                                self.print_step(f"Found permission: {permission_name}", "PASS")
                        
                        # Check if we have required permissions
                        has_submit = 'AppCatalog.Submit' in found_permissions
                        has_readwrite = 'AppCatalog.ReadWrite.All' in found_permissions
                        
                        if has_submit:
                            self.print_step("Required permission AppCatalog.Submit: FOUND", "PASS")
                        else:
                            self.print_step("Required permission AppCatalog.Submit: MISSING", "FAIL")
                        
                        if has_readwrite:
                            self.print_step("Optional permission AppCatalog.ReadWrite.All: FOUND", "PASS")
                        else:
                            self.print_step("Optional permission AppCatalog.ReadWrite.All: NOT FOUND", "WARN")
                        
                        return has_submit
                    else:
                        self.print_step(f"Could not get app role assignments: {ara_response.status_code}", "FAIL")
                        return False
                else:
                    self.print_step("Service principal not found", "FAIL")
                    return False
            else:
                self.print_step(f"Could not get service principal: {sp_response.status_code}", "FAIL")
                return False
                
        except Exception as e:
            self.print_step(f"Permissions check error: {e}", "FAIL")
            return False
    
    def test_app_catalog_access(self) -> bool:
        """Test 4: Test access to app catalog API"""
        self.print_header("Test 4: App Catalog API Access")
        
        if not self.access_token:
            self.print_step("Skipping app catalog test - no access token", "FAIL")
            return False
        
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        
        try:
            # Try to access the app catalog
            catalog_url = "https://graph.microsoft.com/v1.0/appCatalogs/teamsApps"
            self.print_step("Testing access to Teams App Catalog...")
            
            response = requests.get(catalog_url, headers=headers)
            
            if response.status_code == 200:
                apps_data = response.json()
                app_count = len(apps_data.get('value', []))
                self.print_step(f"App catalog access successful - found {app_count} apps", "PASS")
                return True
            elif response.status_code == 403:
                error_data = response.json() if response.content else {}
                error_msg = error_data.get('error', {}).get('message', 'Access denied')
                self.print_step(f"App catalog access denied: {error_msg}", "FAIL")
                self.print_step("💡 This means you need Application permissions (not Delegated)", "WARN")
                return False
            else:
                self.print_step(f"App catalog access failed: HTTP {response.status_code}", "FAIL")
                return False
                
        except Exception as e:
            self.print_step(f"App catalog test error: {e}", "FAIL")
            return False
    
    def create_test_package(self) -> Optional[Path]:
        """Create a test M365 app package"""
        try:
            # Create temporary directory
            temp_dir = Path(tempfile.mkdtemp())
            
            # Create manifest.json
            manifest = {
                "$schema": "https://developer.microsoft.com/en-us/json-schemas/teams/v1.16/MicrosoftTeams.schema.json",
                "manifestVersion": "1.16",
                "id": "test-app-12345",
                "version": "1.0.0",
                "packageName": "com.test.m365agent",
                "developer": {
                    "name": "Test Corp",
                    "websiteUrl": "https://test.com",
                    "privacyUrl": "https://test.com/privacy",
                    "termsOfUseUrl": "https://test.com/terms"
                },
                "name": {
                    "short": "Test M365 Agent",
                    "full": "Test M365 Agent - Integration Test"
                },
                "description": {
                    "short": "Test app for M365 Agent",
                    "full": "A test M365 Copilot plugin for testing deployment"
                },
                "icons": {
                    "outline": "outline.png",
                    "color": "color.png"
                },
                "accentColor": "#FFFFFF",
                "copilotAgents": {
                    "declarativeAgents": [
                        {
                            "id": "com.test.agent",
                            "file": "plugin.json"
                        }
                    ]
                }
            }
            
            # Create plugin.json
            plugin = {
                "$schema": "https://developer.microsoft.com/en-us/microsoft-365/copilot/schema/api-plugin-manifest.2.2.json",
                "id": "com.test.agent",
                "name": "Test Agent",
                "description": "Test agent for deployment testing",
                "version": "1.0.0",
                "api": {
                    "openapi": {
                        "url": "./openapi.json"
                    },
                    "auth": {
                        "type": "apiKey",
                        "keyHeaderName": "x-functions-key"
                    }
                }
            }
            
            # Create openapi.json
            openapi = {
                "openapi": "3.0.3",
                "info": {
                    "title": "Test API",
                    "description": "Test API for M365 Agent",
                    "version": "1.0.0"
                },
                "servers": [
                    {"url": "https://test-function.azurewebsites.net"}
                ],
                "paths": {
                    "/api/test": {
                        "post": {
                            "operationId": "testFunction",
                            "summary": "Test function",
                            "description": "Test endpoint",
                            "requestBody": {
                                "required": True,
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "object",
                                            "properties": {
                                                "question": {"type": "string"}
                                            }
                                        }
                                    }
                                }
                            },
                            "responses": {
                                "200": {
                                    "description": "Success",
                                    "content": {
                                        "application/json": {
                                            "schema": {"type": "object"}
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
            
            # Write files
            with open(temp_dir / "manifest.json", "w") as f:
                json.dump(manifest, f, indent=2)
            
            with open(temp_dir / "plugin.json", "w") as f:
                json.dump(plugin, f, indent=2)
            
            with open(temp_dir / "openapi.json", "w") as f:
                json.dump(openapi, f, indent=2)
            
            # Create placeholder icons
            (temp_dir / "color.png").write_bytes(b"PNG_PLACEHOLDER")
            (temp_dir / "outline.png").write_bytes(b"PNG_PLACEHOLDER")
            
            # Create zip file
            zip_path = temp_dir / "test-package.zip"
            with zipfile.ZipFile(zip_path, 'w') as zipf:
                for file_path in temp_dir.iterdir():
                    if file_path.is_file() and file_path.name != "test-package.zip":
                        zipf.write(file_path, file_path.name)
            
            return zip_path
            
        except Exception as e:
            print(f"❌ Failed to create test package: {e}")
            return None
    
    def test_package_upload(self, dry_run: bool = True) -> bool:
        """Test 5: Test package upload (dry run by default)"""
        self.print_header(f"Test 5: Package Upload {'(DRY RUN)' if dry_run else '(LIVE)'}")
        
        if not self.access_token:
            self.print_step("Skipping upload test - no access token", "FAIL")
            return False
        
        if dry_run:
            self.print_step("Creating test package...", "")
            test_package = self.create_test_package()
            
            if not test_package:
                self.print_step("Failed to create test package", "FAIL")
                return False
            
            self.print_step(f"Test package created: {test_package}", "PASS")
            self.print_step("DRY RUN: Would upload package to Microsoft Graph", "PASS")
            self.print_step("To perform actual upload, run with dry_run=False", "WARN")
            
            # Clean up
            test_package.unlink()
            try:
                test_package.parent.rmdir()
            except OSError:
                pass  # Directory might not be empty, ignore
            
            return True
        else:
            # Actual upload test - BE CAREFUL!
            self.print_step("⚠️ LIVE UPLOAD TEST - This will create a real app!", "WARN")
            
            test_package = self.create_test_package()
            if not test_package:
                return False
            
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/zip'
            }
            
            try:
                upload_url = "https://graph.microsoft.com/v1.0/appCatalogs/teamsApps"
                
                with open(test_package, "rb") as f:
                    response = requests.post(upload_url, headers=headers, data=f)
                
                if response.status_code in [200, 201]:
                    result = response.json()
                    app_id = result.get('id', 'Unknown')
                    self.print_step(f"Upload successful! App ID: {app_id}", "PASS")
                    self.print_step("⚠️ Remember to delete the test app from Teams Admin Center", "WARN")
                    return True
                else:
                    error_data = response.json() if response.content else {}
                    self.print_step(f"Upload failed: HTTP {response.status_code}", "FAIL")
                    self.print_step(f"Error: {error_data}", "FAIL")
                    return False
                    
            except Exception as e:
                self.print_step(f"Upload test error: {e}", "FAIL")
                return False
            finally:
                # Clean up
                if test_package.exists():
                    test_package.unlink()
                try:
                    test_package.parent.rmdir()
                except OSError:
                    pass  # Directory might not be empty, ignore
    
    def run_all_tests(self, live_upload: bool = False) -> Dict[str, bool]:
        """Run all tests and return results"""
        print("🧪 M365 Agent Deployment Test Suite")
        print("=" * 60)
        print("This script will test your M365 app registration setup")
        print("and verify that deployment will work correctly.")
        print()
        
        results = {}
        
        # Run tests in sequence
        results['environment'] = self.test_environment_variables()
        results['authentication'] = self.test_authentication()
        results['permissions'] = self.test_permissions()
        results['app_catalog'] = self.test_app_catalog_access()
        results['upload'] = self.test_package_upload(dry_run=not live_upload)
        
        # Print summary
        self.print_header("Test Summary")
        
        all_passed = True
        for test_name, passed in results.items():
            status = "PASS" if passed else "FAIL"
            self.print_step(f"{test_name.replace('_', ' ').title()}: {status}", status)
            if not passed:
                all_passed = False
        
        print("\n" + "=" * 60)
        if all_passed:
            print("🎉 ALL TESTS PASSED! Your M365 Agent deployment should work!")
        else:
            print("❌ Some tests failed. Please fix the issues above before deployment.")
            print("\n💡 Common fixes:")
            print("- Ensure you have Application permissions (not Delegated)")
            print("- Grant admin consent for permissions")
            print("- Check that credentials in .env are correct")
        print("=" * 60)
        
        return results


def main():
    """Main test runner"""
    import argparse
    
    parser = argparse.ArgumentParser(description='M365 Agent Deployment Test Suite')
    parser.add_argument('--live-upload', action='store_true', 
                        help='Perform actual upload test (creates real app)')
    parser.add_argument('--verbose', action='store_true', 
                        help='Enable verbose output')
    
    args = parser.parse_args()
    
    if args.live_upload:
        print("⚠️ WARNING: Live upload test will create a real app in your tenant!")
        confirm = input("Continue? (yes/no): ")
        if confirm.lower() != 'yes':
            print("Test cancelled.")
            return
    
    # Run tests
    test_suite = M365TestSuite()
    results = test_suite.run_all_tests(live_upload=args.live_upload)
    
    # Exit with appropriate code
    exit_code = 0 if all(results.values()) else 1
    exit(exit_code)


if __name__ == "__main__":
    main()
