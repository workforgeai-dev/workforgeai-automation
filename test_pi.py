import sys
sys.path.insert(0, /home/erico/automation)
from modules.utils import load_config
c = load_config()
print(Config:, c[app_name], c[version])
from modules.product_builder import ProductBuilder
b = ProductBuilder()
pkgs = b.build_all()
print(Products:, len(pkgs))
from modules.wp_client import WordPressClient
print(All modules OK)
