# Function Deployment SSL Certificate Troubleshooting Guide

## Problem Description
When deploying Azure Functions from a private network environment, you may encounter SSL certificate verification errors like:

```
ERROR: HTTPSConnectionPool(host='function1-fggkg8gxf4c9fzdj.scm.swedencentral-01.azurewebsites.net', port=443): 
Max retries exceeded with url: /api/zipdeploy?isAsync=true&Deployer=az_cli_functions 
(Caused by SSLError(CertificateError("hostname 'function1-fggkg8gxf4c9fzdj.scm.swedencentral-01.azurewebsites.net' 
doesn't match either of '.search.windows.net', '.management.search.windows.net'")))
```

This typically happens in corporate networks with proxy servers or private Azure environments.

## Solutions (In Order of Preference)

### 🎯 Solution 1: Manual Deployment Script (Recommended)
Use our enhanced deployment script that handles SSL bypass:

```bash
cd /home/azureuser/agentic-rag-demo
python3 scripts/manual_function_deploy.py <resource_group> <function_name>
```

**Example:**
```bash
python3 scripts/manual_function_deploy.py myResourceGroup function1-fggkg8gxf4c9fzdj
```

This script automatically:
- ✅ Tries deployment with SSL bypass
- ✅ Falls back to alternative methods
- ✅ Provides detailed error messages

### 🌐 Solution 2: Azure Portal Upload (Most Reliable)
1. **Create deployment package:**
   ```bash
   cd /home/azureuser/agentic-rag-demo
   python3 scripts/create_function_zip.py
   ```

2. **Download the zip file** to your local machine

3. **Upload via Azure Portal:**
   - Go to [Azure Portal](https://portal.azure.com)
   - Navigate to your Function App
   - Go to **Deployment Center**
   - Choose **Zip Deploy**
   - Upload the zip file

### 🔧 Solution 3: VS Code Extension
1. Install **Azure Functions** extension in VS Code
2. Sign in to Azure
3. Right-click on the `function` folder
4. Select **Deploy to Function App**

### ⚙️ Solution 4: Network Configuration (Long-term)
Work with your network administrator to:

1. **Add Azure certificates to trusted store:**
   ```bash
   # Download Azure root certificates
   curl -o azure-root-ca.crt https://cacerts.digicert.com/DigiCertGlobalRootCA.crt.pem
   
   # Add to trusted certificates (Ubuntu/Debian)
   sudo cp azure-root-ca.crt /usr/local/share/ca-certificates/
   sudo update-ca-certificates
   ```

2. **Configure proxy settings** (if using corporate proxy):
   ```bash
   export HTTPS_PROXY=your-proxy-server:port
   export HTTP_PROXY=your-proxy-server:port
   export NO_PROXY=localhost,127.0.0.1,.local
   ```

3. **Configure Azure CLI for proxy:**
   ```bash
   az config set core.use_global_ca_bundle=true
   az config set core.ca_bundle_path=/etc/ssl/certs/ca-certificates.crt
   ```

## Environment-Specific Workarounds

### For Private Azure Environments
If you're using Azure Government or private Azure instances:

```bash
# Set Azure CLI to use specific cloud
az cloud set --name AzureUSGovernment  # or your private cloud name
az login
```

### For Corporate Networks
```bash
# Disable SSL verification (temporary fix only)
export PYTHONHTTPSVERIFY=0
export AZURE_CLI_DISABLE_CONNECTION_VERIFICATION=1

# Run deployment
az functionapp deployment source config-zip -g <rg> -n <function-name> --src function.zip
```

## Verification Steps

After deployment, verify your function works:

1. **Check deployment status:**
   ```bash
   az functionapp show -g <resource-group> -n <function-name> --query "state"
   ```

2. **Test function endpoint:**
   ```bash
   curl -k https://<function-name>.azurewebsites.net/api/your-function
   ```

3. **Check logs:**
   ```bash
   az functionapp logs tail -g <resource-group> -n <function-name>
   ```

## Prevention

To avoid SSL issues in the future:

1. **Use managed identity** instead of keys where possible
2. **Deploy from environments with proper certificate trust**
3. **Consider using Azure DevOps or GitHub Actions** for CI/CD
4. **Keep Azure CLI and certificates updated**

## Getting Help

If these solutions don't work:

1. **Check Azure CLI version:**
   ```bash
   az --version
   ```

2. **Update Azure CLI:**
   ```bash
   curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
   ```

3. **Contact support** with:
   - Your network configuration
   - Azure CLI version
   - Complete error message
   - Output of `nslookup <your-function-hostname>`

## Files Created by This Guide

- `scripts/manual_function_deploy.py` - Enhanced deployment script
- `scripts/create_function_zip.py` - Creates deployment package
- `function_deployment_*.zip` - Ready-to-upload deployment package

---

*Last updated: July 8, 2025*
