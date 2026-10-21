---
name: uv-artifactory-hash-repair
description: 'Resolve UV lock hash mismatch failures against Artifactory or any private PyPI mirror in any Python project. Use when uv sync --locked fails in CI or local with a Hash mismatch -- especially Jenkins, buildpack, or container builds. Audits the whole uv.lock in one pass to catch every drifted wheel/sdist at once (CI only reports the first), then patches and verifies. Trigger whenever someone reports a uv hash mismatch, a locked sync failing in CI, or asks to fix "all out of sync" lock hashes.'
argument-hint: 'Paste the uv hash mismatch block or package name/version (for example: proto-plus==1.27.1)'
user-invocable: true
disable-model-invocation: false
---

# UV Artifactory Hash Repair

## What This Skill Produces
- A minimal, targeted `uv.lock` repair for hash drift served by Artifactory (or another private mirror).
- A full audit of every artifact in the lock, so all drifted wheels/sdists get fixed in one pass -- not just the one CI happened to report first.
- Verification that `uv sync --locked --no-default-groups` succeeds afterward on a clean cache.

## When To Use
- `uv sync --locked` fails with `Hash mismatch for <package==version>` in CI/Jenkins/buildpack or locally.
- A private mirror (Artifactory, Nexus, etc.) re-mirrored upstream and one or more lock hashes drifted.
- Someone asks to fix "all out of sync" lock hashes, or a lock that worked yesterday fails today.

## Key Insight: Audit The Whole Lock, Not Just The Reported Package
CI stops at the **first** hash failure, so the build log names a single package -- but a mirror re-sync usually drifts several wheels at once. If you patch only the reported one, the next `uv sync` just fails on the next drifted package, and you burn a CI round-trip per package. (Real example: a build reported only `email-validator`, but the lock actually had 10 drifted wheels.)

The fast path is therefore to audit **every** artifact URL in `uv.lock` up front, find all the drift together, patch it in one go, and validate once.

You don't need to download artifacts to check them: Artifactory returns the true SHA-256 in the `x-checksum-sha256` response header on a HEAD request (`curl -fsSL -I --netrc <url>`). This matches the real downloaded bytes and makes auditing ~1000 artifacts take seconds. The bundled `scripts/audit_uv_lock.py` does exactly this across the whole lock in parallel.

## Inputs
- The failing command output (package/version + Expected vs Computed hash) -- confirms the registry and whether the bad artifact is a wheel or sdist.
- The project `uv.lock`.
- Authenticated access to the mirror -- typically `~/.netrc`, which both `curl --netrc` and `uv` read.

## Procedure
1. Confirm the registry and credentials.
   - From the failing log, note the package, version, and whether the bad artifact is a wheel or sdist.
   - Sanity-check access: `curl -fsSL -I --netrc <wheel-url-from-lock>` should return `200` with an `x-checksum-sha256` header. A 401/403/404 means fix auth or the URL first (see Decision Points).

2. Audit the entire lockfile -- not just the reported package.
   - Run the bundled script against the project's lock (it lives next to this SKILL.md, so substitute its directory for `<skill-dir>`):
     - `python <skill-dir>/scripts/audit_uv_lock.py uv.lock`
   - It parses every `[[package]]`, HEADs each sdist and wheel URL in parallel, and prints `MATCH / MISMATCH / ERROR` counts followed by every mismatch with both the lock hash and the registry hash.
   - If your mirror doesn't return the checksum header (you'll see `ERROR ... no_checksum_header`), re-run with `--download` to fetch and hash each artifact instead.

3. Patch every mismatched hash.
   - For each `MISMATCH`, replace the `hash = "sha256:<lock>"` value in that package's block with the registry value the audit printed. Patch the wheel hash for wheel drift, the sdist hash for sdist drift.
   - Each SHA-256 is unique across the lock, so a direct per-hash find-and-replace is safe and keeps the diff minimal. Don't re-lock the whole file or touch URLs, versions, or dependencies.

4. Validate with a clean cache.
   - Use an isolated cache so stale local bytes can't mask the result:
     - `UV_CACHE_DIR="$PWD/.uv-cache-hashfix" uv sync --locked --no-default-groups`
   - Expect exit code 0. To prove the *download* path verifies (not just a cache hit), force a fresh pull of the packages you patched:
     - `UV_CACHE_DIR="$PWD/.uv-cache-fresh" uv sync --locked --no-default-groups --reinstall-package <pkg1> --reinstall-package <pkg2> ...`

5. Re-audit and confirm a minimal diff.
   - Re-run the audit and expect `MISMATCH=0`.
   - Check `git diff uv.lock` shows only hash-line changes, then remove any temporary cache dirs you created.

6. Iterate only if needed.
   - If the audit reported `ERROR` rows you couldn't resolve, fix access and re-run for those.
   - Mirrors re-sync over time, so if new drift appears later the same one-pass audit handles it.

## Decision Points And Branching
- Auth failure (401/403/404):
  - Verify `~/.netrc` has the mirror host and that the URL from the lock is correct.
  - If the registry is genuinely down, stop and report the exact failing URL as a blocker rather than guessing hashes.

- Mirror doesn't expose `x-checksum-sha256`:
  - Run the audit with `--download`. Slower, but it hashes the real bytes and works on any mirror.

- Multiple wheels in one package block:
  - Patch only the wheel(s) the audit flags as `MISMATCH`. It checks each wheel URL independently, so platform/marker-specific wheels are handled correctly.

- Mirror drift versus PyPI drift:
  - Trust the bytes served by the CI mirror, not a public PyPI checksum. A private mirror can legitimately serve different (re-mirrored) bytes for the same version.

- Wheel versus sdist:
  - In practice the wheel hash drifts while the sdist stays stable, but always patch whichever the audit flags.

## Quality Gates
- The audit reports `MISMATCH=0` after patching.
- `uv sync --locked --no-default-groups` succeeds on a clean cache, including a forced fresh re-download of the patched packages.
- `git diff uv.lock` is restricted to hash fields for the affected packages -- no URL, version, or dependency changes.

## Recommended Command Snippets
```bash
# Verify one artifact's hash WITHOUT downloading it (Artifactory header).
curl -fsSL -I --netrc "<wheel-url-from-uv.lock>" | grep -i x-checksum-sha256

# Audit the whole lock at once (prints every drifted wheel/sdist).
python <skill-dir>/scripts/audit_uv_lock.py uv.lock
# Fallback for mirrors without the checksum header:
python <skill-dir>/scripts/audit_uv_lock.py uv.lock --download

# Fall back to downloading a single artifact and hashing it.
curl -fsSL --netrc "<url-from-uv.lock>" -o /tmp/pkg && shasum -a 256 /tmp/pkg

# Validate a locked sync with an isolated cache.
UV_CACHE_DIR="$PWD/.uv-cache-hashfix" uv sync --locked --no-default-groups
```

## Completion Checklist
- Confirmed the registry/auth from the failing log and a HEAD request.
- Audited the entire `uv.lock` and captured every `MISMATCH` (not just the package CI reported).
- Patched only the drifted hash fields, verified against the mirror's bytes.
- Re-ran the locked sync on a clean cache (plus a forced fresh re-download) and got exit 0.
- Confirmed a minimal, hash-only diff and recorded the result for the PR/Jenkins notes.
