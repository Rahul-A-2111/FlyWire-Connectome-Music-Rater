import os
import numpy as np
import soundfile as sf
import librosa

from cave import FlyAuditoryNetwork, adj_matrix
from audio_utils import wav_to_jon_current

sim = FlyAuditoryNetwork(adj_matrix)

def evaluate_song_with_fly(file_path, progress_callback=None):
    def notify(data):
        if progress_callback:
            progress_callback(data)

    notify({"stage": "⚡ Initializing Fly-Delity Bio-Acoustic Scanner..."})

    # Load Audio File
    clean_wav_path = file_path
    if not file_path.lower().endswith('.wav'):
        notify({"stage": "🎵 Converting audio format to 16 kHz Mono WAV..."})
        from pydub import AudioSegment
        clean_wav_path = file_path.rsplit('.', 1)[0] + "_temp_converted.wav"
        sound = AudioSegment.from_file(file_path)
        sound = sound.set_channels(1).set_frame_rate(16000)
        sound.export(clean_wav_path, format="wav")

    temp_clips = []
    try:
        notify({"stage": "🔍 Extracting Track BPM & Frequency Spectrum..."})
        y, sr = librosa.load(clean_wav_path, sr=16000, mono=True)
        
        # 1. Detect BPM and Peak Frequency
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
        bpm = float(np.round(tempo[0] if isinstance(tempo, np.ndarray) else tempo, 1))
        
        spec = np.abs(np.fft.rfft(y[:sr*5]))
        freqs = np.fft.rfftfreq(sr*5, 1/sr)
        peak_freq = int(freqs[np.argmax(spec)])

        # 2. Slice into 12 Clips for sequential simulation
        clip_duration = 2.0
        samples_per_clip = int(clip_duration * sr)
        total_clips = int(len(y) // samples_per_clip)

        if total_clips == 0:
            return {"result": "BAD", "score": 0.0, "message": "Song is too short!"}

        num_clips = min(total_clips, 12)
        clip_indices = np.linspace(0, total_clips - 1, num_clips, dtype=int)

        firing_rates = []
        variances = []

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

                # Connectome LIF Simulation
                stimulus = wav_to_jon_current(temp_clip_path, sim_dt=0.1, duration_ms=2000)
                spikes = sim.run_simulation(stimulus, dt=0.1)

                firing_rates.append(spikes.mean() * 1000.0)
                variances.append(spikes.sum(axis=1).var())

        notify({"stage": "📊 Computing Courtship Pulse & Dopamine Surge Scores..."})

        # Biological Preference Calculations:
        # Ideal Drosophila Courtship BPM ~ 120 - 160 BPM
        bpm_match = max(0, 100 - abs(bpm - 140) * 0.8)
        
        # Ideal Antenna Resonance ~ 140 - 220 Hz
        freq_match = max(0, 100 - abs(peak_freq - 180) * 0.3)
        
        # Neural Spike Dynamic Score
        avg_firing = np.mean(firing_rates) if firing_rates else 0
        avg_var = np.mean(variances) if variances else 0
        neural_score = min(100, (avg_firing * 8.0) + (avg_var * 0.5))

        # Overall Connectome Affinity (Weighted 0 to 100)
        overall_score = round((bpm_match * 0.35) + (freq_match * 0.25) + (neural_score * 0.40), 1)

        # Metrics for dashboard display
        threat_coefficient = round(min(1.0, max(0.02, (100 - freq_match) / 100)), 2)
        dopamine_surge = round(min(99, max(10, overall_score * 0.98)), 1)
        courtship_sync = round(min(99, max(5, bpm_match)), 1)
        flight_motor_activation = round(min(98, max(8, neural_score * 0.92)), 1)

        THRESHOLD = 65.0
        is_good = overall_score >= THRESHOLD

        return {
            "result": "GOOD" if is_good else "BAD",
            "score": overall_score,
            "threshold": THRESHOLD,
            "bpm": bpm,
            "peak_freq": peak_freq,
            "courtship_sync": courtship_sync,
            "dopamine_surge": dopamine_surge,
            "threat_coefficient": threat_coefficient,
            "flight_motor": flight_motor_activation
        }

    finally:
        if clean_wav_path != file_path and os.path.exists(clean_wav_path):
            try: os.remove(clean_wav_path)
            except Exception: pass
        for clip in temp_clips:
            if os.path.exists(clip):
                try: os.remove(clip)
                except Exception: pass