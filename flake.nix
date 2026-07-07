{
  description = "Godot Engine packages (Standard & Mono) for every published release of godotengine/godot-builds";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  };

  outputs = {
    self,
    nixpkgs,
  }: let
    supportedSystems = [
      "x86_64-linux"
      "aarch64-linux"
    ];

    forAllSystems = f:
      nixpkgs.lib.genAttrs supportedSystems (system: f system nixpkgs.legacyPackages.${system});

    data = builtins.fromJSON (builtins.readFile ./versions.json);

    mkGodot = {
      pkgs,
      version,
      mono,
      url,
      sha256,
    }: let
      suffix =
        if mono
        then "-mono"
        else "";

      dotnetSdk = pkgs.dotnet-sdk_10;
      dotnetRuntime = pkgs.dotnet-runtime_10;

      desktopItem = pkgs.makeDesktopItem {
        name = "godot" + suffix;
        desktopName = "Godot" + suffix;
        exec = "godot" + suffix + " %f";
        icon = "godot";
        terminal = false;
        categories = ["Development" "IDE"];
        mimeTypes = [
          "application/x-godot-project"
        ];
      };

      icon = pkgs.fetchurl {
        name = "icon.png";
        hash = "sha256-zIgTMu5S3rT06a4TpSP8ffBqDC/TG7sX+vpZMfKrctY=";
        url = "https://godotengine.org/assets/press/icon_color.png";
      };

      dotnetPkgs = [
        dotnetSdk
        dotnetRuntime
      ];

      runtimeLibs = with pkgs;
        [
          xorg.libX11
          xorg.libXcursor
          xorg.libXinerama
          xorg.libXrandr
          xorg.libXi
          xorg.libXext
          libGL
          alsa-lib
          libpulseaudio
          wayland
          systemd
          dbus
          fontconfig
          freetype
          zlib
          stdenv.cc.cc.lib
          libxkbcommon
        ]
        ++ (
          if mono
          then dotnetPkgs
          else []
        );
    in
      pkgs.stdenv.mkDerivation {
        pname = "godot${suffix}";
        inherit version;

        src = pkgs.fetchurl {
          inherit url sha256;
          name = "godot${suffix}-${version}.zip";
        };

        nativeBuildInputs = with pkgs; [
          unzip
          autoPatchelfHook
          makeWrapper
        ];

        buildInputs = runtimeLibs;

        unpackPhase = ''
          mkdir src
          cd src
          unzip $src
        '';

        configurePhase = pkgs.lib.optionalString mono ''
          export DOTNET_ROOT="${dotnetSdk}"
          export PATH="${dotnetSdk}/bin:$PATH"
        '';

        installPhase = ''
          mkdir -p $out/bin $out/lib
          cp -r ./* $out/lib/

          godot_bin=$(find $out/lib -type f -name "Godot_*" ! -name "*.so" ! -name "*.dll" | head -n 1)
          if [ -z "$godot_bin" ]; then
            echo "Could not locate Godot binary" >&2
            exit 1
          fi
          chmod +x "$godot_bin"

          makeWrapper "$godot_bin" $out/bin/godot${suffix} \
            --prefix LD_LIBRARY_PATH : "${pkgs.lib.makeLibraryPath runtimeLibs}" \
            ${pkgs.lib.optionalString mono ''--prefix PATH : "${pkgs.lib.makeBinPath [dotnetSdk]}"''} \
            ${pkgs.lib.optionalString mono ''--set DOTNET_ROOT "${dotnetSdk}"''}

           mkdir -p $out/share/icons/hicolor/256x256/apps
          cp ${icon} \
            $out/share/icons/hicolor/256x256/apps/godot.png

          mkdir -p $out/share/applications
          cp ${desktopItem}/share/applications/* \
            $out/share/applications/
        '';

        meta = {
          description = "Godot Engine ${version}${
            if mono
            then " (Mono / .NET)"
            else ""
          }";
          homepage = "https://godotengine.org";
          platforms = ["x86_64-linux" "aarch64-linux"];
        };
      };

    # Build the per-system package set from versions.json.
    packagesFor = system: pkgs: let
      releases = data.releases;

      # For each release tag, emit `<tag>` (standard) and `<tag>-mono`
      # if the corresponding asset exists for this system.
      perTag = tag: rel: let
        sysAssets = rel.assets.${system} or {};
        mkPair = flavor: let
          asset = sysAssets.${flavor};
          isMono = flavor == "mono";
          attrName =
            if isMono
            then "${tag}-mono"
            else tag;
        in {
          name = attrName;
          value = mkGodot {
            inherit pkgs;
            version = tag;
            mono = isMono;
            inherit (asset) url sha256;
          };
        };
        flavors = builtins.attrNames sysAssets;
      in
        map mkPair flavors;

      allPairs = builtins.concatLists (
        nixpkgs.lib.mapAttrsToList perTag releases
      );

      base = builtins.listToAttrs allPairs;

      # Aliases. Only added if the underlying attr exists for this system.
      maybeAlias = name: target:
        if builtins.hasAttr target base
        then {${name} = base.${target};}
        else {};

      aliases =
        (maybeAlias "default" data.latest_stable)
        // (maybeAlias "default-mono" "${data.latest_stable}-mono")
        // (maybeAlias "latest" data.latest_any)
        // (maybeAlias "latest-mono" "${data.latest_any}-mono");
    in
      base // aliases;
  in {
    packages = forAllSystems packagesFor;
  };
}
