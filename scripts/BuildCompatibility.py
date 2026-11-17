#!/usr/bin/env python3
"""Apply narrow build fixes after feeds are installed, before make defconfig."""
from pathlib import Path
import re

source = Path('openwrt')
if not (source / 'package').is_dir():
    raise SystemExit('Run from the workspace containing openwrt/package')

# Rust CI LLVM artifacts expire (1.96.0 currently returns HTTP 404).
# Build the bundled LLVM instead; keep the feed's Rust version and hashes.
rust = source / 'feeds/packages/lang/rust/Makefile'
if rust.exists():
    text = rust.read_text()
    updated = text.replace('--set=llvm.download-ci-llvm=true',
                           '--set=llvm.download-ci-llvm=false')
    if updated != text:
        rust.write_text(updated)
        print('Rust: build LLVM locally instead of downloading expiring CI artifacts')

# Upstream fix: immortalwrt/immortalwrt@2fe3065ade26bd1ef85539c9d1bd2272bdb0aa01.
# Only refresh the known stale hunk for this exact firewall4 source revision.
firewall = source / 'package/network/config/firewall4'
makefile = firewall / 'Makefile'
patch = firewall / 'patches/001-firewall4-add-support-for-fullcone-nat.patch'
if makefile.exists() and patch.exists() and re.search(
        r'^PKG_SOURCE_VERSION:=3722eadc088c3ab81389596ca9796112b436583a$',
        makefile.read_text(), re.MULTILINE):
    old = ('@@ -5,6 +5,10 @@ config defaults\n'
           ' \toption forward\t\tREJECT\n'
           ' # Uncomment this line to disable ipv6 rules\n'
           ' #\toption disable_ipv6\t1\n')
    new = ('@@ -3,6 +3,10 @@ config defaults\n'
           ' \toption input\t\tREJECT\n'
           ' \toption output\t\tACCEPT\n'
           ' \toption forward\t\tREJECT\n')
    text = patch.read_text()
    if old in text:
        patch.write_text(text.replace(old, new, 1))
        print('firewall4: refresh FullCone patch context for 3722eadc')
