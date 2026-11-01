#!/usr/bin/env python3
"""Reproduce a LicensePosture digest without GenLayer.

Usage:
    python scripts/digest_local.py <owner> <repo> <commit>

The contract normalizes the license text and hashes it with SHA-256 before any
model sees it, so the digest is a pure function of the bytes GitHub serves for
that commit. This script applies the same normalization and prints the same
hash, which lets a reader check a stored record against the source directly.
"""

import hashlib
import sys
import urllib.error
import urllib.request

LICENSE_PATHS = (
    "LICENSE",
    "LICENSE.md",
    "LICENSE.txt",
    "license",
    "license.md",
    "COPYING",
    "LICENSE-MIT",
    "LICENSE-APACHE",
    "COPYING.md",
)

MAX_BYTES = 65536
RAW_HOST = "https://raw.githubusercontent.com/"


def normalize(text):
    """Same rule as _norm in the contract: one space between words, no edges."""
    return " ".join(text.replace(chr(160), " ").split())


def fetch(owner, repo, commit):
    for candidate in LICENSE_PATHS:
        url = RAW_HOST + owner + "/" + repo + "/" + commit + "/" + candidate
        request = urllib.request.Request(url, headers={"User-Agent": "license-posture-digest"})
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                body = response.read()
        except urllib.error.HTTPError as error:
            if error.code == 404:
                continue
            raise SystemExit("host answered with status " + str(error.code) + " for " + candidate)
        if len(body) > MAX_BYTES:
            raise SystemExit("file is larger than the contract limit: " + candidate)
        text = body.decode("utf-8", "replace")
        normalized = normalize(text)
        if normalized == "":
            continue
        return candidate, len(body), normalized
    return None, 0, ""


def main():
    if len(sys.argv) != 4:
        raise SystemExit(__doc__.strip())
    owner, repo, commit = sys.argv[1], sys.argv[2], sys.argv[3]
    path, length, normalized = fetch(owner, repo, commit)
    if path is None:
        print("no license file at any of the nine conventional paths")
        return
    print("path   " + path)
    print("length " + str(length))
    print("digest " + hashlib.sha256(normalized.encode("utf-8")).hexdigest())


if __name__ == "__main__":
    main()
