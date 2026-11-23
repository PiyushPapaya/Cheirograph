/*
 * HID spike (WP-34): NUS UART and a BLE HID keyboard on one link.
 * Sends a dummy 80-byte frame at 50 Hz (valid checksum, mask 0x7F) and types
 * 'a' every 2 s. Tests whether Windows pairs it as a keyboard while Web
 * Bluetooth still reads the UART. NOT flashed yet.
 */
#include <bluefruit.h>

BLEUart bleuart;
BLEHidAdafruit blehid;

void setup(){
  Serial.begin(115200);
  Bluefruit.begin();                       // S1: one peripheral link. S2: Bluefruit.begin(2, 0)
  Bluefruit.setTxPower(4);
  Bluefruit.setName("HandRig-HID-spike");
  Bluefruit.Security.setIOCaps(false, false, false);   // Just Works pairing; HID needs an encrypted link
  bleuart.begin();
  blehid.begin();                          // both services exist before advertising starts

  Bluefruit.Advertising.addFlags(BLE_GAP_ADV_FLAGS_LE_ONLY_GENERAL_DISC_MODE);
  Bluefruit.Advertising.addAppearance(BLE_APPEARANCE_HID_KEYBOARD);
  Bluefruit.Advertising.addService(blehid);          // HID UUID in the advert (the OS looks for it)
  Bluefruit.ScanResponse.addService(bleuart);        // NUS UUID and name in the scan response
  Bluefruit.ScanResponse.addName();
  Bluefruit.Advertising.restartOnDisconnect(true);
  Bluefruit.Advertising.start(0);
}

void loop(){
  static uint32_t nextFrame = 0, nextKey = 0;
  static uint8_t seq = 0;
  uint32_t now = millis();

  if((int32_t)(now - nextFrame) >= 0){
    nextFrame = now + 20;
    uint8_t buf[80] = {0};
    buf[0] = 0xAB; buf[1] = seq++;
    memcpy(buf + 2, &now, 4);
    buf[6] = 0x7F;
    uint8_t ck = 0; for(uint8_t i = 0; i < 79; i++) ck ^= buf[i];
    buf[79] = ck;
    if(Bluefruit.connected() && bleuart.notifyEnabled()) bleuart.write(buf, sizeof(buf));
  }
  if((int32_t)(now - nextKey) >= 0){
    nextKey = now + 2000;
    if(Bluefruit.connected()){ blehid.keyPress('a'); delay(10); blehid.keyRelease(); }
  }
  delay(2);
}
