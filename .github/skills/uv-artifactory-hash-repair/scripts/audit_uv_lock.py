#!/usr/bin/env python3
"""Audit every artifact hash in a uv.lock against the bytes the registry serves.

Why this exists
---------------
When ``uv sync --locked`` fails with a hash mismatch, CI stops at the FIRST bad
package -- but a private mirror (Artifactory, Nexus, ...) re-mirroring upstream
often drifts several wheels at once. Fixing them one CI round-trip at a time is
slow. This script checks the hash of EVERY sdist and wheel URL in the lock in a
single pass so you can patch all of the drift together.

How it works
------------
By default it sends a HEAD request per artifact and reads the registry's
``x-checksum-sha256`` response header instead of downloading the file.
Artifactory returns this header and it matches the real downloaded bytes, so a
full audit of ~1000 artifacts takes seconds. If your mirror does not expose that
header (rows show up as ``no_checksum_header``), pass ``--download`` to fetch and
hash each artifact instead.

Auth: requests reuse your ``~/.netrc`` (``curl --netrc``), the same credentials
uv uses, so no secrets are passed on the command line.

Usage
-----
    python audit_uv_lock.py [path/to/uv.lock] [--download] [--write-tsv out.tsv]

Exit code is 0 when there are no mismatches, 1 when any drift is found, and 2 on
a usage/IO error -- handy for scripting.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import subprocess
import sys
import tempfile
import tomllib
from concurrent.futures import ThreadPoolExecutor

MAX_WORKERS = 16

# (name, version, kind, url, expected_hash)
Entry = tuple[str, str, str, str, str]


def head_sha256(url: str) -> tuple[str, str]:
    """Return (sha256, error) from the registry's HEAD checksum header."""
    try:
        out = subprocess.run(
            ["curl", "-fsSL", "-I", "--netrc", url],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return "", "timeout"
    if out.returncode != 0:
        return "", f"curl_rc={out.returncode}"
    for line in out.stdout.splitlines():
        if line.lower().startswith("x-checksum-sha256:"):
            return line.split(":", 1)[1].strip().lower(), ""
    return "", "no_checksum_header"


def download_sha256(url: str) -> tuple[str, str]:
    """Return (sha256, error) by downloading the artifact and hashing it."""
    tmp = ""
    try:
        with tempfile.NamedTemporaryFile(delete=False) as handle:
            tmp = handle.name
        out = subprocess.run(
            ["curl", "-fsSL", "--netrc", url, "-o", tmp],
            capture_output=True,
            text=True,
            timeout=300,
            check=False,
        )
        if out.returncode != 0:
            return "", f"curl_rc={out.returncode}"
        digest = hashlib.sha256()
        with open(tmp, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                digest.update(chunk)
        return digest.hexdigest(), ""
    except subprocess.TimeoutExpired:
        return "", "timeout"
    finally:
        if tmp and os.path.exists(tmp):
            os.unlink(tmp)


def collect_entries(lock_path: str) -> list[Entry]:
    """Return one entry per sdist and wheel artifact in the lock."""
    with open(lock_path, "rb") as fh:
        data = tomllib.load(fh)

    entries: list[Entry] = []
    for pkg in data.get("package", []):
        name = pkg.get("name", "?")
        version = pkg.get("version", "?")
        sdist = pkg.get("sdist")
        if isinstance(sdist, dict) and sdist.get("url") and sdist.get("hash"):
            h = sdist["hash"].removeprefix("sha256:").lower()
            entries.append((name, version, "sdist", sdist["url"], h))
        for wheel in pkg.get("wheels", []) or []:
            if wheel.get("url") and wheel.get("hash"):
                h = wheel["hash"].removeprefix("sha256:").lower()
                entries.append((name, version, "wheel", wheel["url"], h))
    return entries


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit uv.lock artifact hashes against the registry's served bytes.",
    )
    parser.add_argument(
        "lock",
        nargs="?",
        default="uv.lock",
        help="Path to uv.lock (default: uv.lock)",
    )
    parser.add_argument(
        "--download",
        action="store_true",
        help="Download and hash each artifact instead of using HEAD checksum headers "
        "(use when the mirror does not return x-checksum-sha256).",
    )
    parser.add_argument(
        "--write-tsv",
        metavar="PATH",
        help="Also write the full audit table to this TSV path.",
    )
    args = parser.parse_args()

    if not os.path.exists(args.lock):
        print(f"lock file not found: {args.lock}", file=sys.stderr)
        return 2

    entries = collect_entries(args.lock)
    verify = download_sha256 if args.download else head_sha256
    mode = "download+hash" if args.download else "HEAD x-checksum-sha256"
    print(
        f"Auditing {len(entries)} artifacts from {args.lock} ({mode}) ...",
        file=sys.stderr,
    )

    def check(entry: Entry):
        name, version, kind, url, expected = entry
        actual, err = verify(url)
        if err:
            status = "ERROR"
        elif actual == expected:
            status = "MATCH"
        else:
            status = "MISMATCH"
        return status, name, version, kind, expected, actual, err, url

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        results = list(pool.map(check, entries))

    mismatches = [r for r in results if r[0] == "MISMATCH"]
    errors = [r for r in results if r[0] == "ERROR"]
    matches = [r for r in results if r[0] == "MATCH"]

    if args.write_tsv:
        with open(args.write_tsv, "w") as out:
            out.write("status\tname\tversion\tkind\texpected\tactual\terror\turl\n")
            out.writelines("\t".join(str(x) for x in r) + "\n" for r in sorted(results))

    print(f"\nMATCH={len(matches)} MISMATCH={len(mismatches)} ERROR={len(errors)}\n")

    if mismatches:
        print("=== MISMATCHES (patch these hashes in uv.lock) ===")
        for _s, name, version, kind, expected, actual, _e, _u in sorted(mismatches):
            print(f"{name}=={version} [{kind}]")
            print(f"  lock:     sha256:{expected}")
            print(f"  registry: sha256:{actual}")
    if errors:
        print("\n=== ERRORS (could not verify -- check auth/URL, or try --download) ===")
        for _s, name, version, kind, _exp, _act, err, url in sorted(errors):
            print(f"{name}=={version} [{kind}] -> {err}\n  {url}")

    return 1 if mismatches else 0


if __name__ == "__main__":
    raise SystemExit(main())
