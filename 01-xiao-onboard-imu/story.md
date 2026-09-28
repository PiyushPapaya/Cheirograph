# Story — the reference sensor

Same session as the LED test, second half. Once the board was proven alive, I moved straight to the onboard IMU, since it's the one sensor every other measurement in this project ultimately gets compared against.

This one went smoothly, mostly because I'd already read the datasheet closely enough to know the address is `0x6A`, not the `0x68` I'd been expecting from the MPU-6050 modules sitting on my desk. If I hadn't caught that ahead of time, I probably would have burned twenty minutes assuming the sensor was dead.

Got clean accel and gyro values streaming to serial pretty quickly after that. Tilted the board around, watched the numbers respond the way gravity says they should. Nothing dramatic here — which, for a "does this chip work" test, is exactly the outcome you want. The interesting problems were still ahead of me.
