#!/usr/bin/env python3
"""
Build an MSIX from a PyInstaller onedir without the MSIX GUI/CLI templates.
- Copies your dist/ to a staging folder
- Writes a minimal AppxManifest.xml
- Calls MakeAppx.exe to pack into .msix
- Verifies result size

Usage: python build_msix.py
"""

import shutil, sys, subprocess
from pathlib import Path
from textwrap import dedent

# ========= EDIT THESE VALUES =========
DIST   = Path(r"C:\Users\steven-elitedesk\Documents\ImpulseQt\dist")
OUT    = Path(r"C:\Users\steven-elitedesk\Documents\ImpulseQt\MSIX")
STAGE  = Path(r"C:\Users\steven-elitedesk\Documents\ImpulseQt\stage")

# MUST MATCH PARTNER CENTER EXACTLY:
IDENTITY_NAME = "StevenSesselmann.ImpulseQt"

PUBLISHER       = "CN=14005534-7E89-4B87-AF78-8BF52D151431"

DISPLAY_NAME    = "ImpulseQt"
PUBLISHER_NAME  = "Steven Sesselmann"
DESCRIPTION     = "Gamma spectrometry interface and analysis tool."
VERSION         = "3.1.3.0"
ARCH            = "x64"

# Your project assets folder (where you generated the icons)
PROJECT_ASSETS  = Path(r"C:\Users\steven-elitedesk\Documents\ImpulseQt\assets")

# The exact icon files we’ll package (base + auto scales)
STORE_LOGO_BASE = "storelogo.scale-100.png"   # 50x50 base
ICON44_BASE     = "icon44.scale-100.png"      # 44x44 base
ICON150_BASE    = "icon150.scale-100.png"     # 150x150 base
# =====================================


def fail(msg, code=2):
    print(f"❌ {msg}", file=sys.stderr)
    sys.exit(code)


def find_makeappx() -> Path:
    """Try to locate MakeAppx.exe from Windows 10/11 SDK."""
    kits = Path(r"C:\Program Files (x86)\Windows Kits\10\bin")
    if kits.exists():
        for p in kits.iterdir():
            cand = p / "x64" / "makeappx.exe"
            if cand.exists():
                return cand
    # Fallback to a common latest SDK path
    cand = Path(r"C:\Program Files (x86)\Windows Kits\10\bin\10.0.26100.0\x64\makeappx.exe")
    if cand.exists():
        return cand
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
        <!-- Store logo should be the 50x50 base -->
        <Logo>assets\\{STORE_LOGO_BASE}</Logo>
      </Properties>

      <Resources>
        <Resource Language="en-us" />
      </Resources>

      <Dependencies>
        <TargetDeviceFamily Name="Windows.Desktop" MinVersion="10.0.19041.0" MaxVersionTested="10.0.26100.0"/>
      </Dependencies>

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
            BackgroundColor="#2B2B2B"
            Square44x44Logo="assets\\{ICON44_BASE}"
            Square150x150Logo="assets\\{ICON150_BASE}">
            <!-- Optional: supply a 310x310 tile later if you have artwork
            <uap:DefaultTile Square310x310Logo="assets\\icon310.png"/>
            -->
          </uap:VisualElements>
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

    # copy only the needed icons into stage/assets
    stage_assets = STAGE / "assets"
    stage_assets.mkdir(parents=True, exist_ok=True)

    needed = [
        STORE_LOGO_BASE, "storelogo.scale-200.png", "storelogo.scale-400.png",
        ICON44_BASE, "icon44.scale-200.png", "icon44.scale-400.png",
        ICON150_BASE, "icon150.scale-200.png", "icon150.scale-400.png",
    ]
    for name in needed:
        src = PROJECT_ASSETS / name
        if not src.exists():
            fail(f"Missing asset: {src}")
        shutil.copy2(src, stage_assets / name)

    # write manifest
    manifest_path = STAGE / "AppxManifest.xml"
    print(f"📝 Writing manifest → {manifest_path}")
    write_manifest(manifest_path)

    # pack
    makeappx = find_makeappx()
    out_msix = OUT / f"{DISPLAY_NAME}_{ARCH}.msix"
    print(f"🛠️  Packing with: {makeappx}")
    proc = subprocess.run([str(makeappx), "pack", "/d", str(STAGE), "/p", str(out_msix)],
                          text=True, capture_output=True)

    if proc.returncode != 0:
        print(proc.stdout)
        print(proc.stderr, file=sys.stderr)
        fail(f"MakeAppx failed with exit code {proc.returncode}")

    # optional validate
    _ = subprocess.run([str(makeappx), "validate", "/p", str(out_msix)],
                       text=True, capture_output=True)

    if not out_msix.exists():
        fail("MSIX not created.")
    size_mb = out_msix.stat().st_size / (1024 * 1024)
    if size_mb < 1.0:
        fail(f"MSIX output is too small ({size_mb:.2f} MB) — something is wrong.")

    print(f"✅ Done: {out_msix}  ({size_mb:.1f} MB)")
    print("   Upload this file to Partner Center → Windows → Your product → New submission → Packages.")


if __name__ == "__main__":
    main()
