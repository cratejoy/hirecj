#!/usr/bin/env python3
"""Find all environment variables in the codebase."""

import os
import re
from pathlib import Path
from collections import defaultdict
import json

def find_env_vars():
    """Scan codebase for all environment variable usage."""
    env_vars = defaultdict(set)
    
    # Patterns to find environment variable usage
    patterns = [
        # Python patterns
        r'os\.environ\.get\(["\'](\w+)["\']\)',
        r'os\.environ\[["\'](\w+)["\']\]',
        r'os\.getenv\(["\'](\w+)["\']\)',
        # Pydantic Field patterns
        r'(\w+):\s*(?:str|int|bool|float)\s*=\s*Field\([^)]*default_factory[^)]*["\'](\w+)["\']',
        r'(\w+):\s*(?:str|int|bool|float)\s*=\s*Field\([^)]*env=["\'](\w+)["\']',
        # Simple Pydantic patterns
        r'(\w+):\s*(?:str|int|bool|float)\s*=\s*["\'].*["\']\s*#.*env',
        # JavaScript/TypeScript patterns
        r'process\.env\.(\w+)',
        r'import\.meta\.env\.(\w+)',
        # Shell patterns in scripts
        r'\$(\w+)',
        r'\$\{(\w+)\}',
    ]
    
    # Directories to skip
    skip_dirs = {'.git', 'node_modules', 'venv', '__pycache__', '.pytest_cache', 'dist', 'build'}
    
    for root, dirs, files in os.walk('.'):
        # Skip directories
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        
        for file in files:
            # Skip non-code files
            if not file.endswith(('.py', '.js', '.ts', '.tsx', '.sh', '.env', '.env.example')):
                continue
                
            filepath = Path(root) / file
            
            # Skip test files for now
            if 'test_' in str(filepath) or '_test.' in str(filepath):
                continue
            
            try:
                content = filepath.read_text()
                
                # Special handling for .env files
                if file.endswith(('.env', '.env.example')):
                    for line in content.splitlines():
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key = line.split('=')[0].strip()
                            if key and key.isupper():
                                env_vars[key].add(str(filepath))
                else:
                    # Apply patterns
                    for pattern in patterns:
                        matches = re.findall(pattern, content, re.MULTILINE)
                        for match in matches:
                            if isinstance(match, tuple):
                                # Handle patterns with groups
                                var = match[-1] if match[-1].isupper() else match[0]
                            else:
                                var = match
                            
                            # Filter out non-env looking variables
                            if var and var.isupper() and len(var) > 2:
                                env_vars[var].add(str(filepath))
            except Exception as e:
                print(f"Error reading {filepath}: {e}")
    
    return env_vars

def generate_report(env_vars):
    """Generate comprehensive report of environment variables."""
    print(f"\n🔍 Found {len(env_vars)} unique environment variables\n")
    
    # Save detailed report
    with open('docs/all_env_vars.md', 'w') as f:
        f.write("# All Environment Variables in HireCJ\n\n")
        f.write(f"Total unique variables: {len(env_vars)}\n\n")
        
        # Group by service
        service_vars = defaultdict(set)
        for var, files in env_vars.items():
            for file in files:
                if '/auth/' in file:
                    service_vars['auth'].add(var)
                elif '/agents/' in file:
                    service_vars['agents'].add(var)
                elif '/database/' in file:
                    service_vars['database'].add(var)
                elif '/homepage/' in file:
                    service_vars['homepage'].add(var)
                elif '/shared/' in file:
                    service_vars['shared'].add(var)
                else:
                    service_vars['root'].add(var)
        
        f.write("## Variables by Service\n\n")
        for service, vars in sorted(service_vars.items()):
            f.write(f"### {service.title()} ({len(vars)} variables)\n\n")
            for var in sorted(vars):
                f.write(f"- `{var}`\n")
            f.write("\n")
        
        f.write("## Detailed Usage\n\n")
        for var, files in sorted(env_vars.items()):
            f.write(f"### {var}\n")
            f.write(f"Used in {len(files)} file(s):\n")
            for file in sorted(files):
                f.write(f"- `{file}`\n")
            f.write("\n")
    
    # Save JSON for programmatic use
    env_dict = {var: list(files) for var, files in env_vars.items()}
    with open('scripts/env_vars.json', 'w') as f:
        json.dump(env_dict, f, indent=2, sort_keys=True)
    
    print("✅ Reports generated:")
    print("   - docs/all_env_vars.md (human readable)")
    print("   - scripts/env_vars.json (for scripts)")

if __name__ == "__main__":
    print("🔍 Auditing environment variables...")
    env_vars = find_env_vars()
    generate_report(env_vars)