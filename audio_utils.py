import numpy as np
import scipy.signal as signal
import librosa


# ==========================================
# INTERNAL HELPERS
# ==========================================
def _load_and_frame(wav_path, sim_dt=0.1, duration_ms=2000):
    """Load audio, resample to the simulation's timestep rate, and pad/trim to duration_ms."""
    target_sr = int(1000 / sim_dt)
    y, sr = librosa.load(wav_path, sr=target_sr, mono=True)

    target_samples = int((duration_ms / 1000.0) * target_sr)
    if len(y) > target_samples:
        y = y[:target_samples]
    else:
        y = np.pad(y, (0, target_samples - len(y)))

    return y, target_sr


def _bandpass(y, sr, low_hz, high_hz, order=4):
    nyq = sr / 2.0
    low_n = max(low_hz / nyq, 1e-6)
    high_n = min(high_hz / nyq, 0.999)
    b, a = signal.butter(order, [low_n, high_n], btype='band')
    return signal.filtfilt(b, a, y)


def _lowpass(y, sr, cutoff_hz, order=4):
    nyq = sr / 2.0
    b, a = signal.butter(order, min(cutoff_hz / nyq, 0.999), btype='low')
    return signal.filtfilt(b, a, y)


def _envelope(y):
    analytic_signal = signal.hilbert(y)
    return np.abs(analytic_signal)


def _scale_to_current(envelope, max_current=30.0):
    max_val = np.max(envelope)
    if max_val > 0:
        envelope = (envelope / max_val) * max_current
    return envelope


# ==========================================
# 1. CIRCUIT-SPECIFIC CURRENT INJECTION (JON-A/B vs JON-C/E)
# ==========================================
def wav_to_jon_current(wav_path, sim_dt=0.1, duration_ms=2000):
    """
    Converts a .wav audio file into separate 0-30 nA driving-current
    envelopes for the two functionally distinct JON sub-populations:

      - JON_AB: near-field courtship/auditory channel. Tuned to subtle
        low-frequency particle velocity (100-250 Hz) -- pulse/sine song.
      - JON_CE: wind/gravity/threat channel. Tuned to steady low-frequency
        air-pressure cues plus high-intensity transient spikes (distortion,
        clipping, sudden volume jumps).

    Returns a dict: {'JON_AB': ndarray, 'JON_CE': ndarray, 'broadband': ndarray}
    The 'broadband' key is kept for backward compatibility with callers that
    expect a single undifferentiated envelope.
    """
    y, sr = _load_and_frame(wav_path, sim_dt, duration_ms)

    # --- JON-A/B: near-field courtship channel (100-250 Hz) ---
    y_ab = _bandpass(y, sr, 100, 250)
    env_ab = _scale_to_current(_envelope(y_ab))

    # --- JON-C/E: steady low-frequency wind/gravity cues (<80 Hz) ---
    y_ce_steady = _lowpass(y, sr, 80)
    env_ce_steady = _envelope(y_ce_steady)

    # --- JON-C/E: high-intensity transient spikes (onset strength) ---
    hop_length = max(1, int(sr * (sim_dt / 1000.0)))
    onset_env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop_length)
    onset_env = np.interp(
        np.linspace(0, len(onset_env) - 1, len(y)),
        np.arange(len(onset_env)),
        onset_env
    ) if len(onset_env) > 1 else np.zeros(len(y))

    env_ce = _scale_to_current(env_ce_steady + onset_env)

    # --- Legacy broadband envelope ---
    env_broadband = _scale_to_current(_envelope(y))

    return {
        'JON_AB': env_ab,
        'JON_CE': env_ce,
        'broadband': env_broadband,
    }


# ==========================================
# 2. INTER-PULSE INTERVAL (IPI) SYNCHRONIZATION
# ==========================================
def compute_ipi_sync_index(wav_path, target_ipi_ms=35.0, tolerance_ms=5.0):
    """
    Male fruit-fly courtship pulse song consists of discrete acoustic pulses
    separated by roughly 30-40 ms gaps. This detects pulse peaks in the
    envelope and scores how tightly the measured inter-pulse intervals
    cluster around that natural window.

    Returns dict: {'ipi_sync_index': 0-1 float, 'mean_ipi_ms': float|None,
                    'num_pulses': int}
    """
    y, sr = librosa.load(wav_path, sr=22050, mono=True)
    envelope = np.abs(signal.hilbert(y))

    if len(envelope) > 101:
        envelope = signal.savgol_filter(envelope, 101, 3)

    peak_indices, _ = signal.find_peaks(
        envelope,
        distance=int(sr * 0.02),
        prominence=max(np.max(envelope) * 0.05, 1e-6)
    )

    if len(peak_indices) < 2:
        return {'ipi_sync_index': 0.0, 'mean_ipi_ms': None, 'num_pulses': int(len(peak_indices))}

    peak_times_ms = (peak_indices / sr) * 1000.0
    ipis = np.diff(peak_times_ms)

    deviations = np.abs(ipis - target_ipi_ms)
    scores = np.clip(1.0 - (deviations / tolerance_ms), 0.0, 1.0)

    return {
        'ipi_sync_index': float(np.mean(scores)),
        'mean_ipi_ms': float(np.mean(ipis)),
        'num_pulses': int(len(peak_indices)),
    }


# ==========================================
# 3. HARMONICITY-TO-NOISE RATIO (HNR)
# ==========================================
def compute_hnr(wav_path):
    """
    Clean musical harmonies phase-lock JON-A responses; chaotic noise or
    harsh distortion degrades phase locking and biases the network toward
    threat channels. Returns the harmonic-to-noise ratio in dB (higher =
    cleaner/more harmonic).
    """
    y, sr = librosa.load(wav_path, sr=22050, mono=True)
    y_harmonic, _ = librosa.effects.hpss(y)

    harmonic_energy = float(np.sum(y_harmonic ** 2))
    noise_energy = float(np.sum((y - y_harmonic) ** 2)) + 1e-10

    if harmonic_energy <= 0:
        return -60.0

    return float(10 * np.log10(harmonic_energy / noise_energy))


# ==========================================
# 4. DYNAMIC TEMPO ENTRAINMENT
# ==========================================
def compute_dynamic_tempo(wav_path, frame_length_s=4.0, hop_s=2.0):
    """
    Tracks tempo across overlapping windows instead of relying on a single
    static BPM reading for the whole track, so smooth rhythmic transitions
    can be rewarded and jarring tempo jumps can be penalized.

    Returns dict: {'tempo_track': [(start_time_s, bpm), ...],
                    'tempo_stability': 0-1 float (1.0 = perfectly steady),
                    'duration_s': float}
    """
    y, sr = librosa.load(wav_path, sr=22050, mono=True)
    duration_s = len(y) / sr

    frame_samples = int(frame_length_s * sr)
    hop_samples = max(int(hop_s * sr), 1)

    tempo_track = []
    t = 0
    while t < len(y):
        chunk = y[t:t + frame_samples]
        if len(chunk) < sr:  # too short a tail to estimate reliably
            break
        onset_env = librosa.onset.onset_strength(y=chunk, sr=sr)
        tempo = librosa.feature.tempo(onset_envelope=onset_env, sr=sr)
        bpm = float(tempo[0]) if len(tempo) else 0.0
        tempo_track.append((t / sr, bpm))
        t += hop_samples

    bpms = [b for _, b in tempo_track if b > 0]
    if len(bpms) >= 2 and np.mean(bpms) > 0:
        tempo_stability = float(1.0 / (1.0 + (np.std(bpms) / np.mean(bpms))))
    else:
        tempo_stability = 1.0

    return {
        'tempo_track': tempo_track,
        'tempo_stability': tempo_stability,
        'duration_s': float(duration_s),
    }


# ==========================================
# 5. CONVENIENCE: FULL FEATURE BUNDLE
# ==========================================
def extract_full_feature_set(wav_path, sim_dt=0.1, duration_ms=2000):
    """
    One-stop call that gathers everything the judge engine needs: the
    per-channel driving currents plus the higher-level acoustic descriptors
    (IPI sync, HNR, dynamic tempo). Convenient for wiring into app.py /
    judge_engine.py without importing each function individually.
    """
    currents = wav_to_jon_current(wav_path, sim_dt=sim_dt, duration_ms=duration_ms)
    ipi = compute_ipi_sync_index(wav_path)
    hnr_db = compute_hnr(wav_path)
    tempo = compute_dynamic_tempo(wav_path)

    return {
        'currents': currents,
        'ipi': ipi,
        'hnr_db': hnr_db,
        'tempo': tempo,
    }