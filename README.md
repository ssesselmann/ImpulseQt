# ImpulseQt

**ImpulseQt — A Complete Refactor of Impulse**

Impulse started as an experiment: could a Multi-Channel Analyzer (MCA) be written in Python using Dash-Plotly to run in a browser? It worked — but many users found it slow and unresponsive. This was mostly due to the Dash-Plotly GUI, which is great for static plots but not ideal for dynamic, real-time applications like a continuously updating MCA.

So I rewrote the program using **PySide6** for the front-end GUI. The result? A smaller app bundle, a faster and more responsive interface — and best of all, the program now actually quits cleanly when you close the window!

---

### **Multi-Device Support**

Just like the original Impulse, **ImpulseQt** supports **multiple hardware types**. It operates in two modes:
- **Sound card spectrometers** such as *GammaSpectacular* and *Theremino*
- **USB MCAs** including *Atom Spectrometers* and *GS-MAX*

While the GUI is shared, each device type uses its own dedicated engine under the hood.

---

### **Multi-Platform**

ImpulseQt is written in Python and compiled for **Windows** and **macOS**. (Yes, there are a few of us Mac users in the scientific world!)  
**Linux** users can run it directly from source.

---

### **Open Source**

ImpulseQt is open source under the **MIT License** — which means you're free to copy, modify, fork, or even steal it.  
Just be respectful, and remember the **hundreds of hours** I spent designing, coding, and debugging this software.

---

### **Feedback**

Your feedback is appreciated, it shapes future versions!

---

### **Installing**

On **Windows** and **macOS** you **don’t need Python installed**. ImpulseQt comes bundled as a standalone executable that includes everything it needs to run.

On **Linux**, run it from source with [uv](https://docs.astral.sh/uv/):

```sh
uv run ImpulseQt.py
```

`uv` reads `pyproject.toml`/`uv.lock`, creates a `.venv`, installs the pinned dependencies (PySide6, numpy, scipy, PyAudio, etc.) and launches the app. PyAudio needs PortAudio's headers/library to build; on Debian/Ubuntu install them first with `sudo apt install portaudio19-dev`, on Fedora `sudo dnf install portaudio-devel`.

#### NixOS

Manylinux wheels (PySide6's Qt6 plugins, PyAudio's PortAudio binding) expect shared libraries in standard FHS paths that don't exist on NixOS. This repo ships a `flake.nix` that provides an FHS-compatible dev shell with `uv` and all the required runtime libraries (Qt6/xcb, OpenGL, ALSA/PortAudio, etc.):

```sh
nix develop
uv run ImpulseQt.py
```

`nix develop` drops you into a sandboxed shell that looks like a normal FHS Linux distro to `uv` and the wheels it installs — no manual `LD_LIBRARY_PATH` wrangling needed.

On first launch, it creates a folder:

C:\Users\Username\ImpulseQtData

This is where it stores:
- isotope libraries
- your recorded files
- custom settings

On Windows, it also writes logs and settings to:

C:\Users\Username\AppData\Local\ImpulseQt\logs\impulse.log
C:\Users\Username\AppData\Roaming\ImpulseQt\settings

---

### **Downloading**

Download the latest release here:  
👉 https://github.com/ssesselmann/ImpulseQt/releases

---

### **Thank You**

Thank you for downloading **ImpulseQt**. I hope it helps with your experiments — and maybe even contributes to real science. If you end up publishing your work, I’d be grateful if you gave ImpulseQt a mention.

**Steven Sesselmann**  
Sydney, NSW, Australia  
https://www.GammaSpectacular.com




