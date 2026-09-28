// Phase 0 — XIAO nRF52840 Sense LED sanity test
//
// Purpose: the very first "is this board alive and can I flash it?" check.
// Cycles the onboard RGB user-LED through red -> green -> blue, 500 ms each.
// If you see this cycle, the toolchain, USB, bootloader, and MCU are all good.
//
// Board: Seeed XIAO nRF52840 Sense (Arduino IDE, "Seeed nRF52 Boards" package)
//
// GOTCHA — the RGB LED is ACTIVE-LOW:
//   digitalWrite(pin, LOW)  = LED segment ON
//   digitalWrite(pin, HIGH) = LED segment OFF
// This trips everyone once. The pins LED_RED / LED_GREEN / LED_BLUE are
// predefined by the Seeed board package, so you don't need the raw P0.xx numbers.

void setup() {
  pinMode(LED_RED, OUTPUT);
  pinMode(LED_GREEN, OUTPUT);
  pinMode(LED_BLUE, OUTPUT);
}

void loop() {
  // Red (active-LOW: LOW = on, HIGH = off)
  digitalWrite(LED_RED, LOW);
  digitalWrite(LED_GREEN, HIGH);
  digitalWrite(LED_BLUE, HIGH);
  delay(500);

  // Green
  digitalWrite(LED_RED, HIGH);
  digitalWrite(LED_GREEN, LOW);
  digitalWrite(LED_BLUE, HIGH);
  delay(500);

  // Blue
  digitalWrite(LED_RED, HIGH);
  digitalWrite(LED_GREEN, HIGH);
  digitalWrite(LED_BLUE, LOW);
  delay(500);
}
