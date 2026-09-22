import numpy as np
import scipy.signal as signal
import librosa

def wav_to_jon_current(wav_path, sim_dt=0.1, duration_ms=2000):
    """
    Converts a .wav audio file into a 0-30 nA current envelope 
    to stimulate JON (Johnston's Organ) auditory sensory neurons.
    """
    # 1. Target sample rate matching the simulation timestep (10 kHz for dt=0.1ms)
    target_sr = int(1000 / sim_dt)
    
    # Load audio file and resample to mono 10 kHz
    y, sr = librosa.load(wav_path, sr=target_sr, mono=True)
    
    # 2. Pad or truncate audio array to match duration_ms
    target_samples = int((duration_ms / 1000.0) * target_sr)
    if len(y) > target_samples:
        y = y[:target_samples]
    else:
        y = np.pad(y, (0, target_samples - len(y)))
        
    # 3. Extract Hilbert analytic signal envelope (simulates ear mechanical deflection)
    analytic_signal = signal.hilbert(y)
    envelope = np.abs(analytic_signal)
    
    # 4. Scale envelope amplitude into standard driving current (0 to 30 nA)
    max_val = np.max(envelope)
    if max_val > 0:
        envelope = (envelope / max_val) * 30.0
        
    return envelope