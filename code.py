# pico_dj_board_poly_with_DAC.py
# Problems usually occur if: you move very fast between multiple sounds.
# If you have board on a flat surface & contacts can touch
# Feel free to try more sounds.

import board, adafruit_mpr121, gc, time, audiobusio
import microcontroller, watchdog
from adafruit_debouncer import Button
from audiocore import WaveFile
from audiomixer import Mixer
import sdcardio, storage, busio

# Configure Audio
SD_CS        = board.GP17
SPEAKER_PIN  = board.GP14
PATH         = "/sd/128_bpm/"

# Make sure .wav files are saved 22050, 16 bit depth, mono
SAMPLE_RATE  = 22050
BIT_DEPTH    = 16
CHANNELS     = 1
NUM_VOICES   = 3 # simultaneous sound play
MIXER_BUFFER = 4096   # mixer's internal DMA buffer (bytes)
# Per-pad SD read buffer — max 1024
# WAVE_BUFFER_SIZE = 512
WAVE_BUFFER_SIZE = 1024

# DAC setup
audio = audiobusio.I2SOut(
   bit_clock=board.GP10,
   word_select=board.GP9,
   data=board.GP11
)

# Mixer setup
mixer = Mixer(
    voice_count=NUM_VOICES,
    sample_rate=SAMPLE_RATE,
    channel_count=CHANNELS,
    bits_per_sample=BIT_DEPTH,
    samples_signed=True,
    buffer_size=MIXER_BUFFER,
)
audio.play(mixer)

# All files in the 128_bpm folder. Modified from free downloads at: https://cymatics.fm/
# Descriptions are my own poor attempt
sounds = [
    "perc_loop_3_128bpm.wav",                        # fun starting drums with a bit of a slap every few beats
    "house_top_drum_loop_10_128bpm.wav",             # drum loop with some slap claps
    "full_drum_loop_128bpm.wav",                     # like a background under beat you'd hear on the dance floor
    "house_buildup_drums_1_128bpm.wav",              # great build up drums
    "drum_buildup_12_128bpm.wav",                    # another buildup
    "mirage_vocoder_loop_11_f_minor_128bpm.wav",     # almost vocal. High bopping tone
    "house_vocal_loop_2_f_minor_128bpm.wav",         # another almost vocal - lower tone. Bops
    "future_house_loop_4_128bpm.wav",                # boppy up and down
    "big_boom_loop_1_c_128bpm.wav",                  # laser zap followed by chirpy gallop, repeated.
    "prometheus_vocal_arp_15_a_minor_128bpm.wav",    # rapid, almost like alien musical chirps. arpeggiated with a warble
    "per_loop_16_128bpm.wav",                        # another slower but good start drum
    "drum_loop_3_128bpm.wav",                        # tick & slappy, but might be too similar to others
    # "full_drum_loop_2_128bpm.wav",                 # like cymbals & tick tock, but might not be enough to include
    # "full_drum_loop_20_128bpm.wav",                # an up and down, but similar to some of the others.
    # "drum_loop_18_128bpm.wav",                     # thumping with some faster woodpecker toward end of beats
    # "full_drum_loop_9_128bpm.wav",                 # maybe this blends in well with above?
    # "super_saw_loop_10_128bpm.wav",                # dramatic pulsing down and up
    # "super_saw_loop_36_128bpm.wav",                # rapid, almost sounds like an epic theme.
    # "soft_chord_loop_11_emaj_128bpm.wav",          # chirp single tones, almost like xylophones.
    # "tension_white_noise_down_7_128bpm.wav",       # this is that big zoop one note high down low
    # "tension_noise_drum_up_1_128bpm.wav"           # low to high one note zoop.
    # "prometheus_vocal_arp_10_e_minor_128bpm.wav",  # rapid, almost like a video game
    # "soft_chord_loop_1_cmin_128bpm.wav",           # sounds like Coldplay
    # "arp_loop_20_emin_128bpm.wav",                 # cool, but also not much for da club. Also a bit Coldplay
    # "arp_loop_1_cmaj_128bpm.wav"                   # crazy up and down. Not much fun for da club.
]

# microSD card setup - assumes Adalogger Cowbell
spi0   = busio.SPI(board.GP18, board.GP19, board.GP16)
# sdcard = sdcardio.SDCard(spi0, SD_CS)
sdcard = sdcardio.SDCard(spi0, SD_CS, baudrate=8_000_000)
vfs    = storage.VfsFat(sdcard)

try:
    storage.mount(vfs, "/sd")
    print("😎 SD card mounted")
except ValueError:
    print("❌ No SD card — halting")
    raise SystemExit

# Touchpad setup - adafruit MPR121 12 pad STEMMA-QT gator board
i2c       = board.STEMMA_I2C()
touch_pad = adafruit_mpr121.MPR121(i2c)
pads      = [Button(t, value_when_pressed=True) for t in touch_pad] # Debounced

NUM_PADS       = 12
pad_last_press = [0.0] * NUM_PADS
PAD_COOLDOWN   = 0.2   # seconds — prevents rapid-fire SPI bus hammering
# Global cooldown throttles rapid cross-pad tapping — the main crash trigger.
# PAD_COOLDOWN is per-pad, so hammering different pads in quick succession
# bypasses it entirely. This adds a board-wide minimum gap between any two
# start_sound() calls, giving the SPI bus time to finish each seek/WaveFile
# reconstruction before the next one begins. 50 ms is imperceptible to a
# human performer but enough to prevent SPI bus contention crashes.
last_any_press  = 0.0
GLOBAL_COOLDOWN = 0.05  # seconds — min gap between any two pad presses

# Pre-open WAV files at startup
# Each pad gets one permanent file handle, one permanent read buffer, and one
# WaveFile object — all allocated here, never again during playback.
print("Opening WAV files...")
wav_files   = []   # permanent open file handles
wav_buffers = []   # permanent pre-allocated read buffers
wavs        = []   # WaveFile objects, reconstructed on each press via seek(0)

for i in range(NUM_PADS):
    try:
        f   = open(PATH + sounds[i], "rb")
        buf = bytearray(WAVE_BUFFER_SIZE)
        wav = WaveFile(f, buf)
        wav_files.append(f)
        wav_buffers.append(buf)
        wavs.append(wav)
        print(f"  ✓ Pad {i}: {sounds[i]}")
    except OSError as e:
        wav_files.append(None)
        wav_buffers.append(None)
        wavs.append(None)
        print(f"  ✗ Pad {i}: {e}")

# gc = garbage collection, reclaims memory from objects no longer in use
gc.collect()
print(f"Ready. Free memory: {gc.mem_free()} bytes")

# Set up pool of voices
pad_voice  = [None] * NUM_PADS
voice_used = [False] * NUM_VOICES

def _free_voice():
    for v, in_use in enumerate(voice_used):
        if not in_use:
            return v
    return None

def stop_sound(pad_idx):
    v = pad_voice[pad_idx]
    if v is not None:
        mixer.voice[v].stop()
        # Block until DMA has truly finished — stop() is non-blocking.
        # Seeking the file while DMA is still reading corrupts the SPI bus.
        deadline = time.monotonic() + 0.2
        while mixer.voice[v].playing:
            if time.monotonic() > deadline:
                print(f"⚠️  DMA timeout voice {v}")
                break
        voice_used[v]      = False
        pad_voice[pad_idx] = None
        print(f"■ Pad {pad_idx} stopped")

def start_sound(pad_idx):
    global last_any_press
    if wav_files[pad_idx] is None:
        return
    now = time.monotonic()
    # Check global cooldown first — if any pad was just started, wait.
    if now - last_any_press < GLOBAL_COOLDOWN:
        return
    if now - pad_last_press[pad_idx] < PAD_COOLDOWN:
        return

    if pad_voice[pad_idx] is not None:
        stop_sound(pad_idx)

    v = _free_voice()
    if v is None:
        print(f"⚠️  All voices busy, skipping pad {pad_idx}")
        return

    # DMA is confirmed stopped — safe to seek and reconstruct WaveFile
    wav_files[pad_idx].seek(0)
    wavs[pad_idx] = WaveFile(wav_files[pad_idx], wav_buffers[pad_idx])

    mixer.voice[v].play(wavs[pad_idx], loop=True)
    pad_voice[pad_idx]      = v
    voice_used[v]           = True
    pad_last_press[pad_idx] = now
    last_any_press          = now   # update global timestamp on successful start
    print(f"▶ Pad {pad_idx} → voice {v}")

# Watchdog - will restart board in event of hang/crash
wd         = microcontroller.watchdog
wd.timeout = 2     # seconds — auto-restart if main loop freezes
wd.mode    = watchdog.WatchDogMode.RESET
print("🐕 Watchdog armed — auto-restart on freeze (2 s)")

print(f"🎛  DJ board ready — {NUM_VOICES} simultaneous voices")

while True:
    wd.feed() # Watchdog, checks board, restarts if frozen
    for i in range(NUM_PADS):
        pads[i].update()
        if pads[i].pressed:
            start_sound(i)
        elif pads[i].released:
            stop_sound(i)
