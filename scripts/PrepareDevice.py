#!/usr/bin/env python3
"""Apply defaults before network generation; retain upstream port definitions."""
import re
import sys
from pathlib import Path

root = Path(sys.argv[1])
device = {
    'ipq60xx-libWrt-nowifi-ress01': 'jdcloud_re-ss-01',
    'ipq60xx-libWrt-nowifi-znm2': 'zn_m2',
}[sys.argv[2]]
image_path = root / 'target/linux/qualcommax/image/ipq60xx.mk'
image = image_path.read_text()
pattern = re.compile(r'(?ms)^define Device/' + re.escape(device) + r'\n.*?^endef$')
matches = list(pattern.finditer(image))
if len(matches) != 1:
    raise SystemExit('Device definition changed; review upstream')
block = matches[0].group()
# Per-device packages may re-add wireless despite global =n settings.
excluded = ('ath11k-firmware-ipq6018', 'kmod-ath11k', 'kmod-ath11k-ahb',
            'kmod-ath11k-pci', 'hostapd-common', 'wpad-openssl',
            'iw', 'iwinfo', 'wifi-scripts', 'wireless-regdb', 'ipq-wifi-' + device)
block = block.replace('\nendef', '\n\tDEVICE_PACKAGES += ' +
                      ' '.join('-' + name for name in excluded) + '\nendef')
if device == 'jdcloud_re-ss-01':
    recipe = 'append-kernel | pad-to $$(KERNEL_SIZE) | append-rootfs | append-metadata'
    if block.count(recipe) != 1 or 'KERNEL_SIZE := 6144k' not in block:
        raise SystemExit('RESS01 factory layout changed; review upstream')
    block = block.replace(recipe, 'append-kernel | check-size $$(KERNEL_SIZE) | '
                          'pad-to $$(KERNEL_SIZE) | append-rootfs | append-metadata')
    path = root / 'package/base-files/files/bin/config_generate'
    text = path.read_text()
    old = 'lan) ipad=${ipaddr:-"192.168.1.1"} ;;'
    if text.count(old) != 1 or "add_list network.$1.ipaddr='$ipad/$prefix'" not in text:
        raise SystemExit('Network generator changed; review LAN address and prefix')
    path.write_text(text.replace(old, 'lan) ipad=${ipaddr:-"192.168.10.1"} ;;'))
    # Preserve upstream /24 prefix and upgrade configurations.
    (root / 'files/etc/uci-defaults/99-custom-lan-ip').unlink(missing_ok=True)
image_path.write_text(image[:matches[0].start()] + block + image[matches[0].end():])
print(f'{device}: prepared no-Wi-Fi image; retained network ports and prefix')
