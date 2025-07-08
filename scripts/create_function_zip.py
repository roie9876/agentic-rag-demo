#!/usr/bin/env python3
"""
Create Function Deployment Package
----------------------------------
Creates a zip file of the function code for manual deployment via Azure Portal.
"""

import zipfile
from pathlib import Path
import datetime

def create_function_zip():
    """Create a zip file of the function directory for manual deployment."""
    
    func_dir = Path.cwd() / "function"
    if not func_dir.exists():
        print(f"❌ Function directory not found: {func_dir}")
        return False
    
    # Create timestamp for unique filename
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_name = f"function_deployment_{timestamp}.zip"
    zip_path = Path.cwd() / zip_name
    
    print(f"📦 Creating deployment package: {zip_name}")
    
    try:
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            file_count = 0
            for file_path in func_dir.rglob('*'):
                if file_path.is_file():
                    # Skip unnecessary files
                    if any(skip in str(file_path) for skip in ['.pyc', '__pycache__', '.git']):
                        continue
                    
                    arcname = file_path.relative_to(func_dir)
                    zipf.write(file_path, arcname)
                    file_count += 1
                    
        print(f"✅ Created {zip_name} with {file_count} files")
        print(f"📁 Location: {zip_path}")
        print("\n🚀 **Next Steps for Manual Deployment:**")
        print("1. Download this zip file to your local machine")
        print("2. Go to Azure Portal → Your Function App → Deployment Center")
        print("3. Choose 'Zip Deploy' and upload this file")
        print("4. Wait for deployment to complete")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating zip file: {e}")
        return False

def main():
    """Main function."""
    print("📦 Function Deployment Package Creator")
    print("=" * 40)
    
    success = create_function_zip()
    
    if not success:
        print("\n❌ Failed to create deployment package")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
