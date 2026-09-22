import os
import soundfile as sf

# Updated input path based on your exact File Explorer path
input_dir = r"C:\Users\rahul_o2332zg\flywire_env\dataset\wav songs"

# Output directory for the 2-second sliced clips
output_dir = r"C:\Users\rahul_o2332zg\flywire_env\dataset\sliced_wav_songs"

clip_duration_sec = 2.0  # 2-second chunks

print(f"Checking input directory: {input_dir}")

if not os.path.exists(input_dir):
    print(f"ERROR: The folder '{input_dir}' does not exist!")
else:
    # Filter for files starting with or ending in .wav
    files = [f for f in os.listdir(input_dir) if ".wav" in f.lower()]
    print(f"Found {len(files)} WAV file(s): {files}")

    if len(files) == 0:
        print("No .wav files found in directory!")
    else:
        os.makedirs(output_dir, exist_ok=True)
        total_clips_created = 0

        for file in files:
            file_path = os.path.join(input_dir, file)
            
            # Strip all .wav extensions to clean up base name
            base_name = file.lower().replace(".wav", "")

            # Read audio file metadata
            info = sf.info(file_path)
            sr = info.samplerate
            channels = info.channels
            samples_per_clip = int(clip_duration_sec * sr)

            print(f"\nProcessing '{file}' ({info.duration:.1f} seconds, {sr} Hz)...")

            clip_idx = 1
            with sf.SoundFile(file_path) as f:
                while True:
                    data = f.read(samples_per_clip)
                    if len(data) < samples_per_clip:
                        break  # Stop when remaining audio is less than 2 seconds

                    # Convert to mono if stereo
                    if channels > 1:
                        data = data.mean(axis=1)

                    output_filename = f"{base_name}_clip_{clip_idx:03d}.wav"
                    output_path = os.path.join(output_dir, output_filename)

                    sf.write(output_path, data, sr, subtype='PCM_16')
                    clip_idx += 1
                    total_clips_created += 1

            print(f"Created {clip_idx - 1} clips for '{file}'.")

        print(f"\nSUCCESS: Created {total_clips_created} total 2-second clips in '{output_dir}'.")