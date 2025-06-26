# PowerShell Deployment Debugging and Fixes

## Issues Addressed

### 1. DistributionMethod Parameter Missing ✅ FIXED
**Error**: `Cannot bind argument to parameter 'DistributionMethod' because it is an empty string.`
**Cause**: Teams PowerShell module 7.1.0+ requires `-DistributionMethod Store` parameter
**Fix**: Added version detection and conditional parameter inclusion

### 2. JSON Parsing Failures ✅ IMPROVED
**Error**: `WARNING: Failed to parse JSON result: Expecting value: line 1 column 1 (char 0)`
**Cause**: JSON output formatting issues or script failures before JSON generation
**Fix**: 
- Improved JSON generation in PowerShell (separate variable assignment)
- Enhanced JSON parsing with BOM handling and better error logging
- Added extensive debugging output to track script execution

## Changes Made

### PowerShell Script Improvements (in `m365_agent_tab.py`)

1. **Version-aware New-TeamsApp calls**:
   ```powershell
   if ($MajorVersion -ge 7) {
       $AppResult = New-TeamsApp -Path $PackagePath -DistributionMethod Store
   } else {
       $AppResult = New-TeamsApp -Path $PackagePath
   }
   ```

2. **Improved JSON Output**:
   ```powershell
   $JsonOutput = $Result | ConvertTo-Json -Compress
   Write-Host "RESULT_JSON:$JsonOutput"
   ```

3. **Enhanced Debugging**:
   - Added DEBUG statements throughout script execution
   - Track Teams module import, version detection, authentication, and upload
   - Detailed error reporting with JSON generation debugging

### Python JSON Parsing Improvements

1. **Robust JSON Extraction**:
   ```python
   json_str = line.replace("RESULT_JSON:", "").strip()
   json_str = json_str.encode('utf-8').decode('utf-8-sig').strip()
   ```

2. **Enhanced Error Logging**:
   - Log raw JSON lines for debugging
   - Show PowerShell output when JSON parsing fails
   - Better error context and troubleshooting guidance

3. **Fallback Success Detection**:
   - Look for success indicators even if JSON parsing fails
   - Extract app details with regex patterns
   - Multiple layers of success/failure detection

### Standalone Script Updates

- Updated `teams_7x_deployment_fix.ps1` with same fixes
- Added debug output for manual troubleshooting
- Consistent JSON output format

## Testing Tools Created

1. **`test_powershell_json.py`**: Tests basic PowerShell JSON output functionality
2. **`test_teams_7x_fix.py`**: Validates that DistributionMethod fixes are in place
3. **Debug output**: Extensive logging in deployment scripts

## Current Status

✅ **DistributionMethod Parameter**: Fixed for Teams 7.x+  
🔄 **JSON Parsing**: Improved with debugging  
✅ **Version Detection**: Working correctly  
✅ **Error Handling**: Enhanced with detailed logging  
✅ **Fallback Methods**: Manual upload instructions available  

## Next Steps for Debugging

If you're still seeing issues:

1. **Check the DEBUG output**: The PowerShell script now has extensive debug logging
2. **Look for specific error patterns**: Authentication failures, permission issues, etc.
3. **Run test scripts**: Use `python test_powershell_json.py` to verify basic functionality
4. **Check Teams module version**: Run `Get-Module MicrosoftTeams -ListAvailable` in PowerShell
5. **Try manual upload**: Use Teams Admin Center as the most reliable method

## Common Error Patterns

### Authentication Errors (Teams 7.x+)
- `Unsupported User Type 'Unknown'`
- `NonInteractive parameter not found`
- **Solution**: Use interactive authentication (browser login)

### Permission Errors
- `Access denied` or `403 Forbidden`
- **Solution**: Ensure Teams Administrator role

### Package Errors
- `Package validation failed`
- **Solution**: Check manifest.json format and required files

### Timeout Errors
- Script hangs or times out
- **Solution**: Try manual upload or check network connectivity

The debug output will now help identify exactly where the deployment process is failing.
