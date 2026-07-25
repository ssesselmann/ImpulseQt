{
  description = "ImpulseQt dev environment: uv-managed Python inside an FHS shell";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs { inherit system; };

        # Runtime shared libraries that manylinux wheels (PySide6/Qt6 xcb
        # platform plugin, PyAudio -> portaudio, numpy/scipy -> libstdc++)
        # expect to find on a normal FHS Linux distro but that don't exist
        # in plain paths on NixOS.
        runtimeLibs = with pkgs; [
          stdenv.cc.cc.lib # libstdc++, libgomp
          zlib
          portaudio
          alsa-lib
          fontconfig
          freetype
          glib
          dbus
          libGL
          libglvnd
          libxkbcommon
          libx11
          libxext
          libxrender
          libxcb
          libxi
          libsm
          libice
          libxrandr
          libxshmfence
          libxcb-cursor
          libxcb-image
          libxcb-keysyms
          libxcb-render-util
          libxcb-wm
          libxcb-errors
        ];

        fhs = pkgs.buildFHSEnv {
          name = "impulseqt-fhs";

          targetPkgs = pkgs: (with pkgs; [
            uv
            python312
          ]) ++ runtimeLibs;

          # Let PySide6's Qt plugins (xcb, image formats, etc.) find each
          # other's shared libs without extra LD_LIBRARY_PATH plumbing.
          runScript = "bash";

          profile = ''
            # Use the FHS-provided CPython instead of letting uv download a
            # foreign python-build-standalone glibc binary (which cannot
            # execute outside an FHS/NixOS-patched environment).
            export UV_PYTHON_PREFERENCE=only-system
            export UV_PYTHON=python3.12
          '';
        };
      in
      {
        # `nix develop` -> interactive FHS shell for humans.
        devShells.default = fhs.env;

        # `nix run . -- <cmd>` -> non-interactive, scriptable FHS entrypoint
        # (the .env shellHook execs into the sandbox, which breaks
        # `nix develop --command`; this package form forwards argv instead).
        packages.default = fhs;
      });
}
