# Fly-Delity: 1930s Rubber Hose Noir Connectome Music Rater

A connectome-based music rating application that evaluates audio using a simplified *Drosophila melanogaster* auditory circuit and Leaky Integrate-and-Fire (LIF) simulation, wrapped in an authentic 1930s Rubber Hose Noir aesthetic.

The application evaluates songs through simulated Johnston's Organ mechanoreceptors, measuring acoustic resonance, pulse timing (IPI), harmonicity (HNR), and downstream activations across courtship (P1/pIP10), territorial, and threat/escape (LC4/Giant Fiber) neural pathways.

---

## Key Features

- **Connectome Hall of Acclaim (Real-Time Leaderboard System)**:
  - Persistent server-backed leaderboard (`leaderboard.json`) tracking audited specimens.
  - **Instant Real-Time Sync**: Audited tracks are immediately logged in memory and synced to the backend without requiring a page refresh.
  - **Visual Audit Highlights**: Newly audited tracks are styled with a shimmering gold border and an animated `★ JUST AUDITED` badge.
  - **Live Dispatch Feed**: An automatic synapse feed banner (`⚡ LIVE AUDIT LOG // REAL-TIME DISPATCH`) dynamically displays the latest audited tracks across categories.
  - Category filtration tabs:
    - `All Categories`: Comprehensive chronological audit register with live dispatch.
    - `★ All-Time Affinity`: High-scoring auditory masterpieces ($\ge 75$).
    - `♫ Courtship Harmonics`: Songs evaluated under Courtship mode.
    - `⚡ Johnston's Vibration`: Songs evaluated under Territorial mode.
    - `☾ Nocturnal Slumber`: Songs evaluated under Quiet / Sleep mode.
    - `⚠ Dreadful Swatter Triggers`: Low-scoring or chaotic din inducing LC4 escape panic ($< 55$).
    - `🕒 Recent Audits`: Quick chronological filter for the latest specimens.
  - Interactive entries: Click any ledger item to instantly queue and re-audit it in the screening booth.
  - Direct ledger shortcut: A dedicated `★ VIEW ON LEADERBOARD ➔` button on the final scorecard smoothly scrolls down to inspect your track's ledger entry.

- **Online Song Lookup & Instant Preview Auditing**:
  - Global music archive search powered by the public iTunes Search API.
  - No API key required; search any artist, jazz standard, classical composition, or contemporary track.
  - In-browser 30-second audio preview player (`▶ Preview`) to audition before rating.
  - 1-Click connectome evaluation: Automatically downloads, converts to 16 kHz mono WAV via FFmpeg, and streams through the neural simulator.

- **15 Customized Verdicts (3 Modes $\times$ 5 Score Tiers)**:
  - Custom rank badges, verdict headlines, and vintage critic commentary from *Lord Drosophila, Esq.*:
    - **Courtship Mode**: From *True Romantic Sync* (180 Hz wing extension) down to *Swatter Divorce* (courtship paralysis).
    - **Territorial Mode**: From *Apex Warrior Thorax Shock* (dominion over the banana throne) down to *Routed Retreat* (Giant Fiber panic).
    - **Quiet / Sleep Mode**: From *Velvet Lullaby* (circadian tranquility) down to *Nightmare Siren* (violent awakening).
  - Score Tiers:
    - Tier 1: 85.0 – 100.0 (Rank S+)
    - Tier 2: 70.0 – 84.9 (Rank A)
    - Tier 3: 50.0 – 69.9 (Rank B)
    - Tier 4: 30.0 – 49.9 (Rank C)
    - Tier 5: 0.0 – 29.9 (Rank F)

- **Mode Locking During Bio-Scan**:
  - Behavioral mode selection is automatically locked and disabled during audio evaluation with a visual warning badge to prevent state corruption during active neural simulation.

- **1930s Film Screening Experience & Video Synchronization**:
  - Authentic 1930s film grain vignette, projector flicker, and rubber hose bobbing animations.
  - **Front-and-Center Video Playback**: Clicking **SEE RESULTS** dismisses the preliminary popup and centers the film viewport into direct sight.
  - **Full Reel Theatrical Timing**: The custom MP4 reaction cartoon (`fly_good.mp4` / `fly_bad.mp4`) plays in its entirety. The comprehensive 5-gauge scorecard **only slides up after the video clip ends**, preserving the comedic punchline.
  - **Scrubber & Skip Control**: Features an optical soundtrack progress bar, live timecode, and a `SKIP TO REPORT ➔` button for immediate report access when desired.
  - Fallback animated silent reel with projector flicker if MP4 decoding is unsupported in the client browser.

---

## Project Layout

- `app.py`: Flask web application, SSE streaming pipeline, search endpoints, and leaderboard handlers.
- `judge_engine.py`: Audio feature extraction, LIF connectome simulation, 3-mode scoring, and 15-tier verdict generator.
- `audio_utils.py`: Audio-to-current conversion (JON-A/B vs JON-C/E channels), IPI sync, HNR, and dynamic tempo analysis.
- `cave.py`: FlyWire data loading, signed synaptic connectivity matrix, and sparse LIF network.
- `leaderboard.json`: Persistent ledger database storing archived and user-audited tracks.
- `jon_synapses.csv`: Cached FlyWire synapse dataset.
- `neuron_annotations.csv`: Cached neuron cell-type annotations.
- `static/`: Frontend visual and audio assets (`fly_hero.png`, `fly_good.mp4`, `fly_bad.mp4`, `daft_demo.wav`, `screech_demo.wav`).
- `uploads/`: Temporary audio buffer for uploaded or online-fetched tracks.

---

## Environment Setup

The project uses the virtual environment located at:

```text
C:\Users\rahul_o2332zg\flywire_env
```

Activate in PowerShell:

```powershell
..\flywire_env\Scripts\Activate.ps1
```

If dependencies need to be installed:

```powershell
python -m pip install flask flask-cors caveclient librosa numpy scipy soundfile pandas
```

Verify CAVEclient:

```powershell
python -c "import caveclient; print(caveclient.__version__)"
```

Ensure FFmpeg is available on your system PATH for audio conversion.

---

## Run the Web Application

```powershell
python app.py
```

Open the local server URL (e.g. `http://localhost:5000`):
1. Choose a behavioral mode: **Courtship**, **Territorial**, or **Quiet / Sleep**.
2. Select your audio via **Local File Upload** (`.mp3`, `.wav`, `.m4a`), **Online Song Search**, or **Quick Demos**.
3. Watch the real-time connectome mechanoreceptor scan and click **SEE RESULTS** to enter the screening booth.
4. Watch the full synchronized 1930s reaction cartoon (`fly_good.mp4` / `fly_bad.mp4`), after which your 5-gauge neural scorecard automatically slides up (or click `SKIP TO REPORT ➔`).
5. Review your critic commentary and click `★ VIEW ON LEADERBOARD ➔` to see your track instantly registered and highlighted in real-time in the **Connectome Hall of Acclaim**.
