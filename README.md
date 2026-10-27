# ImpulseQt

**An open source MCA for Gamma Spectrometry**

ImpulseQt is an easy and intuitive Python program for gamma spectrometry. It works equally well under Windows, Mac or Linux. 

A complete manual is embedded in the software, but the programmer's intention was that the manual would never be needed. 

**Features**
 - **Device setup tab** Select device type and fine-tune its settings
 - **Histogram tab** Record and analyse your pulse height histogram. Includes features like linear and logarithmic scale, Gaussian correlation plot, comparison spectrum, background subtraction, isotope library, coincidence counting (stereo sound cards only), calibration and CSV exports. 
 - **Waterfall tab** 3D Waterfall plot showing changes to your spectrum over time. This feature is compatible with an external USB GPS module and when connected can save spectrum as intervals with GPS coordinates and plot the counts directly on a map. 
 - **Count Rate tab** This tab plots the count rate over time and features a smoothing function as well as the ability to export CSV count rates.
 - **Manual tab** This tab contains the full manual and changes dynamically according to the selected device type. 

 Enjoy the simplicity of ImpulseQt and appreciate achieving the same results with fewer settings. 
---

### **Multi-Device Support**

**ImpulseQt** supports **multiple hardware types**. 
It operates in three modes:
- **Sound Card Spectrometer Mode** Works with devices such as *GammaSpectacular* and *Theremino*
- **ATOM USB MCAs** Works with *Atom Spectrometers* and *GS-MAX Spectrometers* USB UART 
- **Teensy MCA** Currently under development

Each device type has its own engine under the hood, but all share a common GUI.

---

### **Multi-Platform**

ImpulseQt is written in Python and compiled for **Windows** and **macOS**. (Yes, there are a few of us Mac users in the scientific world!)  
**Linux** users can run it directly from source using Python 3.10

---

### **Open Source**

ImpulseQt is open source under the **MIT License** — You’re free to use, copy, modify, and fork it under the MIT License

Just be respectful, and remember the **hundreds of hours** I spent designing, coding, and debugging this software.

---

### **Feedback**

Your feedback is appreciated it helps shape future versions!

---

### **Installation**

ImpulseQt has been written for Python 3.10 and works best with this version. If you have a newer or older version installed, I recommend creating a virtual environment using Python 3.10.
If you are running the compiled version you can ignore this instruction. 

On **Windows** and **macOS** you **don’t need Python installed**. ImpulseQt comes bundled as a standalone executable that includes everything it needs to run.

On **Linux**, run it from source with [uv](https://docs.astral.sh/uv/):

```sh
uv run ImpulseQt.py
```

`uv` reads `pyproject.toml`/`uv.lock`, creates a `.venv`, installs the pinned dependencies (PySide6, numpy, scipy, PyAudio, etc.) and launches the app. PyAudio needs PortAudio's headers/library to build; on Debian/Ubuntu install them first with `sudo apt install portaudio19-dev`, on Fedora `sudo dnf install portaudio-devel`.

#### NixOS

Many linux wheels (PySide6's Qt6 plugins, PyAudio's PortAudio binding) expect shared libraries in standard FHS paths that don't exist on NixOS. This repo ships a `flake.nix` that provides an FHS-compatible dev shell with `uv` and all the required runtime libraries (Qt6/xcb, OpenGL, ALSA/PortAudio, etc.):

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




