<div align="center">

![FlyWire Music Rater banner](static/readme_banner.svg)

# 🪰 FlyWire Music Rater

**A fruit fly brain, simulated from real wiring data, decides whether your music is a masterpiece or a swatter-worthy disaster.**

[![Connectome](https://img.shields.io/badge/Connectome-FlyWire%20FAFB-0284c7?style=for-the-badge)](https://flywire.ai/)
[![Model](https://img.shields.io/badge/Model-Leaky%20Integrate--and--Fire-2563eb?style=for-the-badge)](#-how-it-works)
[![Auditory](https://img.shields.io/badge/Auditory-Johnston's%20Organ-0284c7?style=for-the-badge)](#-how-it-works)
[![Escape](https://img.shields.io/badge/Panic-LC4%20Giant%20Fiber-dc2626?style=for-the-badge)](#-how-it-works)
[![Python](https://img.shields.io/badge/Python-3.10%2B-ffffff?style=for-the-badge&labelColor=1e293b&color=dc2626)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-Web%20App-ffffff?style=for-the-badge&labelColor=0f172a&color=2563eb)](https://flask.palletsprojects.com/)

</div>

---

## Contents

- [Overview](#-overview)
- [Behavioral Modes](#-behavioral-modes)
- [Features](#-features)
- [Verdicts](#-verdicts)
- [How It Works](#-how-it-works)
- [Project Structure](#-project-structure)
- [Setup](#-setup)
- [Usage](#-usage)
- [Troubleshooting](#-troubleshooting)
- [Credits](#-credits)

---

## 📖 Overview

FlyWire Music Rater simulates how a fruit fly (*Drosophila melanogaster*) hears and reacts to a song. It uses real synaptic wiring from the [FlyWire Connectome Project](https://flywire.ai/) and a Leaky Integrate-and-Fire (LIF) network. The whole thing is presented as a 1930s rubber hose cartoon, hosted by the gentleman critic **Lord Drosophila, Esq.**

Fruit flies communicate through wing vibrations called courtship songs, and sense them with **Johnston's Organ** in their antennae. This app converts your audio into synaptic current, streams it through the simulated neurons in real time, and reads out how the fly's brain responds: romance, aggression, calm, or full escape panic.

---

## 🎨 Behavioral Modes

The same song is judged differently depending on the fly's mindset.

| Mode | Accent | What the fly wants | Circuits involved |
| :--- | :---: | :--- | :--- |
| ♫ **Courtship** | 🔵 Blue | Steady pulses around 120–160 BPM and hums near 180 Hz | P1 / pIP10 wing-extension command neurons |
| ⚡ **Territorial** | 🔴 Red | Heavy transients, fast tempo, percussive force | Fight-or-flight thoracic motor units |
| ☾ **Quiet / Sleep** | ⚪ White | Low volume, gentle harmonics, ambient drift | Sudden loud sound triggers waking panic |

> [!IMPORTANT]
> The mode selector locks once a scan begins, so the network state cannot be changed mid-simulation.

---

## ⚡ Features

### 🎛️ One unified typebar
- Upload and online search share a single pill-shaped console.
- **Upload mode:** drag and drop, or click, to add `.mp3`, `.wav` or `.m4a`.
- **Search mode:** type an artist or song, for example *Daft Punk* or *Queen*.
- Quick demo buttons (*Daft Punk*, *Discordant Screech*) and suggestion chips (*Cab Calloway*, *Duke Ellington*, *Miles Davis*, *Queen*).

### 🌐 Online search and preview
- Searches the public **iTunes Search API**, so no API key is needed.
- Audition any 30-second preview with the built-in vintage player.
- **AUDIT ➔** downloads the clip, converts it to 16 kHz mono WAV with FFmpeg, and streams it into the simulator.

### 🎬 Theatrical reaction sequence
- Live mechanoreceptor scan while the simulation runs.
- **SEE RESULTS** closes the popup, centers the film reel, and plays the reaction cartoon (`fly_good.mp4` or `fly_bad.mp4`) with sound.
- The 5-gauge scorecard slides up when the clip ends, or immediately via **SKIP TO REPORT ➔**.

### 🏆 Live leaderboard ("Hall of Acclaim")
- New audits appear instantly, with no page refresh.
- Your latest track gets a gold glow and a **★ JUST AUDITED** badge.
- **★ VIEW ON LEADERBOARD ➔** jumps to your entry.
- Filters:

| Filter | Shows |
| :--- | :--- |
| ★ All-Time Affinity | Scores of 75 and above |
| ♫ Courtship Harmonics | Tracks rated in Courtship mode |
| ⚡ Johnston's Vibration | Tracks rated in Territorial mode |
| ☾ Nocturnal Slumber | Tracks rated in Sleep mode |
| ⚠ Dreadful Swatter Triggers | Scores below 55 |
| 🕒 Recent Audits | Latest entries first |

---

## 🏅 Verdicts

Every audit gets a rank badge, a headline and a piece of 1930s-style commentary. There are 15 verdicts in total: 3 modes × 5 tiers.

| Score | Rank | Courtship 🔵 | Territorial 🔴 | Quiet / Sleep ⚪ |
| :---: | :---: | :--- | :--- | :--- |
| **85–100** | **S+** | **True Romantic Sync**: single wing extended at 180 Hz | **Apex Warrior Shock**: the banana throne is yours | **Velvet Lullaby**: sweet dreams in the sugar dish |
| **70–84.9** | **A** | **Enchanted Flutter**: polite abdominal waggle granted | **Aggressive Spar**: rivals retreat in respect | **Gentle Slumber**: dorsal vessel pulses rhythmically |
| **50–69.9** | **B** | **Lukewarm Hover**: a tipsy gentleman in a speakeasy | **Mild Skirmish**: neither fruit won nor honor lost | **Restless Twitch**: light slumber disturbed |
| **30–49.9** | **C** | **Discordant Rejection**: antenna grooming in horror | **Territory Surrendered**: chased off the fruit platter | **Rude Awakening**: a groggy fall from the hammock |
| **0–29.9** | **F** | **Swatter Divorce**: bring the swatter | **Routed Retreat**: Giant Fiber panic, straight into a wall | **Nightmare Siren**: launched out of the hammock |

> [!CAUTION]
> Harsh, erratic noise over-stimulates the Giant Fiber interneurons. If the **Swatter Threat** gauge passes **50%**, the fly panics, rejects the track, and plays `fly_bad.mp4`.

---

## 🔬 How It Works

```text
   Audio file (.mp3 / .wav / .m4a)
                │   FFmpeg → 16 kHz mono WAV
                ▼
   Audio → synaptic current
   (spectrum, pulse timing / IPI, tempo)
                │
                ▼
   Johnston's Organ mechanoreceptors
     ├─ JO-A/B : frequency-sensitive (about 120–250 Hz)
     └─ JO-C/E : low-frequency / transient vibration
                │
                ▼
   Leaky Integrate-and-Fire network (FlyWire synapses)
     ├─ Signed synapses (excitatory / inhibitory)
     ├─ P1, pIP10       : courtship command neurons
     └─ LC4, Giant Fiber: escape neurons
                │
                ▼
   5 telemetry gauges → score → mode-specific verdict
```

| # | Gauge | Meaning |
| :-: | :--- | :--- |
| 1 | 🔵 **JO-AB Resonance** | Percent harmonic lock in the auditory neurons |
| 2 | 🔵 **Courtship Pulse** | Percent wing-extension sync |
| 3 | 🔴 **Flight Motor Stim.** | Percent thoracic vibration burst |
| 4 | 🔴 **Swatter Threat** | Percent LC4 / Giant Fiber escape trigger |
| 5 | ⚪ **Dopamine Surge** | Mushroom body reward multiplier |

---

## 📂 Project Structure

```text
flywire-song-project/
├── app.py                  # Flask app, SSE streaming pipeline, search & leaderboard APIs
├── judge_engine.py         # Connectome scoring, 3 modes, 15 verdicts
├── audio_utils.py          # Audio-to-current conversion, IPI pulse sync, tempo analysis
├── cave.py                 # FlyWire synapse matrices and LIF simulator
├── leaderboard.json        # Persistent leaderboard storage
├── jon_synapses.csv        # Cached FlyWire synapse data
├── neuron_annotations.csv  # Cached FlyWire cell-type annotations
├── static/
│   ├── readme_banner.svg   # README banner
│   ├── fly_hero.png        # Idle Lord Drosophila portrait
│   ├── fly_good.mp4        # Reaction: fly grooving on tempo
│   ├── fly_bad.mp4         # Reaction: fly in agony
│   ├── daft_demo.wav       # Clean 128 BPM electronic preset
│   └── screech_demo.wav    # Harsh discordant preset
└── uploads/                # Temporary audio buffer
```

---

## 🚀 Setup

### Prerequisites
- **Python 3.10+**
- **FFmpeg** on your system `PATH` (used for audio conversion)

### Install

```bash
git clone https://github.com/Rahul-A-2111/FlyWire-Connectome-Music-Rater.git
cd FlyWire-Connectome-Music-Rater

python -m venv venv
# Windows (PowerShell): .\venv\Scripts\Activate.ps1
# macOS / Linux:        source venv/bin/activate

python -m pip install flask flask-cors caveclient librosa numpy scipy soundfile pandas
```

Verify the key dependencies:

```bash
ffmpeg -version
python -c "import caveclient, librosa; print('ok')"
```

> [!NOTE]
> Synapse and annotation data are cached in `jon_synapses.csv` and `neuron_annotations.csv`. Configure CAVEclient credentials only if you want to re-pull data from FlyWire.

---

## 🎮 Usage

```bash
python app.py
```

Then open <http://localhost:5000>.

1. **Choose a mode:** Courtship, Territorial, or Quiet / Sleep.
2. **Pick music:** drop a file on the typebar, use a quick demo, or click **🌐 Search Archives Online** and type an artist or track.
3. **Watch the scan:** the mechanoreceptor simulation runs live.
4. **Click SEE RESULTS ➔:** the reaction cartoon plays, then the scorecard slides up.
5. **Check the leaderboard:** click **★ VIEW ON LEADERBOARD ➔**, or click any archived entry to audition another track.

---

## 🩺 Troubleshooting

| Problem | Likely fix |
| :--- | :--- |
| Upload or online audit fails at conversion | Confirm `ffmpeg` runs in the same terminal that launches `app.py` |
| `ModuleNotFoundError` | Activate your virtual environment, then re-run the `pip install` line |
| Port 5000 already in use | Stop the other process, or change the port in `app.py` |
| Online search returns nothing | Check your internet connection; the iTunes Search API needs no key |
| Reaction video silent | Browsers may block autoplay audio until you click; use the SEE RESULTS button |

---

## 🙏 Credits

- [FlyWire Connectome Project](https://flywire.ai/) for the *Drosophila* brain wiring data
- [CAVEclient](https://github.com/CAVEconnectome/CAVEclient) for data access
- [iTunes Search API](https://developer.apple.com/library/archive/documentation/AudioVideo/Conceptual/iTuneSearchAPI/) for song search and previews

<div align="center">

**Drosophila Biosonic Sound Laboratories • Circa 1934**
*Certified by Lord Drosophila, Esq. // 139,255 Synapses Audited*

</div>
