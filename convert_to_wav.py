import os
import librosa
import soundfile as sf

input_dir = r"C:\Users\rahul_o2332zg\flywire_env\songs"   # Folder containing your MP3s
output_dir = r"C:\Users\rahul_o2332zg\flywire_env\dataset\wav songs"

os.makedirs(output_dir, exist_ok=True)

if os.path.exists(input_dir):
    for file in os.listdir(input_dir):
        if file.lower().endswith((".mp3", ".m4a", ".flac", ".aac")):
            input_path = os.path.join(input_dir, file)
            base_name = os.path.splitext(file)[0]
            output_path = os.path.join(output_dir, f"{base_name}.wav")
            
            print(f"Converting: {file} -> {base_name}.wav")
            
            # Load audio file (resampled to 16 kHz, mono)
            y, sr = librosa.load(input_path, sr=16000, mono=True)
            
            # Export to 16-bit PCM WAV format
            sf.write(output_path, y, sr, subtype='PCM_16')

    print("All conversions complete!")
else:
    print(f"Folder '{input_dir}' not found. Please create it and add your audio files.")