12 pad capactitive touch "DJ Board" with CircuitPython
Demo:

Build Video:

More Tutorials: https://YouTube.com/@BuildWithProfG

Components:
- Raspberry Pi Pico 2 (I used a 2w, which is the board for my class. Not tested on original Pico, which is less powerful)
- Adafruit Adalogger Cowbell (provides STEMMA-QT port & microSD card) - I recommend pre-soldered version, otherwise get the headers & prepare for soldering - https://www.adafruit.com/product/6355
- microSD card (don't use one greater than 32GB)
- Adafruit MPR121 12 pad gator capacitive touch STEMMA-QT board - https://learn.adafruit.com/adafruit-mpr121-gator
  STEMMA-QT cable - any should do to connect sensor to Cowbell - https://www.adafruit.com/product/4210
- Adafruit PCM5102 I2S DAC with Line Level Output - 112dB SNR https://www.adafruit.com/product/6250

If you have a standard speaker with its own power source & standard line-out audio plug, you should be able to plug it directly into the jack in the DAC board, above. This will give you better sound.
So that all my students have speaker components, we use very low-cost (and lower-quality sound) components in class:
- Mono Enclosed Speaker - 3W 4 Ohm - https://www.adafruit.com/product/3351
- Adafruit STEMMA Audio Amp - Mono 2.5W Class D - PAM8302 - Adafruit STEMMA Audio Amp - Mono 2.5W Class D - PAM8302
- Connect amp to breadboard - JST SH Compatible 1mm Pitch 3 Pin to Premium Male Headers Cable - 100mm long - https://www.adafruit.com/product/5755

Wiring diagram if you use the speaker setup above, otherwise eliminate the speaker & amp and plug your speaker into the jack in the DAC board
