#!/usr/bin/env python3
"""
Build an MSIX from a PyInstaller onedir without the MSIX GUI/CLI templates.
- Copies your dist/ to a staging folder
- Writes a minimal AppxManifest.xml
- Calls MakeAppx.exe to pack into .msix
- Verifies result size

Usage: python build_msix.py
"""

import os, shutil, sys, subprocess
from pathlib import Path
from textwrap import dedent

# ========= EDIT THESE VALUES =========
# Folder that CONTAINS ImpulseQt.exe (PyInstaller onedir output)
DIST   = Path(r"C:\Users\steven-elitedesk\Documents\ImpulseQt\dist")

# Output folder for the .msix
OUT    = Path(r"C:\Users\steven-elitedesk\Documents\ImpulseQt\MSIX")

# Staging folder (temporary build folder)
STAGE  = Path(r"C:\Users\steven-elitedesk\Documents\ImpulseQt\stage")

# Store identity (copy EXACTLY from Partner Center → Windows → Account settings → App identity)
IDENTITY_NAME   = "StevenSesselmann.ImpulseQt"   
PUBLISHER       = "CN=14005534-7E89-4B87-AF78-8BF52D151431"         

# Display metadata
DISPLAY_NAME    = "ImpulseQt"
PUBLISHER_NAME  = "Steven Sesselmann"
DESCRIPTION     = "Gamma spectrometry interface and analysis tool."

# Version must be A.B.C.D and must increase each Store submission
VERSION         = "3.1.2.0"

# Icons (provide PNGs at these paths or adjust below)
ICON150         = STAGE / "images" / "icon150.png"
ICON44          = STAGE / "images" / "icon44.png"

# Target architecture (x64 / x86 / arm64)
ARCH            = "x64"
# =====================================


def fail(msg, code=2):
    print(f"❌ {msg}", file=sys.stderr)
    sys.exit(code)


def find_makeappx() -> Path:
    """Try to locate MakeAppx.exe from Windows 10/11 SDK."""
    candidates = []
    kits = Path(r"C:\Program Files (x86)\Windows Kits\10\bin")
    if kits.exists():
        for p in kits.iterdir():
            if p.is_dir() and (p / "x64" / "makeappx.exe").exists():
                candidates.append(p / "x64" / "makeappx.exe")
    # Fallback to a common latest SDK path
    candidates.append(Path(r"C:\Program Files (x86)\Windows Kits\10\bin\10.0.26100.0\x64\makeappx.exe"))
    for c in candidates:
        if c.exists():
            return c
    fail("MakeAppx.exe not found. Install the Windows SDK:\n"
         "  winget install --id Microsoft.WindowsSDK")


def write_manifest(manifest_path: Path):
    manifest = dedent(f"""\
    <?xml version="1.0" encoding="utf-8"?>
    <Package
      xmlns="http://schemas.microsoft.com/appx/manifest/foundation/windows10"
      xmlns:uap="http://schemas.microsoft.com/appx/manifest/uap/windows10"
      xmlns:uap10="http://schemas.microsoft.com/appx/manifest/uap/windows10/10"
      xmlns:rescap="http://schemas.microsoft.com/appx/manifest/foundation/windows10/restrictedcapabilities">

      <Identity
        Name="{IDENTITY_NAME}"
        Publisher="{PUBLISHER}"
        Version="{VERSION}"
        ProcessorArchitecture="{ARCH}" />

      <Properties>
        <DisplayName>{DISPLAY_NAME}</DisplayName>
        <PublisherDisplayName>{PUBLISHER_NAME}</PublisherDisplayName>
        <Description>{DESCRIPTION}</Description>
        <Logo>images\\icon150.png</Logo>
      </Properties>

      <Resources>
        <Resource Language="en-us" />
      </Resources>

      <Dependencies>
        <TargetDeviceFamily Name="Windows.Desktop" MinVersion="10.0.19041.0" MaxVersionTested="10.0.26100.0"/>
      </Dependencies>

      <!-- Full trust desktop app => behaves like your EXE (serial/audio OK) -->
      <Capabilities>
        <rescap:Capability Name="runFullTrust"/>
      </Capabilities>

      <Applications>
        <Application
          Id="ImpulseQt"
          Executable="ImpulseQt.exe"
          uap10:RuntimeBehavior="packagedClassicApp"
          uap10:TrustLevel="mediumIL">
          <uap:VisualElements
            DisplayName="{DISPLAY_NAME}"
            Description="{DESCRIPTION}"
            Square150x150Logo="images\\icon150.png"
            Square44x44Logo="images\\icon44.png"
            BackgroundColor="#2B2B2B"/>
        </Application>
      </Applications>
    </Package>
    """)
    manifest_path.write_text(manifest, encoding="utf-8")


def main():
    exe = DIST / "ImpulseQt.exe"
    if not exe.exists():
        fail(f"ImpulseQt.exe not found in DIST: {exe}")

    # fresh stage & out
    if STAGE.exists():
        shutil.rmtree(STAGE, ignore_errors=True)
    STAGE.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)

    # copy onedir files to stage root
    print(f"📦 Copying files → {STAGE}")
    shutil.copytree(DIST, STAGE, dirs_exist_ok=True)

    # ensure icons exist (placeholders if missing)
    ICON150.parent.mkdir(parents=True, exist_ok=True)
    for icon in (ICON150, ICON44):
        if not icon.exists():
            # write a tiny 1x1 transparent PNG as placeholder
            icon.write_bytes(
                bytes.fromhex(
                    "89504E470D0A1A0A0000000D49484452000000010000000108060000001F15C4890000000A49444154789C6360000002000100"
                    "05FE02FEA7C20D0000000049454E44AE426082"
                )
            )

    # write manifest
    manifest_path = STAGE / "AppxManifest.xml"
    print(f"📝 Writing manifest → {manifest_path}")
    write_manifest(manifest_path)

    # locate makeappx
    makeappx = find_makeappx()
    out_msix = OUT / f"{DISPLAY_NAME}_{ARCH}.msix"

    # pack
    print(f"🛠️  Packing with: {makeappx}")
    cmd = [str(makeappx), "pack", "/d", str(STAGE), "/p", str(out_msix)]
    proc = subprocess.run(cmd, text=True, capture_output=True)

    if proc.returncode != 0:
        print(proc.stdout)
        print(proc.stderr, file=sys.stderr)
        fail(f"MakeAppx failed with exit code {proc.returncode}")

    # optional validate
    cmd_val = [str(makeappx), "validate", "/p", str(out_msix)]
    _ = subprocess.run(cmd_val, text=True, capture_output=True)

    if not out_msix.exists():
        fail("MSIX not created.")
    size_mb = out_msix.stat().st_size / (1024 * 1024)
    if size_mb < 1.0:
        fail(f"MSIX output is too small ({size_mb:.2f} MB) — something is wrong.")

    print(f"✅ Done: {out_msix}  ({size_mb:.1f} MB)")
    print("   Upload this file to Partner Center → Windows → Your product → New submission → Packages.")

if __name__ == "__main__":
    main()
