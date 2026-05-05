import wave
import struct
import math

sample_rate = 24000
duration = 8.0 # 8 seconds of ringing

with wave.open("ringing.wav", "w") as f:
    f.setnchannels(1)
    f.setsampwidth(2)
    f.setframerate(sample_rate)
    
    # UK ring: 400Hz + 450Hz, 0.4s on, 0.2s off, 0.4s on, 2.0s off
    for i in range(int(sample_rate * duration)):
        t = i / sample_rate
        cycle_t = t % 3.0
        if cycle_t < 0.4 or (0.6 <= cycle_t < 1.0):
            val = math.sin(2 * math.pi * 400 * t) + math.sin(2 * math.pi * 450 * t)
            val = val * 0.15 * 32767
        else:
            val = 0
        f.writeframesraw(struct.pack("<h", int(val)))
