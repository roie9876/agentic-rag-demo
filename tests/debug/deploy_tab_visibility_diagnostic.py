#!/usr/bin/env python3
"""
Deploy Tab Visibility Diagnostic
================================
Diagnose why the subscription selection is not visible in the Deploy tab.
This script simulates the exact conditions and checks that occur in the Deploy tab.
"""

import sys
import os
import streamlit as st
from typing import Dict, Any, List, Optional
import logging

# Add project root to path
sys.path.insert(0, '/home/azureuser/agentic-rag-demo')

from services.ai_foundry_hub_deployment import AIFoundryHubDeploymentService, AIFoundryHubDeploymentConfig

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DeployTabDiagnostic:
    """Diagnostic tool for Deploy tab visibility issues."""
    
    def __init__(self):
        """Initialize the diagnostic."""
        self.service = AIFoundryHubDeploymentService()
    
    def create_complete_configuration(self) -> AIFoundryHubDeploymentConfig:
        """Create a complete mock configuration for testing."""
        config = AIFoundryHubDeploymentConfig()
        
        # Fill in required fields
        config.display_name = "Test AI Foundry Hub"
        config.description = "Test deployment for diagnostic"
        
        # Ensure all basic settings
        if hasattr(config, 'basic_settings') and config.basic_settings:
            config.basic_settings.display_name = "Test AI Foundry Hub"
            config.basic_settings.description = "Test deployment"
        
        return config
    
    def check_template_validation(self) -> bool:
        """Check if template validation passes."""
        print("\n🔍 Step 1: Template Validation")
        print("=" * 50)
        
        valid, msg = self.service.validate_template_path()
        print(f"Template validation: {'✅ PASS' if valid else '❌ FAIL'}")
        if not valid:
            print(f"❌ Error: {msg}")
            return False
        else:
            print(f"✅ Success: {msg}")
            return True
    
    def check_session_state_config(self) -> bool:
        """Check if deployment_config exists in session state."""
        print("\n🔍 Step 2: Session State Configuration")
        print("=" * 50)
        
        # Create a mock complete configuration
        complete_config = self.create_complete_configuration()
        
        # Simulate session state
        mock_session_state = {
            'deployment_config': complete_config
        }
        
        print(f"Mock deployment_config exists: {'✅ YES' if 'deployment_config' in mock_session_state else '❌ NO'}")
        
        if 'deployment_config' in mock_session_state:
            config = mock_session_state['deployment_config']
            print(f"Configuration type: {type(config)}")
            
            # Check key fields
            if hasattr(config, 'basic_settings'):
                print(f"✅ basic_settings exists: {config.basic_settings is not None}")
            if hasattr(config, 'network_config'):
                print(f"✅ network_config exists: {config.network_config is not None}")
            if hasattr(config, 'dns_config'):
                print(f"✅ dns_config exists: {config.dns_config is not None}")
            
            return True
        else:
            print("❌ deployment_config missing from session state")
            return False
    
    def check_config_validation(self) -> bool:
        """Check if configuration validation passes."""
        print("\n🔍 Step 3: Configuration Validation")
        print("=" * 50)
        
        # Create complete configuration
        complete_config = self.create_complete_configuration()
        
        # Validate configuration
        issues = self.service.validate_deployment_config(complete_config)
        
        print(f"Configuration validation: {'✅ PASS' if not issues else '❌ FAIL'}")
        
        if issues:
            print("❌ Configuration issues found:")
            for i, issue in enumerate(issues, 1):
                print(f"   {i}. {issue}")
            return False
        else:
            print("✅ No configuration issues found")
            return True
    
    def check_subscription_loading(self) -> bool:
        """Check if subscriptions load successfully."""
        print("\n🔍 Step 4: Subscription Loading")
        print("=" * 50)
        
        try:
            subscriptions = self.service.get_prioritized_subscriptions()
            
            if subscriptions:
                print(f"✅ Subscriptions loaded: {len(subscriptions)} found")
                
                enabled_count = sum(1 for sub in subscriptions if sub.get('state') == 'Enabled')
                print(f"✅ Enabled subscriptions: {enabled_count}")
                
                # Show first few subscriptions
                print("\nSubscription details:")
                for i, sub in enumerate(subscriptions[:3]):
                    status = "✅" if sub.get('state') == 'Enabled' else "⚠️"
                    print(f"   {status} {sub.get('display_name', 'Unknown')} ({sub.get('subscription_id', 'Unknown')[:8]}...)")
                
                if len(subscriptions) > 3:
                    print(f"   ... and {len(subscriptions) - 3} more")
                
                return enabled_count > 0
            else:
                print("❌ No subscriptions returned")
                return False
                
        except Exception as e:
            print(f"❌ Error loading subscriptions: {str(e)}")
            return False
    
    def check_current_subscription(self) -> bool:
        """Check if current subscription info is available."""
        print("\n🔍 Step 5: Current Subscription Info")
        print("=" * 50)
        
        try:
            current_sub_info = self.service.get_current_subscription_info()
            
            if current_sub_info:
                print("✅ Current subscription info available:")
                print(f"   ID: {current_sub_info.get('subscription_id', 'Unknown')}")
                print(f"   Name: {current_sub_info.get('display_name', 'Unknown')}")
                print(f"   State: {current_sub_info.get('state', 'Unknown')}")
                return True
            else:
                print("❌ Current subscription info not available")
                return False
                
        except Exception as e:
            print(f"❌ Error getting current subscription: {str(e)}")
            return False
    
    def simulate_ui_conditions(self) -> Dict[str, Any]:
        """Simulate the exact conditions in the Deploy tab UI."""
        print("\n🔍 Step 6: UI Condition Simulation")
        print("=" * 50)
        
        # Simulate the exact flow in _render_deploy_tab
        conditions = {
            'template_valid': False,
            'config_exists': False,
            'config_valid': False,
            'subscriptions_loaded': False,
            'ui_should_render': False
        }
        
        # Step 1: Template validation
        valid, msg = self.service.validate_template_path()
        conditions['template_valid'] = valid
        print(f"Template validation: {'✅' if valid else '❌'}")
        
        if not valid:
            print("❌ UI will show template error and return early")
            return conditions
        
        # Step 2: Check session state (simulated)
        complete_config = self.create_complete_configuration()
        mock_session_state = {'deployment_config': complete_config}
        
        conditions['config_exists'] = 'deployment_config' in mock_session_state
        print(f"Configuration exists: {'✅' if conditions['config_exists'] else '❌'}")
        
        if not conditions['config_exists']:
            print("❌ UI will show 'Please configure the deployment first' warning and return early")
            return conditions
        
        # Step 3: Configuration validation
        config = mock_session_state['deployment_config']
        issues = self.service.validate_deployment_config(config)
        conditions['config_valid'] = not issues
        print(f"Configuration valid: {'✅' if conditions['config_valid'] else '❌'}")
        
        if issues:
            print("❌ UI will show configuration issues and return early")
            print("Issues found:")
            for issue in issues:
                print(f"   - {issue}")
            return conditions
        
        # Step 4: Load subscriptions
        try:
            subscriptions = self.service.get_prioritized_subscriptions()
            conditions['subscriptions_loaded'] = bool(subscriptions and any(sub.get('state') == 'Enabled' for sub in subscriptions))
            print(f"Subscriptions loaded: {'✅' if conditions['subscriptions_loaded'] else '❌'}")
            
            if not conditions['subscriptions_loaded']:
                print("❌ UI will show subscription error and return early")
                return conditions
                
        except Exception as e:
            print(f"❌ Error loading subscriptions: {str(e)}")
            return conditions
        
        # If we reach here, the subscription selection UI should render
        conditions['ui_should_render'] = True
        print("✅ All conditions met - subscription selection UI should render!")
        
        return conditions
    
    def check_specific_ui_elements(self) -> None:
        """Check for specific UI elements that might prevent rendering."""
        print("\n🔍 Step 7: Specific UI Element Checks")
        print("=" * 50)
        
        # Check for session state key conflicts
        potential_conflicts = [
            'deployment_subscription_id',
            'deploy_subscription_selector', 
            'deployment_resource_group',
            'ai_foundry_deployment_service'
        ]
        
        print("Checking for potential session state conflicts:")
        for key in potential_conflicts:
            print(f"   {key}: Not in session state (expected)")
        
        # Check for subscription option creation
        try:
            subscriptions = self.service.get_prioritized_subscriptions()
            current_sub_info = self.service.get_current_subscription_info()
            current_sub_id = current_sub_info['subscription_id'] if current_sub_info else None
            
            subscription_options = {}
            for sub in subscriptions:
                if sub['state'] == 'Enabled':
                    label = f"{sub['display_name']} ({sub['subscription_id']})"
                    if sub['subscription_id'] == current_sub_id:
                        label = f"🌟 {label} (Current)"
                    subscription_options[label] = sub['subscription_id']
            
            print(f"\nSubscription options would be created: {len(subscription_options)} options")
            print("Sample options:")
            for i, (label, sub_id) in enumerate(list(subscription_options.items())[:3]):
                print(f"   {i+1}. {label} -> {sub_id[:8]}...")
                
            if len(subscription_options) > 3:
                print(f"   ... and {len(subscription_options) - 3} more")
                
        except Exception as e:
            print(f"❌ Error creating subscription options: {str(e)}")
    
    def run_full_diagnostic(self) -> None:
        """Run the complete diagnostic."""
        print("🔍 Deploy Tab Visibility Diagnostic")
        print("=" * 60)
        print("This diagnostic checks why subscription selection might not be visible in the Deploy tab.")
        print()
        
        # Run all checks
        template_ok = self.check_template_validation()
        config_ok = self.check_session_state_config()
        validation_ok = self.check_config_validation()
        subscriptions_ok = self.check_subscription_loading()
        current_sub_ok = self.check_current_subscription()
        
        # Simulate UI conditions
        conditions = self.simulate_ui_conditions()
        
        # Check specific UI elements
        self.check_specific_ui_elements()
        
        # Final summary
        print("\n🎯 DIAGNOSTIC SUMMARY")
        print("=" * 60)
        
        all_checks = [
            ("Template Validation", template_ok),
            ("Session State Config", config_ok),
            ("Config Validation", validation_ok),
            ("Subscription Loading", subscriptions_ok),
            ("Current Subscription", current_sub_ok),
            ("UI Should Render", conditions['ui_should_render'])
        ]
        
        for check_name, status in all_checks:
            status_icon = "✅" if status else "❌"
            print(f"{status_icon} {check_name}")
        
        print()
        
        if conditions['ui_should_render']:
            print("🎉 CONCLUSION: All backend conditions are met!")
            print("   The subscription selection UI should be visible.")
            print("   If it's not visible in the Streamlit app, this suggests:")
            print("   1. 🔄 Session state issue in live app")
            print("   2. 🐛 UI rendering bug")
            print("   3. 🌐 Browser/JavaScript issue")
            print("   4. 📱 Streamlit caching issue")
            print()
            print("🔧 RECOMMENDED ACTIONS:")
            print("   1. Restart the Streamlit app (Ctrl+C, then restart)")
            print("   2. Clear browser cache and refresh")
            print("   3. Try a different browser")
            print("   4. Check browser console for JavaScript errors")
            print("   5. Check Streamlit logs for warnings/errors")
        else:
            print("❌ CONCLUSION: Backend conditions not met")
            failed_checks = [name for name, status in all_checks if not status]
            print(f"   Failed checks: {', '.join(failed_checks)}")
            print("   The subscription selection should not be visible until these are fixed.")

def main():
    """Main function."""
    print("Starting Deploy Tab Visibility Diagnostic...")
    
    diagnostic = DeployTabDiagnostic()
    diagnostic.run_full_diagnostic()
    
    print("\n✅ Diagnostic complete!")

if __name__ == "__main__":
    main()
