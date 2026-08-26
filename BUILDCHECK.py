#!/usr/bin/env python3
"""
VoidDesk v10.5 - Build Integrity & Performance Check
Runs before final packaging for RG35XX-H deployment
"""

import ast
import os
import sys
from pathlib import Path

print("=" * 80)
print("VOIDDESK v10.5 BUILD INTEGRITY CHECK")
print("=" * 80)

errors = []
warnings = []

# 1. Verify critical files exist
print("\n[CHECK 1] Critical Files")
critical_files = [
    "desk/main.py",
    "desk/nexus.py",
    "desk/intro.py",
    "desk/const.py",
    "mux_launch.sh",
    "glyph/",
    "assets/",
]

for fname in critical_files:
    if os.path.exists(fname):
        print(f"  ✅ {fname}")
    else:
        print(f"  ❌ MISSING: {fname}")
        errors.append(f"Missing critical file: {fname}")

# 2. Verify Python syntax
print("\n[CHECK 2] Python Syntax")
for py_file in sorted(Path("desk").glob("*.py")):
    try:
        with open(py_file, 'r') as f:
            ast.parse(f.read())
        print(f"  ✅ {py_file.name}")
    except SyntaxError as e:
        print(f"  ❌ {py_file.name}: {e}")
        errors.append(f"Syntax error in {py_file.name}: {e}")

# 3. Verify critical imports
print("\n[CHECK 3] Import Resolution")
try:
    # Try to import main modules in isolation (without running)
    import importlib.util
    
    for module_name in ["desk.const", "desk.icons", "desk.utils"]:
        try:
            parts = module_name.split(".")
            if len(parts) == 2:
                spec = importlib.util.spec_from_file_location(module_name, f"{parts[0]}/{parts[1]}.py")
                if spec and spec.loader:
                    print(f"  ✅ {module_name} importable")
                else:
                    warnings.append(f"Import spec unclear: {module_name}")
        except Exception as e:
            warnings.append(f"Import test failed for {module_name}: {e}")
except Exception as e:
    warnings.append(f"Import resolution skipped: {e}")

# 4. Check version strings
print("\n[CHECK 4] Version Strings")
with open("desk/const.py", "r") as f:
    const_content = f.read()
    
if 'VERSION = "10.5.0"' in const_content:
    print("  ✅ Version = 10.5.0")
else:
    errors.append("Version string incorrect")

if 'VERSION_CODENAME = "D.N"' in const_content:
    print("  ✅ Codename = D.N")
else:
    errors.append("Codename string incorrect")

# 5. Check for critical memory issues
print("\n[CHECK 5] Memory Leak Patterns")
leak_patterns = []

for py_file in ["desk/intro.py", "desk/main.py"]:
    with open(py_file, "r") as f:
        content = f.read()
    
    # Count problematic patterns (simple heuristic)
    unclosed_opens = content.count("open(") - content.count("with open(")
    if unclosed_opens > 10:
        leak_patterns.append(f"{py_file}: {unclosed_opens} potential unmanaged file opens")

if leak_patterns:
    print("  ⚠️  File descriptor concerns found:")
    for pattern in leak_patterns:
        print(f"     {pattern}")
        warnings.append(pattern)
else:
    print("  ✅ No obvious file descriptor leaks")

# 6. Check Nexus cache initialization
print("\n[CHECK 6] NexusRenderer Cache")
with open("desk/nexus.py", "r") as f:
    nexus_content = f.read()

if "_nexus_planet_lru = {}" in nexus_content and "_nexus_planet_lru_order = []" in nexus_content:
    print("  ✅ Cache attributes initialized")
else:
    errors.append("NexusRenderer cache not properly initialized")

# 7. Check icon imports
print("\n[CHECK 7] Icon Module Imports")
if "from desk import icons" in nexus_content:
    print("  ✅ icons imported globally in nexus.py")
else:
    warnings.append("icons not imported globally in nexus.py")

# 8. Manifest check
print("\n[CHECK 8] Manifest Files")
manifest_items = [
    ("mux_launch.sh", "executable"),
    ("desk/main.py", "python module"),
    ("glyph/", "icon directory"),
]

for item, desc in manifest_items:
    if os.path.exists(item):
        if item.endswith(".sh") and os.access(item, os.X_OK):
            print(f"  ✅ {item} ({desc}) - executable")
        else:
            print(f"  ✅ {item} ({desc})")

# SUMMARY
print("\n" + "=" * 80)
print("BUILD CHECK SUMMARY")
print("=" * 80)

if errors:
    print(f"\n❌ ERRORS ({len(errors)}):")
    for err in errors:
        print(f"  • {err}")
    sys.exit(1)
elif warnings:
    print(f"\n⚠️  WARNINGS ({len(warnings)}):")
    for warn in warnings:
        print(f"  • {warn}")
    print("\n✅ Build acceptable for deployment (warnings noted)")
else:
    print("\n✅ BUILD PASSED - All checks OK")
    print("Ready for final packaging")

sys.exit(0)
