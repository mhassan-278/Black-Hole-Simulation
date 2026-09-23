# 🌌 Schwarzschild Black Hole — Interactive 3D Simulation

A real-time, GPU-accelerated general-relativistic ray tracer of a Schwarzschild black hole — written in Python.

Every pixel of every frame is a light ray traced backwards through curved spacetime — produced live at 60+ FPS.

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.8%2B-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/OpenGL-3.2%2B-5586A4?style=flat-square&logo=opengl&logoColor=white" alt="OpenGL">
  <img src="https://img.shields.io/badge/License-MIT-yellow?style=flat-square" alt="License">
  <img src="https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-informational?style=flat-square" alt="Platform">
</p>

---

## ✨ Features

### 🌌 Physics
- 🕳️ **Event horizon & black hole shadow**
- 💫 **Gravitational lensing** of background stars
- 🔭 **Einstein rings** & multiple disk images
- ⚡ **Relativistic Doppler beaming** (approaching side brighter)
- 🌡️ **Gravitational redshift** color shifts
- 🌀 **Photon sphere** at `r = 1.5 rs`

### 🎨 Rendering
- 🖥️ **Per-pixel GPU ray tracing**
- ✨ **Procedural starfield** with galactic band
- 🔥 **Accretion disk** with spiral turbulence
- 🎞️ **Tone mapping + gamma correction**
- 📐 **Adaptive step integration**
- 🎯 **60+ FPS** on modern GPUs

### 🎮 Interactivity
- 🖱️ **Mouse orbit** camera
- 🔍 **Wheel zoom** in / out
- 🔄 **Auto-rotate** mode
- ⌨️ **Keyboard shortcuts**
- 📊 **Live FPS counter** in the title bar

### 💻 Platform
- 🍎 **macOS** (OpenGL 3.2 + GLSL 150)
- 🪟 **Windows** (OpenGL 3.3+)
- 🐧 **Linux** (OpenGL 3.3+)
- 🔧 **Auto-detects GLSL version**
- 🧩 **Minimal dependencies**

---

## 🎮 Controls

| Input | Action |
|:-----:|:-------|
| 🖱️ **Left mouse drag** | Orbit the camera around the black hole |
| 🖱️ **Mouse wheel** | Zoom in / out |
| ⌨️ **SPACE** | Toggle automatic camera rotation |
| ⌨️ **R** | Reset camera to default position |
| ⌨️ **ESC** / **Q** | Quit the simulation |

---

## ⚙️ Installation

### Setup

```bash
# 1. Clone the repository
git clone https://github.com/mhassan-278/blackhole-sim.git
cd blackhole-sim

# 2. Create a virtual environment
python -m venv venv

# 3. Activate it
#    Linux / macOS:
source venv/bin/activate
#    Windows:
venv\Scripts\activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Run the simulation
python main.py
```

### 🍎 macOS Users

The code auto-detects macOS and uses **OpenGL 3.2 core** with **GLSL 150**.
If you see a black screen or pixelated window, run:

```bash
export SDL_VIDEO_HIGHDPI_DISABLED=1
python main.py
```

### 🐧 Linux Users

Check your GPU driver supports OpenGL 3.3+:

```bash
glxinfo | grep "OpenGL version"
```

If below 3.3, install `mesa-utils` and update your graphics drivers.

### 🪟 Windows Users

For best performance, also install:

```bash
pip install PyOpenGL_accelerate
```

Optional but recommended.

---

## 📦 Requirements

All dependencies are listed in `requirements.txt`:

```
pygame>=2.5.0
PyOpenGL>=3.1.6
numpy>=1.24.0
```

**Optional:**
```
PyOpenGL_accelerate>=3.1.6   # Faster rendering on Windows
```

Install everything at once:

```bash
pip install -r requirements.txt
```

---

## 📁 Project Structure

```
blackhole-sim/
├── main.py              # Core simulation (renderer + physics shader)
├── requirements.txt     # Python dependencies
├── README.md            # This file
├── LICENSE              # MIT License
└── .gitignore           # Git ignore rules
```

---

## 🧠 How It Works

### The Physics

The simulation integrates **null geodesics** in **Schwarzschild spacetime**.
With the Schwarzschild radius set to `rs = 1` (so `M = 0.5`, `c = G = 1`),
the orbit equation for a photon is:

```
d²u/dφ² + u = 3M u²     ,     u = 1/r
```

This is reproduced in Cartesian form by the **pseudo-Newtonian acceleration**:

```
a = -3M h² x / r⁵  =  -1.5 h² x / r⁵
```

where `h = |x × v|` is the conserved angular momentum of the ray.

This produces the correct:

| Physical Effect | Value |
|-----------------|-------|
| **Photon sphere** | `r = 1.5 rs` |
| **Black hole shadow** | apparent radius `√27 M ≈ 2.6 rs` |
| **ISCO** (disk inner edge) | `r = 3 rs` (6M) |
| **Einstein rings** | multiple images of the disk |

### The Rendering Pipeline

```
┌─────────────────────────────────────────────────────────────┐
│  PYTHON (CPU)                                               │
│  • Handle input (mouse, keyboard)                           │
│  • Compute camera basis (position, right, up, forward)      │
│  • Upload uniforms to GPU                                   │
└──────────────────────────┬──────────────────────────────────┘
                           │ uniforms
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  GPU (FRAGMENT SHADER — runs per pixel, in parallel)        │
│  1. Compute ray direction from camera                       │
│  2. Integrate null geodesic (300 steps)                     │
│  3. Detect accretion disk crossings                         │
│  4. Apply Doppler beaming + gravitational redshift          │
│  5. Sample procedural starfield if ray escapes              │
│  6. Tone map + gamma correct → output color                 │
└──────────────────────────┬──────────────────────────────────┘
                           │ texture
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  Framebuffer texture → fullscreen quad → screen             │
└─────────────────────────────────────────────────────────────┘
```

**Why this is fast:** the GPU processes **~600,000 rays in parallel**, each doing 300 physics steps per frame. Python alone would take hours per frame; the GPU does it in ~16 milliseconds.

---

## 🚀 Performance Tips

Edit the constants at the top of `main.py`:

| Variable | Default | Effect |
|----------|:-------:|--------|
| `RENDER_SCALE` | `0.70` | Lower = faster. Try `0.5` on weak GPUs. |
| `MAX_STEPS` (shader) | `300` | Lower = faster, less accurate near hole. |
| `DISK_OUTER` | `14.0` | Smaller disk = fewer ray crossings. |
| `WIDTH / HEIGHT` | `1280 × 720` | Smaller window = faster. |

**⚡ Quick win:** Set `RENDER_SCALE = 0.5` to roughly **double your FPS** with minimal visual difference.

---

## 🔬 Roadmap

- [x] Schwarzschild black hole (static, non-rotating)
- [x] Accretion disk with Doppler beaming
- [x] Gravitational lensing + Einstein rings
- [x] Procedural starfield
- [x] Cross-platform (macOS / Windows / Linux)
- [ ] **Kerr black hole** (rotating, frame-dragging, "D"-shaped shadow)
- [ ] **Volumetric disk** with real 3D density falloff
- [ ] **Polar jets** & magnetic field lines
- [ ] **Bloom / lens flare** post-processing
- [ ] **Free-fly camera** — fall into the hole!
- [ ] **VR support** — stereoscopic two-eye rendering
- [ ] **HUD** — distance, time dilation, orbital velocity

PRs welcome! Open an issue to discuss before starting big features.

---

## 🤝 Contributing

Contributions are what make the open-source community amazing.

1. **Fork** the project
2. **Create** your feature branch (`git checkout -b feature/AmazingFeature`)
3. **Commit** your changes (`git commit -m 'Add AmazingFeature'`)
4. **Push** to the branch (`git push origin feature/AmazingFeature`)
5. **Open** a Pull Request

Please follow [PEP 8](https://peps.python.org/pep-0008/) style and add comments for any new physics.

---

## 👨‍💻 Author

**Muhammad Hassan**

- 🎓 Deep Learning Engineer & AI Researcher
- 🐙 GitHub: [@mhassan-278](https://github.com/mhassan-278)
- 💼 LinkedIn: [muhammad-hassan-ai](https://www.linkedin.com/in/muhammad-hassan-ai)
- 📍 Pakistan

---

## 📚 References

- Misner, Thorne & Wheeler, *Gravitation* (1973) — Ch. 25 on Schwarzschild geodesics
- [Luminet (1979)](https://ui.adsabs.harvard.edu/abs/1979A%26A....75..228L) — the original black hole ray-tracing paper
- [Riazuelo (2018)](https://arxiv.org/abs/1805.09483) — modern ray-traced black hole visualizations
- [James et al. (2015)](https://arxiv.org/abs/1502.03809) — the *Interstellar* Gargantua paper (Kip Thorne's team)

---

## 🙏 Acknowledgements

Built with:

- [**Pygame**](https://www.pygame.org/) — window, input, OpenGL context
- [**PyOpenGL**](https://pyopengl.sourceforge.net/) — OpenGL bindings
- [**NumPy**](https://numpy.org/) — vertex buffer data

Inspired by the visual style of *Interstellar* (2014) and *Event Horizon* (1997).

---

## 📄 License

Released under the **MIT License** — see [LICENSE](LICENSE) for details.

You're free to use, modify, and distribute this code for personal or commercial projects.

---

<p align="center">
  <b>Made with ❤️ and a lot of physics by <a href="https://github.com/mhassan-278">Muhammad Hassan</a></b>
</p>

<p align="center">
  <i>"We used to look up at the sky and wonder at our place in the stars.<br>
  Now we just look down and worry about our place in the dirt."</i><br>
  <b>— Interstellar (2014)</b>
</p>

<p align="center">
  <a href="#top">⬆️ Back to top</a>
</p>
