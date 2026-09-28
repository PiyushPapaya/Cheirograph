# Story - the sensor that wasn't what it claimed to be

This was the first real debugging session of the project, and it taught me something I'd end up relearning at a bigger scale later: never trust a part's label, check the chip itself.

I wired up one MPU-6050 breakout directly to the XIAO, four wires plus the address pin, and reached for the most obvious library, Adafruit's MPU6050 driver, because it's well documented and I'd used Adafruit libraries before without issues. It refused to even start. Just printed "Failed to find MPU6050 chip!" and halted.

My first instinct was to assume I'd wired something wrong. So I ran an I²C bus scanner to check, and it clearly found a device sitting at address `0x68`, exactly where it should be. That ruled out wiring. The chip was there, responding, but the library still refused to talk to it.

That's when I stopped guessing and went to the actual register. The `WHO_AM_I` register is supposed to identify the chip, and a real MPU-6050 reports `0x68` there too. Mine reported `0x72`. That number belongs to the MPU-6500/9250 family, a different, similar chip that a lot of cheap "MPU-6050" boards actually ship with instead of the real thing. Adafruit's library checks that number strictly and bails if it doesn't match. Nothing was wrong with my wiring or my code. The part itself just wasn't what the listing said it was.

Switched to a different library, `MPU6050_light`, which doesn't gate on that identity check, and everything worked immediately. I made a mental note right there: since I ordered all five finger sensors in the same batch, they were probably all the same clone. That assumption turned out to matter a lot more later, once all five were wired up behind the mux and I had to root-cause a much stranger set of symptoms, worth remembering this was the first sign of it.
