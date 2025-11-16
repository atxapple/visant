#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test Railway volume path detection."""

import os
import sys
from pathlib import Path

# Fix Windows console encoding
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

# Test without Railway env
print("Test 1: Local environment (no RAILWAY_ENVIRONMENT)")
os.environ.pop('RAILWAY_ENVIRONMENT', None)
os.environ.pop('RAILWAY_ENVIRONMENT_NAME', None)
# Force reload of module
if 'cloud.api.storage.config' in sys.modules:
    del sys.modules['cloud.api.storage.config']
from cloud.api.storage.config import get_uploads_dir
local_path = get_uploads_dir()
print(f"  UPLOADS_DIR: {local_path}")
assert local_path == Path("uploads"), f"Expected 'uploads', got '{local_path}'"
print("  ✓ PASS\n")

# Test with Railway env
print("Test 2: Railway environment (RAILWAY_ENVIRONMENT=production)")
os.environ['RAILWAY_ENVIRONMENT'] = 'production'
# Force reload of module
if 'cloud.api.storage.config' in sys.modules:
    del sys.modules['cloud.api.storage.config']
from cloud.api.storage.config import get_uploads_dir
railway_path = get_uploads_dir()
print(f"  UPLOADS_DIR: {railway_path}")
assert railway_path == Path("/mnt/data"), f"Expected '/mnt/data', got '{railway_path}'"
print("  ✓ PASS\n")

print("All tests passed! ✓")
