// Phase 2 diagnostic - I2C SCANNER + WHO_AM_I reader
//
// This is the sketch that cracked the "Failed to find MPU6050 chip!" problem.
// It does two things, in order:
//   1) Walks every 7-bit I2C address (0x08..0x77) and reports which ones ACK -
//      i.e. which devices are physically present and wired correctly.
//   2) For anything found at 0x68/0x69 (the MPU-6050 address pair), reads the
//      WHO_AM_I register (0x75) and prints it.
//
// Why this matters: a genuine MPU-6050 returns 0x68 in WHO_AM_I. Our module ACKs
// at address 0x68 (so wiring is fine) but WHO_AM_I comes back 0x72 - it's a clone
// (MPU-6500/9250 family). That mismatch is exactly why Adafruit_MPU6050 refuses
// the chip while MPU6050_light accepts it. See DECISIONS.md (2026-07-14).
//
// Pure Wire.h - no sensor library - so it can't be fooled by a library's own
// device check. If you ever get a "chip not found" error, run THIS first to
// separate "not wired" from "wired but not the chip the driver expected".
//
// Output: human-readable text (not the CSV contract - this is a scope, not data).

#include <Wire.h>

// Read one 8-bit register from an I2C device. Returns false if the device didn't
// respond to the read (NACK / no bytes returned).
bool readRegister(uint8_t addr, uint8_t reg, uint8_t &value) {
  Wire.beginTransmission(addr);
  Wire.write(reg);
  if (Wire.endTransmission(false) != 0) return false;  // repeated start; keep bus
  if (Wire.requestFrom((int)addr, 1) != 1) return false;
  value = Wire.read();
  return true;
}

void setup() {
  Serial.begin(115200);
  while (!Serial);  // BENCH-TEST ONLY - see the milestone sketch's note
  Wire.begin();
  Wire.setClock(400000);

  Serial.println("I2C scan starting...");
  uint8_t found = 0;

  for (uint8_t addr = 0x08; addr <= 0x77; addr++) {
    Wire.beginTransmission(addr);
    if (Wire.endTransmission() == 0) {  // 0 => device ACKed
      found++;
      Serial.print("  device found at 0x");
      Serial.println(addr, HEX);

      // If it's at an MPU-6050 address, interrogate WHO_AM_I to see what it
      // really is - the whole point of this diagnostic.
      if (addr == 0x68 || addr == 0x69) {
        uint8_t who = 0;
        if (readRegister(addr, 0x75, who)) {
          Serial.print("    WHO_AM_I (0x75) = 0x");
          Serial.print(who, HEX);
          if (who == 0x68)      Serial.println("  -> genuine MPU-6050");
          else if (who == 0x70) Serial.println("  -> MPU-6500 clone");
          else if (who == 0x71) Serial.println("  -> MPU-9250 clone");
          else if (who == 0x72) Serial.println("  -> clone (MPU-6500/9250 family) - use MPU6050_light");
          else                  Serial.println("  -> unknown / other clone");
        } else {
          Serial.println("    WHO_AM_I read failed");
        }
      }
    }
  }

  if (found == 0) {
    Serial.println("  no I2C devices found - check wiring, power, and pull-ups");
  }
  Serial.println("scan complete.");
}

void loop() {
  // one-shot; nothing to do
}
