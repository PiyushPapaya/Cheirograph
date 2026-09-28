# Story — first light

This was the actual first session with the hardware, after everything arrived and got soldered. The question was simple: is the board even alive?

I plugged the XIAO into my laptop and it just... didn't show up. No COM port, nothing in the Arduino IDE's port list. My first thought was that I'd bought a dead board. Turns out that's a known thing with the nRF52840 — you have to double-tap the RESET button to force it into bootloader mode before it'll enumerate as programmable. Once I did that, the port appeared immediately and uploads worked fine. I'm writing this down mainly because I know I'll forget it and hit this exact confusion again in six months.

After that it was straightforward. Wrote the LED blink sketch, uploaded it, watched it cycle red, green, blue. Small win, but it confirmed the whole chain — USB, bootloader, board package, upload process — actually works. Everything after this session builds on that assumption being true.

One small thing I noted and almost missed: the LED is active-LOW, so `LOW` means "on." Wired my expectations backwards for about thirty seconds before I checked the datasheet.
