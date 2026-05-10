# Godot Nix Flake

**Every published Godot Engine release — Standard & Mono — packaged as a Nix flake.**

Run any Godot version on Nix/NixOS with one command. Auto-updated daily from [`godotengine/godot-builds`](https://github.com/godotengine/godot-builds).

---

## About this fork

This is a fork of [**redyf/godot-nix-flake**](https://github.com/redyf/godot-nix-flake), extended to:

- Expose **every released Godot version** (stable, RC, beta, dev) instead of a single hand-pinned one.
- Support both **Standard** and **Mono** flavors automatically.
- Support both `x86_64-linux` and `aarch64-linux`.
- Auto-track new releases via a daily GitHub Actions job that opens a PR when new versions ship.

**Huge thanks to [@redyf](https://github.com/redyf)** for the original flake — the packaging logic (autoPatchelf wiring, .NET runtime setup, Mono variant handling) is built directly on their work.

---

## Usage

### Run any version directly

```bash
# Latest stable (default)
nix run github:AnteWall/godot-nix-flake

# Latest stable, Mono
nix run github:AnteWall/godot-nix-flake#default-mono

# Newest release of any kind (incl. RC / beta / dev)
nix run github:AnteWall/godot-nix-flake#latest
nix run github:AnteWall/godot-nix-flake#latest-mono

# A specific version (any tag from godot-builds)
nix run github:AnteWall/godot-nix-flake#"4.5-stable"
nix run github:AnteWall/godot-nix-flake#"4.5-stable-mono"
nix run github:AnteWall/godot-nix-flake#"4.6.3-rc1"
nix run github:AnteWall/godot-nix-flake#"4.6-dev3-mono"
```

> Quote the attribute name when it contains dots — your shell will otherwise treat them as path separators.

### Build locally

```bash
nix build github:AnteWall/godot-nix-flake#"4.6.3-rc1"
./result/bin/godot
```

For Mono builds the wrapper exposes `godot-mono`:

```bash
nix build github:AnteWall/godot-nix-flake#default-mono
./result/bin/godot-mono
```

### List all available versions

```bash
nix flake show github:AnteWall/godot-nix-flake
```

…or browse [`versions.json`](./versions.json).

---

## Aliases

| Attribute       | Resolves to                                  |
|-----------------|----------------------------------------------|
| `default`       | latest `*-stable` release, Standard          |
| `default-mono`  | latest `*-stable` release, Mono              |
| `latest`        | newest release of any kind, Standard         |
| `latest-mono`   | newest release of any kind, Mono             |
| `<tag>`         | exact upstream tag, Standard                 |
| `<tag>-mono`    | exact upstream tag, Mono                     |

`<tag>` is whatever appears in [`godot-builds` releases](https://github.com/godotengine/godot-builds/releases) — e.g. `4.5-stable`, `4.6.3-rc1`, `4.6-dev3`.

---

## Supported platforms

- `x86_64-linux`
- `aarch64-linux`

For Mono builds, .NET SDK 8 and runtime are bundled — no host-side .NET required. `LD_LIBRARY_PATH`, `PATH`, and `DOTNET_ROOT` are wired up by the wrapper.

---

## Using in another flake

```nix
{
  inputs.godot.url = "github:AnteWall/godot-nix-flake";

  outputs = { self, nixpkgs, godot, ... }: {
    # e.g. NixOS module / home-manager
    environment.systemPackages = [
      godot.packages.x86_64-linux.default          # latest stable
      godot.packages.x86_64-linux."4.5-stable"     # pinned version
    ];
  };
}
```

---

## How auto-updates work

`.github/workflows/update-versions.yml` runs daily. It:

1. Fetches all releases from `godotengine/godot-builds` via the GitHub API.
2. Reads each asset's `digest` (SHA256) directly from the API.
3. Regenerates `versions.json`.
4. Opens a PR (`chore/update-godot-versions`) **against this repository only**.

---

## Acknowledgements

- [**redyf/godot-nix-flake**](https://github.com/redyf/godot-nix-flake) — the original flake this is forked from. Thank you!
- [**Godot Engine**](https://godotengine.org) — the engine itself.
- [**godotengine/godot-builds**](https://github.com/godotengine/godot-builds) — upstream release artifacts and digests.

---

## License

[MIT](./LICENSE)
