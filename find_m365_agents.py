#!/usr/bin/env python3
"""
M365 Agent Finder Script
========================
This script helps you identify which M365 agents were deployed using our tool.
"""

import os
import requests
import json
from typing import List, Dict, Any, Optional

def get_access_token() -> Optional[str]:
    """Get access token for Microsoft Graph"""
    tenant_id = os.getenv("M365_TENANT_ID")
    client_id = os.getenv("M365_CLIENT_ID")
    client_secret = os.getenv("M365_CLIENT_SECRET")
    
    if not all([tenant_id, client_id, client_secret]):
        print("❌ M365 credentials not found in environment variables")
        print("Please set: M365_TENANT_ID, M365_CLIENT_ID, M365_CLIENT_SECRET")
        return None
    
    url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "scope": "https://graph.microsoft.com/.default",
        "grant_type": "client_credentials"
    }
    
    try:
        response = requests.post(url, data=data)
        response.raise_for_status()
        return response.json().get("access_token")
    except requests.RequestException as e:
        print(f"❌ Failed to get access token: {e}")
        return None

def list_teams_apps(access_token: str) -> List[Dict[str, Any]]:
    """List all Teams apps in the catalog"""
    url = "https://graph.microsoft.com/v1.0/appCatalogs/teamsApps"
    headers = {"Authorization": f"Bearer {access_token}"}
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json().get("value", [])
    except requests.RequestException as e:
        print(f"❌ Failed to list Teams apps: {e}")
        return []

def find_our_agents(apps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Find agents that match our tool's patterns"""
    our_agents = []
    
    # Common patterns from our tool
    patterns = [
        "Azure Function Proxy",
        "M365 Agent", 
        "Func Proxy",
        "Azure Function Integration",
        "Custom Azure Function Integration",
        "com.contoso.funcproxy"
    ]
    
    for app in apps:
        app_name = (app.get("displayName") or "").lower()
        app_desc = (app.get("shortDescription") or "").lower()
        app_id = app.get("id") or ""
        external_id = (app.get("externalId") or "").lower()
        
        # Check if any of our patterns match
        match_reasons = []
        
        for pattern in patterns:
            pattern_lower = pattern.lower()
            if (pattern_lower in app_name or 
                pattern_lower in app_desc or 
                pattern_lower in external_id):
                match_reasons.append(f"Matches pattern: {pattern}")
        
        # Check for Contoso Corp (our default developer)
        distribution_method = app.get("distributionMethod", "")
        if "contoso" in str(app).lower():
            match_reasons.append("Contains 'Contoso' (our default developer)")
        
        # Check for recent creation (if we can get timestamp)
        created_date = app.get("createdDateTime", "")
        if created_date:
            match_reasons.append(f"Created: {created_date}")
        
        if match_reasons:
            our_agents.append({
                "app": app,
                "match_reasons": match_reasons
            })
    
    return our_agents

def print_agent_details(agent_info: Dict[str, Any]) -> None:
    """Print detailed information about an agent"""
    app = agent_info["app"]
    reasons = agent_info["match_reasons"]
    
    print(f"📱 **{app.get('displayName', 'Unknown')}**")
    print(f"   ID: {app.get('id', 'N/A')}")
    print(f"   External ID: {app.get('externalId', 'N/A')}")
    print(f"   Description: {app.get('shortDescription', 'N/A')}")
    print(f"   Version: {app.get('version', 'N/A')}")
    print(f"   Distribution: {app.get('distributionMethod', 'N/A')}")
    
    if app.get('createdDateTime'):
        print(f"   Created: {app.get('createdDateTime')}")
    
    print("   🔍 Match Reasons:")
    for reason in reasons:
        print(f"      - {reason}")
    print()

def main():
    """Main function to find and display our agents"""
    print("🔍 M365 Agent Finder - Finding agents deployed by our tool")
    print("=" * 60)
    
    # Get access token
    print("🔐 Getting access token...")
    access_token = get_access_token()
    if not access_token:
        return
    
    # List all Teams apps
    print("📋 Listing Teams apps...")
    apps = list_teams_apps(access_token)
    print(f"Found {len(apps)} total apps in catalog")
    
    # Find our agents
    print("\n🎯 Analyzing apps for matches...")
    our_agents = find_our_agents(apps)
    
    if not our_agents:
        print("❌ No agents found matching our tool's patterns")
        print("\n💡 Common agent names from our tool:")
        print("   - Azure Function Proxy")
        print("   - M365 Agent")
        print("   - Func Proxy")
        print("\n💡 Try looking for apps with:")
        print("   - Description containing 'Azure Function Integration'")
        print("   - Developer name 'Contoso Corp'")
        print("   - Recent creation date")
    else:
        print(f"✅ Found {len(our_agents)} potential matches:")
        print()
        
        for i, agent_info in enumerate(our_agents, 1):
            print(f"--- Match #{i} ---")
            print_agent_details(agent_info)
        
        print("💡 To manage these agents:")
        print("   1. Go to Teams Admin Center: https://admin.teams.microsoft.com")
        print("   2. Navigate to: Teams apps → Manage apps")
        print("   3. Search for the agent name(s) listed above")
        print("   4. Set Publishing State = 'Published' to make them available")

if __name__ == "__main__":
    main()
