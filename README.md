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

Each time you exit the program, you’ll see a quick 👍 or 👎 feedback popup. Please don’t ignore it — it’s not annoying, it’s helpful. Your feedback directly shapes future versions!

---

### **Installing**

You **don’t need Python installed**. ImpulseQt comes bundled as a standalone executable that includes everything it needs to run.

On first launch, it creates a folder:
