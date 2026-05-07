import wave
import struct
import math
import os

def generate_stairs(path):
    sample_rate = 44100
    duration = 0.2
    num_samples = int(duration * sample_rate)
    volume = 0.3
    
    with wave.open(path, "w") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        
        for i in range(num_samples):
            t = i / sample_rate
            # Double click-like sound
            # First hit at t=0, second at t=0.1
            if 0 <= t < 0.05:
                local_t = t
                f = 800 * math.exp(-local_t * 100) # Fast pitch drop
                envelope = math.exp(-local_t * 100)
                value = math.sin(2 * math.pi * f * t)
            elif 0.1 <= t < 0.15:
                local_t = t - 0.1
                f = 600 * math.exp(-local_t * 100) # Slightly lower second hit
                envelope = math.exp(-local_t * 100)
                value = math.sin(2 * math.pi * f * t)
            else:
                value = 0
                
            sample = int(value * volume * 32767)
            wav_file.writeframesraw(struct.pack("<h", sample))

output_path = "components/sounds/sfx/stairs.wav"
os.makedirs(os.path.dirname(output_path), exist_ok=True)
generate_stairs(output_path)
print(f"Generated {output_path}")
