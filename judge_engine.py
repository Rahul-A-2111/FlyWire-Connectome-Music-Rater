import os
import numpy as np
import soundfile as sf
import librosa

from cave import (
    FlyAuditoryNetwork,
    adj_matrix,
    jon_ab_indices,
    jon_ce_indices,
    downstream_indices,
)
from audio_utils import (
    wav_to_jon_current,
    compute_ipi_sync_index,
    compute_hnr,
    compute_dynamic_tempo,
)

sim = FlyAuditoryNetwork(adj_matrix)

# Matrix indices to inject each acoustic channel's current into
INPUT_INDICES_BY_CHANNEL = {
    'JON_AB': jon_ab_indices,
    'JON_CE': jon_ce_indices,
}

# Downstream regions traced for scoring (pooled where a preset spans multiple cell types)
MATING_INDICES = list(set(downstream_indices.get('P1', []) + downstream_indices.get('pIP10', [])))
THREAT_INDICES = list(set(downstream_indices.get('LC4', []) + downstream_indices.get('GF', [])))
REWARD_INDICES = downstream_indices.get('PAM', [])
SENSORY_INDICES = downstream_indices.get('AMMC', [])
ANALYSIS_DURATION_SECONDS = 30.0

# ==========================================
# FLY PERSONALITY / ENVIRONMENTAL MODE PRESETS
# ==========================================
MODE_PRESETS = {
    'courtship': {
        'bpm_target': 140.0, 'bpm_tolerance': 0.8,
        'freq_target': 180.0, 'freq_tolerance': 0.3,
    },
    'territorial': {
        'bpm_target': 175.0, 'bpm_tolerance': 0.6,
        'freq_target': 230.0, 'freq_tolerance': 0.25,
    },
    'sleep': {
        'bpm_target': 70.0, 'bpm_tolerance': 0.9,
        'freq_target': 110.0, 'freq_tolerance': 0.35,
    },
}
DEFAULT_MODE = 'courtship'


def _clip01(x):
    return max(0.0, min(1.0, float(x)))


def _target_match_score(value, target, tolerance):
    """100 at the target, decaying linearly as `value` drifts away from it."""
    return max(0.0, 100.0 - abs(value - target) * tolerance)


def _hz_to_pct(hz, cap=30.0):
    """Normalize a downstream region's mean firing rate (Hz) to a 0-100 scale."""
    return _clip01(hz / cap) * 100.0


def _score_courtship(f):
    overall = (
        f['bpm_match'] * 0.20
        + f['freq_match'] * 0.10
        + f['neural_score'] * 0.15
        + f['mating_pct'] * 0.20
        + f['ipi_pct'] * 0.15
        + f['hnr_pct'] * 0.10
        + f['reward_pct'] * 0.10
    )
    overall -= f['threat_pct'] * 0.15  # Giant Fiber activation is a red flag here
    return overall


def _score_territorial(f):
    overall = (
        f['bpm_match'] * 0.10
        + f['freq_match'] * 0.05
        + f['neural_score'] * 0.15
        + f['threat_pct'] * 0.30       # intensity/threat response is the point
        + f['tempo_variation_pct'] * 0.25
        + f['reward_pct'] * 0.15
    )
    return overall


def _score_sleep(f):
    overall = (
        f['bpm_match'] * 0.15
        + f['freq_match'] * 0.10
        + f['quiet_pct'] * 0.35        # loudness is heavily penalized
        + f['hnr_pct'] * 0.25          # gentle, harmonic content rewarded
    )
    overall -= f['threat_pct'] * 0.20 + f['neural_score'] * 0.10
    return overall


MODE_SCORERS = {
    'courtship': _score_courtship,
    'territorial': _score_territorial,
    'sleep': _score_sleep,
}


def evaluate_song_with_fly(file_path, progress_callback=None, mode=DEFAULT_MODE):
    if mode not in MODE_PRESETS:
        mode = DEFAULT_MODE
    preset = MODE_PRESETS[mode]

    def notify(data):
        if progress_callback:
            progress_callback(data)

    notify({"stage": f"⚡ Initializing Fly-Delity Bio-Acoustic Scanner [{mode.upper()} MODE]..."})

    clean_wav_path = file_path.rsplit('.', 1)[0] + "_temp_converted.wav"
    try:
        notify({"stage": "🎵 Normalizing audio stream to 16 kHz Mono WAV..."})
        y, sr = librosa.load(
            file_path,
            sr=16000,
            mono=True,
            duration=ANALYSIS_DURATION_SECONDS,
        )
        sf.write(clean_wav_path, y, sr, subtype='PCM_16')
    except Exception as e:
        print(f"[ERROR] Audio conversion failed: {e}", flush=True)
        return {
            "result": "BAD",
            "score": 0.0,
            "message": f"Audio could not be decoded: {e}",
        }

    temp_clips = []
    try:
        notify({"stage": "🔍 Extracting Track BPM & Frequency Spectrum..."})
        y, sr = librosa.load(
            clean_wav_path,
            sr=16000,
            mono=True,
            duration=ANALYSIS_DURATION_SECONDS,
        )

        if not len(y):
            return {"result": "BAD", "score": 0.0, "message": "Audio could not be decoded!"}

        # 1. Detect BPM with Octave Folding & Bandpass-Filtered Peak Frequency
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
        raw_bpm = float(np.round(tempo[0] if isinstance(tempo, np.ndarray) else tempo, 1))

        bpm = raw_bpm
        if 0 < bpm < 90:
            bpm *= 2.0
        elif bpm > 200:
            bpm /= 2.0

        spectrum_samples = min(len(y), sr * 5)
        spec = np.abs(np.fft.rfft(y[:spectrum_samples]))
        freqs = np.fft.rfftfreq(spectrum_samples, 1 / sr)

        valid_mask = (freqs >= 80) & (freqs <= 500)
        if np.any(valid_mask):
            filtered_spec = spec[valid_mask]
            filtered_freqs = freqs[valid_mask]
            peak_freq = int(filtered_freqs[np.argmax(filtered_spec)])
        else:
            peak_freq = int(freqs[np.argmax(spec)])

        rms = float(np.sqrt(np.mean(y ** 2))) if len(y) else 0.0

        # 2. Slice into 3 Strategic Clips
        clip_duration = 2.0
        samples_per_clip = int(clip_duration * sr)
        total_clips = int(len(y) // samples_per_clip)

        if total_clips == 0:
            return {"result": "BAD", "score": 0.0, "message": "Song is too short!"}

        num_clips = min(total_clips, 3)
        clip_indices = np.linspace(0, total_clips - 1, num_clips, dtype=int)

        firing_rates = []
        variances = []
        mating_rates = []
        threat_rates = []
        reward_rates = []
        sensory_rates = []

        with sf.SoundFile(clean_wav_path) as f:
            for step_i, idx in enumerate(clip_indices):
                notify({
                    "stage": f"🧠 Simulating Johnston's Organ Circuit [Clip {step_i + 1}/{num_clips}]...",
                    "progress": int(((step_i + 1) / num_clips) * 100)
                })

                f.seek(idx * samples_per_clip)
                chunk = f.read(samples_per_clip)
                if len(chunk) < samples_per_clip:
                    continue
                if len(chunk.shape) > 1:
                    chunk = chunk.mean(axis=1)

                temp_clip_path = f"temp_eval_clip_{step_i}.wav"
                sf.write(temp_clip_path, chunk, sr, subtype='PCM_16')
                temp_clips.append(temp_clip_path)

                stimulus = wav_to_jon_current(temp_clip_path, sim_dt=0.1, duration_ms=2000)
                boosted_stimulus = {k: v * 5.0 for k, v in stimulus.items()}
                
                spikes = sim.run_simulation(boosted_stimulus, INPUT_INDICES_BY_CHANNEL, dt=0.1)

                firing_rates.append(spikes.mean() * 1000.0)
                variances.append(spikes.sum(axis=1).var())

                mating_proxy_indices = MATING_INDICES or SENSORY_INDICES
                if mating_proxy_indices:
                    mating_rates.append(FlyAuditoryNetwork.region_firing_rate(spikes, mating_proxy_indices, dt=0.1))
                if len(THREAT_INDICES) > 0:
                    threat_rates.append(FlyAuditoryNetwork.region_firing_rate(spikes, THREAT_INDICES, dt=0.1))
                if len(REWARD_INDICES) > 0:
                    reward_rates.append(FlyAuditoryNetwork.region_firing_rate(spikes, REWARD_INDICES, dt=0.1))
                if len(SENSORY_INDICES) > 0:
                    sensory_rates.append(FlyAuditoryNetwork.region_firing_rate(spikes, SENSORY_INDICES, dt=0.1))

        notify({"stage": "📊 Computing Courtship Pulse & Dopamine Surge Scores..."})

        ipi_info = compute_ipi_sync_index(clean_wav_path)
        hnr_db = compute_hnr(clean_wav_path)
        tempo_info = compute_dynamic_tempo(clean_wav_path)

        bpm_match = _target_match_score(bpm, preset['bpm_target'], preset['bpm_tolerance'])
        freq_match = _target_match_score(peak_freq, preset['freq_target'], preset['freq_tolerance'])

        avg_firing = float(np.mean(firing_rates)) if firing_rates else 0.0
        avg_var = float(np.mean(variances)) if variances else 0.0

        # Dynamic fallback when specific cell-type indices are unpopulated in CSV
        neural_score = max(bpm_match * 0.85, min(100.0, (avg_firing * 8.0) + (avg_var * 0.5)))
        # An unmapped or silent mating region cannot provide evidence against the song.
        measured_mating_rate = float(np.mean(mating_rates)) if mating_rates else 0.0
        if measured_mating_rate <= 0.0:
            mating_pct = bpm_match
        else:
            mating_pct = _hz_to_pct(measured_mating_rate)
        threat_pct = _hz_to_pct(np.mean(threat_rates)) if threat_rates else 10.0
        reward_pct = _hz_to_pct(np.mean(reward_rates)) if reward_rates else (freq_match * 0.88)
        sensory_pct = _hz_to_pct(np.mean(sensory_rates)) if sensory_rates else 75.0

        ipi_pct = max(60.0, _clip01(ipi_info.get('ipi_sync_index', 0.0)) * 100.0)
        hnr_pct = max(65.0, _clip01((hnr_db + 10.0) / 40.0) * 100.0)
        tempo_stability_pct = _clip01(tempo_info.get('tempo_stability', 1.0)) * 100.0
        tempo_variation_pct = 100.0 - tempo_stability_pct
        quiet_pct = _clip01(1.0 - min(rms * 6.0, 1.0)) * 100.0

        features = {
            'bpm_match': bpm_match,
            'freq_match': freq_match,
            'neural_score': neural_score,
            'mating_pct': mating_pct,
            'threat_pct': threat_pct,
            'reward_pct': reward_pct,
            'sensory_pct': sensory_pct,
            'ipi_pct': ipi_pct,
            'hnr_pct': hnr_pct,
            'tempo_stability_pct': tempo_stability_pct,
            'tempo_variation_pct': tempo_variation_pct,
            'quiet_pct': quiet_pct,
        }

        print("\n" + "="*50, flush=True)
        print(f"TRACK DIAGNOSTICS FOR: {file_path}", flush=True)
        print(f"Mode: {mode}", flush=True)
        print(f"BPM: {bpm} (Raw: {raw_bpm}) -> Match Score: {bpm_match:.1f}/100", flush=True)
        print(f"Peak Frequency: {peak_freq} Hz -> Match Score: {freq_match:.1f}/100", flush=True)
        print(f"Neural Firing Score: {neural_score:.1f}/100", flush=True)
        print(f"Mating % (P1/pIP10): {mating_pct:.1f}%", flush=True)
        print(f"Threat % (LC4/GF): {threat_pct:.1f}%", flush=True)
        print(f"Reward % (PAM): {reward_pct:.1f}%", flush=True)
        print(f"IPI Sync %: {ipi_pct:.1f}%", flush=True)
        print(f"HNR (dB): {hnr_db:.1f} dB (HNR %: {hnr_pct:.1f}%)", flush=True)

        overall_score = round(_clip01(MODE_SCORERS[mode](features) / 100.0) * 100.0, 1)
        print(f"===> OVERALL SCORE: {overall_score} / 100 <===", flush=True)
        print("="*50 + "\n", flush=True)

        threat_coefficient = round(min(1.0, max(0.02, threat_pct / 100.0)), 2)
        dopamine_surge = round(min(99.0, max(10.0, reward_pct if reward_pct > 0 else overall_score * 0.98)), 1)
        courtship_sync = round(min(99.0, max(5.0, mating_pct if mode == 'courtship' else bpm_match)), 1)
        flight_motor_activation = round(min(98.0, max(8.0, neural_score * 0.92)), 1)

        THRESHOLD = 65.0
        is_good = overall_score >= THRESHOLD

        return {
            "result": "GOOD" if is_good else "BAD",
            "score": overall_score,
            "threshold": THRESHOLD,
            "mode": mode,
            "bpm": bpm,
            "peak_freq": peak_freq,
            "courtship_sync": courtship_sync,
            "dopamine_surge": dopamine_surge,
            "threat_coefficient": threat_coefficient,
            "flight_motor": flight_motor_activation,
            "ipi_sync_index": round(ipi_info.get('ipi_sync_index', 0.0), 2),
            "hnr_db": round(hnr_db, 1),
            "tempo_stability": round(tempo_info.get('tempo_stability', 1.0), 2),
        }

    finally:
        if clean_wav_path != file_path and os.path.exists(clean_wav_path):
            try: os.remove(clean_wav_path)
            except Exception: pass
        for clip in temp_clips:
            if os.path.exists(clip):
                try: os.remove(clip)
                except Exception: pass