#!/usr/bin/env python3
"""Cache only verified Rust distribution archives, never OpenWrt build stamps."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def configure(source):
    makefile = source / 'feeds/packages/lang/rust/Makefile'
    if not makefile.exists():
        return
    text = makefile.read_text()
    if 'RustToolchainCache.py" restore' in text:
        return
    match = re.search(r'^define Host/Compile\n(.*?)^endef$', text, re.M | re.S)
    if not match:
        raise SystemExit('Rust Host/Compile format changed; review cache integration')
    command = match[1].rstrip()
    # Keep the feed's complete build command (flags, targets and environment).
    wrapped = (
        'define Host/Compile\n'
        '\tif $(PYTHON) "$(GITHUB_WORKSPACE)/scripts/RustToolchainCache.py" restore "$(HOST_BUILD_DIR)/build/dist"; then \\\n'
        '\t\t:; \\\n'
        '\telse \\\n' + command + ' && \\\n'
        '\t\t{ $(PYTHON) "$(GITHUB_WORKSPACE)/scripts/RustToolchainCache.py" save "$(HOST_BUILD_DIR)/build/dist" || echo "Rust cache save failed; build remains valid"; }; \\\n'
        '\tfi\nendef')
    makefile.write_text(text[:match.start()] + wrapped + text[match.end():])


def cache_key(source):
    # No upstream commit hash: unrelated source changes need not rebuild Rust.
    # Full generated config and build rules prevent incompatible target reuse.
    h = hashlib.sha256(b'rust-dist-v1\0')
    for value in ('ImageOS', 'RUNNER_ARCH', 'REPO_URL', 'REPO_BRANCH', 'TARGET'):
        h.update(f'{value}={os.environ.get(value, "")}\0'.encode())
    paths = [source / '.config', source / 'rules.mk', Path(__file__).resolve(),
             Path(__file__).with_name('BuildCompatibility.py')]
    for directory in ('feeds/packages/lang/rust', 'include', 'toolchain'):
        paths.extend(p for p in (source / directory).rglob('*') if p.is_file())
    for path in sorted(paths, key=lambda p: str(p)):
        label = str(path.relative_to(source)) if path.is_relative_to(source) else path.name
        h.update(label.encode() + b'\0' + path.read_bytes() + b'\0')
    return 'rust-dist-v1-' + h.hexdigest()


def transfer(mode, dist):
    cache = Path(os.environ['RUST_DIST_CACHE'])
    key = os.environ['RUST_CACHE_KEY']
    if mode == 'save':
        archives = sorted(dist.glob('*.tar.gz'))
        if not archives or any(not p.is_file() or p.is_symlink() for p in archives):
            raise ValueError('Rust distribution archives missing')
        if cache.exists():
            shutil.rmtree(cache)
        cache.mkdir(parents=True)
        manifest = {'key': key, 'files': {}}
        for path in archives:
            shutil.copy2(path, cache / path.name)
            manifest['files'][path.name] = digest(cache / path.name)
        (cache / 'manifest.json').write_text(json.dumps(manifest, sort_keys=True))
        print(f'Rust cache: saved {len(archives)} distribution archives')
    else:
        manifest = json.loads((cache / 'manifest.json').read_text())
        if manifest['key'] != key or not manifest['files']:
            raise ValueError('Rust cache key mismatch or empty manifest')
        for name, expected in manifest['files'].items():
            path = cache / name
            if (Path(name).name != name or not name.endswith('.tar.gz') or
                    path.is_symlink() or not path.is_file() or digest(path) != expected):
                raise ValueError('Rust cache archive checksum mismatch')
        dist.mkdir(parents=True, exist_ok=True)
        for path in dist.glob('*.tar.gz'):
            path.unlink()
        for name in manifest['files']:
            shutil.copy2(cache / name, dist / name)
        print('Rust cache: verified hit; skipping Rust/LLVM bootstrap compilation')


if __name__ == '__main__':
    mode = sys.argv[1]
    if mode == 'configure':
        configure(Path('openwrt'))
    elif mode == 'key':
        key = cache_key(Path('openwrt'))
        with open(os.environ['GITHUB_OUTPUT'], 'a') as out:
            out.write(f'key={key}\n')
        with open(os.environ['GITHUB_ENV'], 'a') as out:
            out.write(f'RUST_CACHE_KEY={key}\n')
        print(key)
    else:
        try:
            transfer(mode, Path(sys.argv[2]))
        except (OSError, ValueError, KeyError, TypeError) as error:
            print(f'Rust cache unavailable: {error}; source build will be used', file=sys.stderr)
            sys.exit(1)
