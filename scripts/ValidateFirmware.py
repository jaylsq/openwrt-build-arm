#!/usr/bin/env python3
"""Fail before publishing missing or malformed device images."""
import json
import struct
import sys
from pathlib import Path

mode, directory, target = sys.argv[1:]
root = Path(directory)
device = {'ipq60xx-libWrt-nowifi-ress01': 'jdcloud_re-ss-01',
          'ipq60xx-libWrt-nowifi-znm2': 'zn_m2'}[target]

def require(condition, message):
    if not condition:
        raise SystemExit(message)

if mode == 'config':
    config = set((root / '.config').read_text().splitlines())
    require(f'CONFIG_TARGET_DEVICE_qualcommax_ipq60xx_DEVICE_{device}=y' in config,
            'Selected device missing after defconfig')
    for package in ('luci', 'firewall4', 'kmod-qca-nss-dp'):
        require(f'CONFIG_PACKAGE_{package}=y' in config, f'Missing network package: {package}')
    require(any(f'CONFIG_PACKAGE_{p}=y' in config for p in ('dnsmasq', 'dnsmasq-full')),
            'Missing DHCP/DNS service')
    require('CONFIG_TARGET_ROOTFS_SQUASHFS=y' in config, 'SquashFS missing')
elif mode == 'images':
    profiles = json.loads((root / 'profiles.json').read_text())['profiles']
    require(set(profiles) == {device}, 'Unexpected device profiles in output')
    profile = profiles[device]
    manifests = list(root.glob('*.manifest'))
    require(len(manifests) == 1, 'Missing or ambiguous package manifest')
    packages = {line.split()[0] for line in manifests[0].read_text().splitlines() if line.strip()}
    require(not any(p in packages for p in ('kmod-ath11k', 'kmod-ath11k-ahb',
                                          'wpad-openssl', 'ipq-wifi-' + device)),
            'Wireless packages remain in device rootfs')
    for image in profile['images']:
        path = root / image['name']
        require(path.is_file() and path.stat().st_size > 0, f'Missing image: {path}')
    if device == 'jdcloud_re-ss-01':
        factories = list(root.glob('*jdcloud_re-ss-01-squashfs-factory.bin'))
        upgrades = list(root.glob('*jdcloud_re-ss-01-squashfs-sysupgrade.bin'))
        require(len(factories) == len(upgrades) == 1, 'Missing RESS01 factory/sysupgrade')
        with factories[0].open('rb') as stream:
            magic, length = struct.unpack('>II', stream.read(8))
            require(magic == 0xD00DFEED and 8 < length <= 6144 * 1024,
                    'Invalid FIT kernel or kernel exceeds 6 MiB factory slot')
            stream.seek(6144 * 1024)
            require(stream.read(4) == b'hsqs', 'SquashFS is not at factory offset 6 MiB')
else:
    raise SystemExit('Unknown validation mode')
print(f'{device}: {mode} checks passed')
