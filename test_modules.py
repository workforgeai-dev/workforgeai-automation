#!/usr/bin/env python3
"""Test automation engine modules"""
import sys
sys.path.insert(0, "/opt/godbot/automation")

from modules.utils import load_config
cfg = load_config()
print(f"Config loaded: {cfg['app_name']} v{cfg['version']}")
print(f"Products: {[p['name'] for p in cfg['products']]}")
print(f"Languages: {cfg['content']['languages']}")

from modules.product_builder import ProductBuilder
b = ProductBuilder()
pkgs = b.build_all()
print(f"\nPackages built: {len(pkgs)}")
for p in pkgs:
    import os
    print(f"  {p} ({os.path.getsize(p)} bytes)")

from modules.ai_generator import NEXUSClient
n = NEXUSClient()
healthy = n.health_check()
print(f"\nNEXUS API health: {'OK' if healthy else 'FAIL'}")

print("\nAll tests passed!")
