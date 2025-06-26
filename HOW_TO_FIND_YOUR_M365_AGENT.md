# Finding Your Deployed M365 Agent

## 🎯 **Agent Identification Guide**

### **Default Agent Names**
Your deployed agent will have one of these names (depending on when it was deployed):

1. **"Azure Function Proxy"** (newest default)
2. **"M365 Agent"** (previous default)  
3. **"Func Proxy"** (original default)
4. **Custom name** if you changed it in the UI

### **Key Identifiers**

| Property | Value |
|----------|-------|
| **Name** | Azure Function Proxy (or custom) |
| **Description** | Custom Azure Function Integration |
| **Developer** | Contoso Corp |
| **Plugin ID** | com.contoso.funcproxy |
| **Type** | Copilot |
| **Icon** | Blue with "Azure Function" text |

### **Where to Look**

#### **In M365 Copilot:**
- Open Microsoft 365 Copilot
- Look for agents in the "Built by your org" section
- Search for the agent name

#### **In Teams Admin Center:**
1. Go to https://admin.teams.microsoft.com
2. Navigate to **Teams apps** → **Manage apps**
3. Sort by **"Date created"** (newest first)
4. Look for agents with the names above

### **Visual Identification in Your Screenshot**

Looking at your screenshot, your agent should appear similar to the others but with these specific characteristics:

- **Name**: "Azure Function Proxy" (or the name you chose)
- **Subtitle**: "Copilot" 
- **Description**: "Built using Microsoft Copilot Studio"
- **Icon**: Blue background with "AF" or "Azure Function" text

### **Quick Search Commands**

#### **Using the Find Script:**
```bash
python find_m365_agents.py
```
This will automatically scan your M365 tenant and identify agents deployed by our tool.

#### **PowerShell Search:**
```powershell
Connect-MicrosoftTeams
Get-TeamsApp | Where-Object {$_.DisplayName -like "*Azure Function*" -or $_.DisplayName -like "*M365 Agent*" -or $_.DisplayName -like "*Func Proxy*"}
```

### **Common Issues**

#### **"I Can't Find My Agent"**
1. **Check recent deployments** - Sort by date created
2. **Search for "Azure Function"** in the Teams Admin Center
3. **Look for "Contoso Corp"** as developer
4. **Check if deployment actually succeeded** - Review the deployment logs

#### **"I Have Multiple Similar Agents"**
1. **Check the Plugin ID** - Should be `com.contoso.funcproxy`
2. **Check creation date** - Find the most recent one
3. **Check description** - Should mention "Azure Function Integration"

### **Agent Usage**

Once you find your agent, users can invoke it in M365 Copilot using:

- `@AzureFunctionProxy` (if name is "Azure Function Proxy")
- `@M365Agent` (if name is "M365 Agent")  
- `@YourCustomName` (if you used a custom name)

### **Next Steps After Finding Your Agent**

1. **Publish the Agent**: Set Publishing State = 'Published' in Teams Admin Center
2. **Configure Permissions**: Set up user access policies if needed
3. **Test the Agent**: Try asking it questions in M365 Copilot
4. **Share with Users**: Let your team know the agent name to use

### **Making It Easier Next Time**

For future deployments, use a distinctive name like:
- `[YourName] AI Assistant`
- `[Department] Function Proxy` 
- `[Project] Agent`

This makes it much easier to identify among many organizational agents!
