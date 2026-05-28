#!/usr/bin/env python3
"""Full automation test - end to end"""
import sys
sys.path.insert(0, "/opt/godbot/automation")

from modules.utils import load_config
from modules.ai_generator import NEXUSClient
from modules.wp_client import WordPressClient
from modules.product_builder import ProductBuilder
from modules.utils import log

cfg = load_config()
errors = []

# 1. NEXUS API
print("="*50)
log("test", "Testing NEXUS API...")
nexus = NEXUSClient()
if nexus.health_check():
    log("test", "✓ NEXUS API: OK")
else:
    log("test", "✗ NEXUS API: FAIL", "ERROR")
    errors.append("NEXUS API")

# 2. WordPress API
print("="*50)
log("test", "Testing WordPress API...")
with open("/opt/godbot/automation/.wp_app_pass") as f:
    wp_pass = f.read().strip()

wp = WordPressClient(
    cfg["wordpress"]["url"],
    "workforgeai@gmail.com",
    wp_pass,
)
if wp.check_health():
    log("test", "✓ WordPress: OK")
else:
    log("test", "✗ WordPress: FAIL", "ERROR")
    errors.append("WordPress")

# 3. Product Builder
print("="*50)
log("test", "Testing Product Builder...")
builder = ProductBuilder()
try:
    pkgs = builder.build_all()
    log("test", f"✓ Products built: {len(pkgs)}")
    for p in pkgs:
        import os
        log("test", f"  {os.path.basename(p)} ({os.path.getsize(p)} bytes)")
except Exception as e:
    log("test", f"✗ Product Builder: {e}", "ERROR")
    errors.append(f"Product Builder: {e}")

# 4. Content generation (test only, don't publish)
print("="*50)
log("test", "Testing content generation (no publish)...")
try:
    raw = nexus.generate_article(
        topic="Quick test article",
        keywords=["test", "automation"],
        language="en",
        word_count=200,
    )
    log("test", f"✓ Content generated ({len(raw)} chars)")
    meta, content = wp.parse_article_response(raw)
    log("test", f"  Meta: {meta[:100]}...")
    log("test", f"  Content: {len(content)} chars")
except Exception as e:
    log("test", f"✗ Content generation: {e}", "ERROR")
    errors.append(f"Content generation: {e}")

# Summary
print("="*50)
if errors:
    log("test", f"FAILED: {len(errors)} error(s)", "ERROR")
    for e in errors:
        log("test", f"  - {e}", "ERROR")
    sys.exit(1)
else:
    log("test", "✓ ALL TESTS PASSED")
    print("="*50)
    print("System ready for production!")
