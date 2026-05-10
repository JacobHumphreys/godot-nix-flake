#!/usr/bin/env python3
"""
Fetch all Godot releases from godotengine/godot-builds and generate
versions.json describing every (version, system, flavor) tuple we package.

Safety: when running inside GitHub Actions (GITHUB_REPOSITORY set), refuses
to run if the current repository is a fork. This prevents the auto-update
workflow from opening PRs against an upstream parent repository. Local runs
(no GITHUB_REPOSITORY) are always allowed.
"""

from __future__ import annotations

import base64
import binascii
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

API = "https://api.github.com/repos/godotengine/godot-builds/releases"
PER_PAGE = 100
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "versions.json"

# (system, flavor) -> asset slug used in upstream filenames
ASSET_SLUGS: dict[tuple[str, str], str] = {
    ("x86_64-linux", "standard"): "linux.x86_64",
    ("x86_64-linux", "mono"): "mono_linux_x86_64",
    ("aarch64-linux", "standard"): "linux.arm64",
    ("aarch64-linux", "mono"): "mono_linux_arm64",
}


def guard_repo() -> None:
    """Refuse to run if executing inside a forked repository on GitHub Actions.

    The check is performed against the GitHub API so it works for any owner/name
    — nothing is hardcoded. Local runs (no GITHUB_REPOSITORY env var) are
    always permitted.
    """
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    if not repo:
        return
    try:
        info, _ = gh_get(f"https://api.github.com/repos/{repo}")
    except urllib.error.URLError as exc:
        sys.exit(f"Could not query repo metadata for {repo}: {exc}")
    if info.get("fork"):
        parent = (info.get("parent") or {}).get("full_name", "<unknown>")
        sys.exit(
            f"Refusing to run in fork '{repo}' (parent: {parent}). "
            "This guard prevents auto-PRs from being opened against the upstream repo."
        )


def gh_get(url: str) -> tuple[Any, dict[str, str]]:
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        headers = {k.lower(): v for k, v in resp.headers.items()}
    return data, headers


def parse_next_link(link_header: str | None) -> str | None:
    if not link_header:
        return None
    for part in link_header.split(","):
        segs = part.strip().split(";")
        if len(segs) < 2:
            continue
        url = segs[0].strip()
        if not (url.startswith("<") and url.endswith(">")):
            continue
        rel = segs[1].strip()
        if rel == 'rel="next"':
            return url[1:-1]
    return None


def fetch_all_releases() -> list[dict]:
    out: list[dict] = []
    url: str | None = f"{API}?per_page={PER_PAGE}"
    while url:
        page, headers = gh_get(url)
        out.extend(page)
        url = parse_next_link(headers.get("link"))
    return out


def hex_digest_to_sri(digest: str) -> str:
    """Convert "sha256:<hex>" to Nix SRI form "sha256-<base64>"."""
    if not digest.startswith("sha256:"):
        raise ValueError(f"Unsupported digest: {digest}")
    raw = binascii.unhexlify(digest.split(":", 1)[1])
    return "sha256-" + base64.b64encode(raw).decode("ascii")


def asset_for(assets: list[dict], tag: str, slug: str) -> dict | None:
    name = f"Godot_v{tag}_{slug}.zip"
    for a in assets:
        if a.get("name") == name:
            return a
    return None


def build_release_entry(release: dict) -> dict | None:
    tag = release.get("tag_name")
    if not tag:
        return None
    assets = release.get("assets") or []

    out_assets: dict[str, dict[str, dict]] = {}
    for (system, flavor), slug in ASSET_SLUGS.items():
        asset = asset_for(assets, tag, slug)
        if asset is None:
            continue
        digest = asset.get("digest")
        if not digest:
            # Skip assets without a published digest; they would require
            # downloading the full archive to hash. Rare in practice.
            continue
        try:
            sri = hex_digest_to_sri(digest)
        except (ValueError, binascii.Error):
            continue
        out_assets.setdefault(system, {})[flavor] = {
            "url": asset["browser_download_url"],
            "sha256": sri,
        }

    if not out_assets:
        return None

    return {
        "published_at": release.get("published_at"),
        "prerelease": bool(release.get("prerelease")),
        "assets": out_assets,
    }


def main() -> int:
    guard_repo()
    print("Fetching releases from godotengine/godot-builds ...", file=sys.stderr)
    releases = fetch_all_releases()
    print(f"Got {len(releases)} releases.", file=sys.stderr)

    entries: dict[str, dict] = {}
    for r in releases:
        entry = build_release_entry(r)
        if entry is None:
            continue
        entries[r["tag_name"]] = entry

    if not entries:
        sys.exit("No usable releases found.")

    # latest_any: newest by published_at
    latest_any = max(entries, key=lambda t: entries[t]["published_at"] or "")

    # latest_stable: newest non-prerelease whose tag ends in -stable
    stable_tags = [
        t for t, e in entries.items() if not e["prerelease"] and t.endswith("-stable")
    ]
    latest_stable = (
        max(stable_tags, key=lambda t: entries[t]["published_at"] or "")
        if stable_tags
        else None
    )

    out = {
        "latest_stable": latest_stable,
        "latest_any": latest_any,
        "releases": dict(sorted(entries.items())),
    }

    OUT.write_text(json.dumps(out, indent=2, sort_keys=False) + "\n")
    print(f"Wrote {OUT} ({len(entries)} versions).", file=sys.stderr)
    print(f"latest_stable={latest_stable}  latest_any={latest_any}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
