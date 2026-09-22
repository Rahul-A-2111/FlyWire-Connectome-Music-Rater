# Fly-Delity

A connectome-based music rating application that evaluates audio using a simplified *Drosophila* auditory circuit and Leaky Integrate-and-Fire (LIF) simulation.

The default Courtship mode favors approximately 140 BPM, a 180 Hz peak frequency, harmonic audio, and stable pulse timing.

## Project Layout

- `app.py`: Flask web application and upload endpoint.
- `judge_engine.py`: Feature extraction, LIF evaluation, mode scoring, and verdict generation.
- `audio_utils.py`: Audio-to-current conversion plus IPI, HNR, and tempo analysis.
- `cave.py`: FlyWire data loading, signed connectivity construction, and sparse LIF network.
- `jon_synapses.csv`: Cached FlyWire synapse data.
- `neuron_annotations.csv`: Cached neuron annotations.
- `static/`: Frontend assets.
- `uploads/`: Uploaded tracks.

## Environment Setup

The project uses the virtual environment located at:

```text
C:\Users\rahul_o2332zg\flywire_env
```

From PowerShell in this project directory:

```powershell
..\flywire_env\Scripts\Activate.ps1
```

If the environment has not been installed yet:

```powershell
python -m pip install flask flask-cors caveclient librosa numpy scipy soundfile pandas
```

Verify the important dependency:

```powershell
python -c "import caveclient; print(caveclient.__version__)"
```

In VS Code, select:

```text
C:\Users\rahul_o2332zg\flywire_env\Scripts\python.exe
```

## Run the Web App

```powershell
python app.py
```

Open the local URL printed by Flask, then upload an MP3 or WAV file. Available modes are:

- Courtship
- Territorial
- Quiet / Sleep

## Evaluation Behavior

- Expensive HNR and dynamic-tempo analysis is limited to the first 30 seconds.
- Track normalization and spectral analysis are also limited to 30 seconds.
- The connectome simulation evaluates three strategic two-second clips.
- Sparse connectivity is retained during recurrent LIF updates instead of converting the matrix to dense form.
- If P1/pIP10 neurons are unmapped or produce no spikes, the mating score falls back to the BPM match. AMMC is used as a proxy when available.
- Empty or malformed audio files return a structured `BAD` result instead of terminating the evaluator.


