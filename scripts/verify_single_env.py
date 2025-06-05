#!/usr/bin/env python3
"""
Verify the single .env pattern is properly implemented.

This script checks that:
1. Only root .env exists for developers to edit
2. No service .env.example files exist
3. No code uses load_dotenv directly
4. All services use centralized config

Phase 4.0: True Environment Centralization
"""

import os
import sys
from pathlib import Path
from typing import List, Set

def check_root_env() -> List[str]:
    """Check that root .env exists."""
    issues = []
    
    if not Path(".env").exists():
        issues.append("❌ Root .env file missing - run 'cp .env.master.example .env'")
    else:
        print("✅ Root .env file exists")
    
    return issues

def check_no_service_examples() -> List[str]:
    """Check no service .env.example files exist."""
    issues = []
    bad_files = []
    
    # Check for service-specific example files that shouldn't exist
    for service in ["auth", "agents", "database", "homepage"]:
        for pattern in [".env.example", ".env.secrets.example"]:
            path = Path(service) / pattern
            if path.exists():
                bad_files.append(str(path))
    
    if bad_files:
        issues.append(f"❌ Found {len(bad_files)} service example files that should be removed:")
        for file in bad_files:
            issues.append(f"   - {file}")
    else:
        print("✅ No service .env.example files found")
    
    return issues

def check_no_dotenv_usage() -> List[str]:
    """Check no code uses load_dotenv directly."""
    issues = []
    files_with_dotenv = []
    
    # Skip these files
    skip_files = {
        'shared/env_loader.py',  # This is our centralized loader
        'scripts/verify_single_env.py',  # This script
        'shared/env_loader.py.backup',  # Backup file
    }
    
    # Directories to skip
    skip_dirs = {'.git', 'node_modules', 'venv', '__pycache__', '.pytest_cache', 'dist', 'build'}
    
    for root, dirs, files in os.walk('.'):
        # Skip directories
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        
        for file in files:
            if not file.endswith('.py'):
                continue
                
            filepath = Path(root) / file
            
            # Skip certain files
            if str(filepath) in skip_files or any(skip in str(filepath) for skip in skip_files):
                continue
            
            try:
                content = filepath.read_text()
                if 'from dotenv import load_dotenv' in content or 'load_dotenv()' in content:
                    files_with_dotenv.append(str(filepath))
            except:
                pass
    
    if files_with_dotenv:
        issues.append(f"❌ Found {len(files_with_dotenv)} files using load_dotenv directly:")
        for file in files_with_dotenv:
            issues.append(f"   - {file}")
    else:
        print("✅ No direct load_dotenv usage found")
    
    return issues

def check_service_configs() -> List[str]:
    """Check that service configs use centralized loading."""
    issues = []
    services_ok = []
    
    # Check each service config
    configs = [
        ("auth", "auth/app/config.py"),
        ("agents", "agents/app/config.py"),
        ("database", "database/app/config.py"),
    ]
    
    for service, config_path in configs:
        path = Path(config_path)
        if not path.exists():
            issues.append(f"❌ Missing config file: {config_path}")
            continue
            
        try:
            content = path.read_text()
            if 'from shared.env_loader import' in content or 'shared.env_loader' in content:
                services_ok.append(service)
            else:
                issues.append(f"❌ {service} config doesn't use shared.env_loader")
        except:
            issues.append(f"❌ Can't read {config_path}")
    
    if services_ok:
        print(f"✅ Services using centralized config: {', '.join(services_ok)}")
    
    return issues

def check_env_distribution() -> List[str]:
    """Check that env distribution script exists and is executable."""
    issues = []
    
    script_path = Path("scripts/distribute_env.py")
    if not script_path.exists():
        issues.append("❌ Missing scripts/distribute_env.py")
    elif not os.access(script_path, os.X_OK):
        issues.append("❌ scripts/distribute_env.py is not executable")
    else:
        print("✅ Environment distribution script ready")
    
    return issues

def check_makefile() -> List[str]:
    """Check that Makefile doesn't create multiple .env files."""
    issues = []
    
    makefile = Path("Makefile")
    if not makefile.exists():
        issues.append("❌ Missing Makefile")
        return issues
    
    try:
        content = makefile.read_text()
        
        # Check for problematic patterns
        bad_patterns = [
            'cp auth/.env.example auth/.env',
            'cp agents/.env.example agents/.env',
            'cp database/.env.example database/.env',
            'cp homepage/.env.example homepage/.env',
        ]
        
        found_bad = []
        for pattern in bad_patterns:
            if pattern in content:
                found_bad.append(pattern)
        
        if found_bad:
            issues.append("❌ Makefile still creates service-specific .env files:")
            for pattern in found_bad:
                issues.append(f"   - {pattern}")
        else:
            print("✅ Makefile doesn't create service .env files")
            
    except:
        issues.append("❌ Can't read Makefile")
    
    return issues

def main():
    """Run all verification checks."""
    print("🔍 Verifying single .env pattern implementation...")
    print("=" * 50)
    
    all_issues = []
    
    # Run all checks
    all_issues.extend(check_root_env())
    all_issues.extend(check_no_service_examples())
    all_issues.extend(check_no_dotenv_usage())
    all_issues.extend(check_service_configs())
    all_issues.extend(check_env_distribution())
    all_issues.extend(check_makefile())
    
    print("=" * 50)
    
    if all_issues:
        print(f"\n❌ Found {len(all_issues)} issues:\n")
        for issue in all_issues:
            print(issue)
        print("\n💡 Run './scripts/cleanup_old_env.sh' to clean up old files")
        print("💡 Update code to use 'from shared.env_loader import get_env'")
        sys.exit(1)
    else:
        print("\n✅ Single .env pattern properly implemented!")
        print("\n🎉 Developers now manage just ONE .env file!")
        print("\n📝 Next steps:")
        print("   1. Run 'python scripts/distribute_env.py' before starting services")
        print("   2. Services will automatically get their needed variables")

if __name__ == "__main__":
    main()