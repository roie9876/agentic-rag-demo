#!/usr/bin/env python3
"""
Test PowerShell JSON output for debugging
"""

import subprocess
import platform
import tempfile
import json

def test_powershell_json():
    """Test that PowerShell JSON output is working correctly"""
    
    # Simple PowerShell script that generates JSON output like our deployment script
    test_script = '''
try {
    $Result = @{
        "success" = $true
        "test_value" = "hello world"
        "number" = 42
    }
    $JsonOutput = $Result | ConvertTo-Json -Compress
    Write-Host "RESULT_JSON:$JsonOutput"
    Write-Host "Test completed successfully!"
} catch {
    $ErrorResult = @{
        "success" = $false
        "error" = $_.Exception.Message
    }
    $ErrorJsonOutput = $ErrorResult | ConvertTo-Json -Compress
    Write-Host "RESULT_JSON:$ErrorJsonOutput"
    exit 1
}
'''
    
    # Write test script to temp file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.ps1', delete=False) as temp_script:
        temp_script.write(test_script)
        script_path = temp_script.name
    
    try:
        # Determine PowerShell command based on platform
        system = platform.system().lower()
        if system == "windows":
            ps_cmd = ["powershell.exe", "-ExecutionPolicy", "Bypass", "-File", script_path]
        else:
            ps_cmd = ["pwsh", "-File", script_path]
        
        print(f"🔍 Testing PowerShell JSON output...")
        print(f"Command: {' '.join(ps_cmd)}")
        
        # Run the script
        result = subprocess.run(
            ps_cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        print(f"\n📊 Results:")
        print(f"Return code: {result.returncode}")
        print(f"STDOUT:")
        for i, line in enumerate(result.stdout.split('\n')):
            print(f"  {i:2d}: {repr(line)}")
        
        if result.stderr:
            print(f"STDERR:")
            for i, line in enumerate(result.stderr.split('\n')):
                print(f"  {i:2d}: {repr(line)}")
        
        # Test JSON parsing
        output_lines = result.stdout.split('\n')
        json_result = None
        json_line_found = None
        
        for line in output_lines:
            line = line.strip()
            if line.startswith("RESULT_JSON:"):
                json_line_found = line
                try:
                    json_str = line.replace("RESULT_JSON:", "").strip()
                    # Remove any potential BOM or extra characters
                    json_str = json_str.encode('utf-8').decode('utf-8-sig').strip()
                    print(f"\n🧾 JSON Processing:")
                    print(f"Raw line: {repr(line)}")
                    print(f"Extracted JSON: {repr(json_str)}")
                    
                    if json_str:
                        json_result = json.loads(json_str)
                        print(f"Parsed JSON: {json_result}")
                        break
                except json.JSONDecodeError as e:
                    print(f"❌ JSON parsing failed: {e}")
                    print(f"   Raw JSON string: {repr(json_str)}")
                except Exception as e:
                    print(f"❌ Unexpected error: {e}")
        
        if json_result:
            print(f"\n✅ SUCCESS: JSON parsing worked!")
            print(f"   Success: {json_result.get('success')}")
            print(f"   Test value: {json_result.get('test_value')}")
            print(f"   Number: {json_result.get('number')}")
        else:
            print(f"\n❌ FAILED: Could not parse JSON from PowerShell output")
            if json_line_found:
                print(f"   JSON line found: {repr(json_line_found)}")
            else:
                print(f"   No RESULT_JSON line found")
        
        return json_result is not None
        
    except subprocess.TimeoutExpired:
        print("❌ PowerShell script timed out")
        return False
    except FileNotFoundError:
        if platform.system().lower() == "windows":
            print("❌ PowerShell not found")
        else:
            print("❌ PowerShell Core (pwsh) not found - install from https://github.com/PowerShell/PowerShell")
        return False
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False
    
    finally:
        # Clean up temp file
        try:
            import os
            os.unlink(script_path)
        except:
            pass

if __name__ == "__main__":
    print("🚀 Testing PowerShell JSON Output")
    print("=" * 50)
    
    success = test_powershell_json()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 PowerShell JSON output is working correctly!")
        print("The issue may be in the specific deployment script content.")
    else:
        print("❌ PowerShell JSON output has issues.")
        print("This explains why the M365 deployment is failing.")
        print("\nTry:")
        print("1. Check if PowerShell Core (pwsh) is installed")
        print("2. Test with a simpler PowerShell script")
        print("3. Use manual upload as backup method")
