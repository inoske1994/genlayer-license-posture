#!/usr/bin/env python3
"""Seed the direct-mode cache with the GenVM release tarball.

gltest asks for .../releases/download/<tag>/genvm-universal.tar.xz, which does not
exist in the release. The runner bundle is published as genvm-runners-all.tar.xz.
This script downloads that asset and stores it under the name gltest looks for,
so pytest can run. It only touches the local cache.
"""

import sys
import urllib.request
from pathlib import Path

RELEASES = "https://github.com/genlayerlabs/genvm/releases"
CACHE_DIR = Path.home() / ".cache" / "gltest-direct"


def latest_tag() -> str:
    request = urllib.request.Request(f"{RELEASES}/latest", method="HEAD")
    request.add_header("User-Agent", "prepare-test-sdk")
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.url.rstrip("/").split("/")[-1]


def download(tag: str) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    target = CACHE_DIR / f"genvm-universal-{tag}.tar.xz"
    if target.exists() and target.stat().st_size > 0:
        print(f"already cached: {target} ({target.stat().st_size // 1048576} MB)")
        return target

    url = f"{RELEASES}/download/{tag}/genvm-runners-all.tar.xz"
    print(f"downloading {url}")
    request = urllib.request.Request(url)
    request.add_header("User-Agent", "prepare-test-sdk")
    partial = target.with_suffix(".part")
    with urllib.request.urlopen(request, timeout=300) as response, open(partial, "wb") as handle:
        total = int(response.headers.get("Content-Length", 0))
        done = 0
        while True:
            chunk = response.read(1048576)
            if not chunk:
                break
            handle.write(chunk)
            done += len(chunk)
            if total:
                print(f"\r  {done * 100 // total}% of {total // 1048576} MB", end="", flush=True)
    print()
    partial.rename(target)
    return target


def main() -> int:
    tag = latest_tag()
    print(f"latest genvm release: {tag}")
    path = download(tag)
    print(f"ready: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
