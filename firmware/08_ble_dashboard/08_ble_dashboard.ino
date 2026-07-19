/*
 * HandRig BLE v3 — 6-IMU live streamer with clone-robust finger init
 * Seeed XIAO nRF52840 SENSE
 *
 *   sensor 0    = onboard LSM6DS3TR-C (hand / palm reference)  @ 0x6A
 *   sensor 1..5 = finger IMUs via PCA9548A mux ch 0..4        @ 0x68
 *
 * WHY v3:
 *   The finger modules are clones reporting WHO_AM_I=0x72 (MPU-6500/9250
 *   family). MPU6050_light talks to them but never does a proper
 *   reset/wake/enable-axes sequence, so several boot half-asleep and return
 *   FIXED register patterns (the "stuck 0x3F00" and "±0x2000 ramp" garbage).
 *
 *   So we DROP MPU6050_light for the fingers and drive them by raw I2C:
 *     - explicit DEVICE_RESET -> wake -> enable all axes -> DLPF -> FS config
 *     - burst-read 0x3B..0x48 and scale with the known sensitivities
 *   The accel/gyro register map is identical across MPU-6050/6500/9250, so
 *   this works whether a channel holds a genuine 0x68 or a 0x72 clone.
 *
 *   Boot prints a per-channel diagnostic: WHO_AM_I + a liveness check
 *   (|a| magnitude and whether the data actually moves). Watch Serial once
 *   after flashing.
 *
 * Frame (79 B): [0xAB][seq][t_ms u32][mask][6*(int16 ax ay az gx gy gz)] LE
 *   accel int16 = g*8192   gyro int16 = dps*65.536   (±4 g / ±500 dps)
 *
 * 3.3 V ONLY.
 */

#include <bluefruit.h>
#include <Wire.h>
#include <LSM6DS3.h>
#include <math.h>

// ---------------- config ----------------
#define TCA_ADDR   0x70
#define MPU_ADDR   0x68
#define SAMPLE_MS  20
#define DEV_NAME   "HandRig-6IMU"
#define ACC_SCALE  8192.0f     // ±4 g  -> 8192 LSB/g
#define GYR_SCALE  65.536f     // ±500 dps -> 65.536 LSB/(°/s)
#define I2C_HZ     400000      // drop to 100000 if a channel is flaky
// ----------------------------------------

// MPU register map (shared 6050 / 6500 / 9250)
#define R_SMPLRT   0x19
#define R_CONFIG   0x1A
#define R_GYRO_CFG 0x1B
#define R_ACC_CFG  0x1C
#define R_ACCEL    0x3B
#define R_PWR1     0x6B
#define R_PWR2     0x6C
#define R_WHOAMI   0x75

const uint8_t NUM_FING = 5;
const uint8_t CH[NUM_FING] = {0, 1, 2, 3, 4};

LSM6DS3 mcuIMU(I2C_MODE, 0x6A);

bool     present[6] = {false};
uint8_t  whoami[6]  = {0};
BLEUart  bleuart;
uint8_t  seq = 0;
uint32_t accReadUs = 0, accWriteUs = 0; uint16_t accN = 0;

// ---- mux ----
void tcaSelect(uint8_t ch){ Wire.beginTransmission(TCA_ADDR); Wire.write(1<<ch); Wire.endTransmission(); }
void tcaDisable()         { Wire.beginTransmission(TCA_ADDR); Wire.write(0x00);  Wire.endTransmission(); }

// ---- raw I2C helpers (device = MPU_ADDR on the currently selected channel) ----
bool wReg(uint8_t reg, uint8_t val){
  Wire.beginTransmission(MPU_ADDR); Wire.write(reg); Wire.write(val);
  return Wire.endTransmission() == 0;
}
uint8_t rReg(uint8_t reg, bool* ok=nullptr){
  Wire.beginTransmission(MPU_ADDR); Wire.write(reg);
  if(Wire.endTransmission(false)!=0){ if(ok)*ok=false; return 0; }
  if(Wire.requestFrom((int)MPU_ADDR,1)!=1){ if(ok)*ok=false; return 0; }
  if(ok)*ok=true; return Wire.read();
}
bool rBurst(uint8_t reg, uint8_t* buf, uint8_t n){
  Wire.beginTransmission(MPU_ADDR); Wire.write(reg);
  if(Wire.endTransmission(false)!=0) return false;
  if(Wire.requestFrom((int)MPU_ADDR,(int)n)!=n) return false;
  for(uint8_t i=0;i<n;i++) buf[i]=Wire.read();
  return true;
}

// ---- explicit clone-robust init on the given mux channel ----
bool initFinger(uint8_t ch){
  tcaSelect(ch);
  bool ack=false; uint8_t who=rReg(R_WHOAMI,&ack);
  whoami[ch+1]=who;
  if(!ack) return false;                 // nothing ACKing at 0x68 on this channel

  wReg(R_PWR1, 0x80); delay(100);        // DEVICE_RESET
  tcaSelect(ch);
  wReg(R_PWR1, 0x01); delay(10);         // wake, clock = PLL(gyro X)
  wReg(R_PWR2, 0x00);                    // enable all accel+gyro axes  <-- key for clones
  wReg(R_CONFIG,  0x03);                 // DLPF ~44 Hz
  wReg(R_SMPLRT,  0x04);                 // 1kHz/(1+4) = 200 Hz
  wReg(R_GYRO_CFG,0x08);                 // FS_SEL=1  -> ±500 dps
  wReg(R_ACC_CFG, 0x08);                 // AFS_SEL=1 -> ±4 g
  delay(20);
  return true;
}

// ---- read one finger (raw registers -> g / dps) ----
void readFinger(uint8_t ch, float a[3], float g[3]){
  tcaSelect(ch);
  uint8_t b[14];
  if(!rBurst(R_ACCEL,b,14)){ a[0]=a[1]=a[2]=g[0]=g[1]=g[2]=0; return; }
  int16_t ax=(b[0]<<8)|b[1],  ay=(b[2]<<8)|b[3],  az=(b[4]<<8)|b[5];
  int16_t gx=(b[8]<<8)|b[9],  gy=(b[10]<<8)|b[11],gz=(b[12]<<8)|b[13];
  a[0]=ax/ACC_SCALE; a[1]=ay/ACC_SCALE; a[2]=az/ACC_SCALE;
  g[0]=gx/GYR_SCALE; g[1]=gy/GYR_SCALE; g[2]=gz/GYR_SCALE;
}

void readSensor(uint8_t sid, float a[3], float g[3]){
  if(sid==0){
    tcaDisable();
    a[0]=mcuIMU.readFloatAccelX(); a[1]=mcuIMU.readFloatAccelY(); a[2]=mcuIMU.readFloatAccelZ();
    g[0]=mcuIMU.readFloatGyroX();  g[1]=mcuIMU.readFloatGyroY();  g[2]=mcuIMU.readFloatGyroZ();
  } else {
    readFinger(CH[sid-1], a, g);
  }
}

// ---- boot liveness check: is the channel actually sampling? ----
void livenessCheck(uint8_t sid){
  float a[3], g[3];
  float amin[3]={9,9,9}, amax[3]={-9,-9,-9}, amagSum=0;
  const uint8_t N=10;
  for(uint8_t i=0;i<N;i++){
    readSensor(sid,a,g);
    for(uint8_t k=0;k<3;k++){ if(a[k]<amin[k])amin[k]=a[k]; if(a[k]>amax[k])amax[k]=a[k]; }
    amagSum += sqrtf(a[0]*a[0]+a[1]*a[1]+a[2]*a[2]);
    delay(20);
  }
  float amag=amagSum/N;
  float rng=0; for(uint8_t k=0;k<3;k++){ float r=amax[k]-amin[k]; if(r>rng)rng=r; }
  bool magOK  = (amag>0.7f && amag<1.3f);
  bool moves  = (rng>0.002f);              // real sensor always dithers >= a few LSB
  Serial.print("#   sid "); Serial.print(sid);
  if(sid>0){ Serial.print(" who=0x"); Serial.print(whoami[sid],HEX); }
  Serial.print(" |a|="); Serial.print(amag,2);
  Serial.print("g accel_range="); Serial.print(rng,3);
  if(!magOK)      Serial.println("  -> BAD (|a| not ~1g: stuck/asleep/dead)");
  else if(!moves) Serial.println("  -> SUSPECT (bit-identical: no live sampling)");
  else            Serial.println("  -> OK");
}

inline void putI16(uint8_t* p, float v, float scale){
  long q=lroundf(v*scale); if(q>32767)q=32767; if(q<-32768)q=-32768;
  int16_t s=(int16_t)q; p[0]=s&0xFF; p[1]=(s>>8)&0xFF;
}

void sendFrame(){
  uint8_t buf[79];
  buf[0]=0xAB; buf[1]=seq++;
  uint32_t t=millis(); buf[2]=t&0xFF; buf[3]=(t>>8)&0xFF; buf[4]=(t>>16)&0xFF; buf[5]=(t>>24)&0xFF;
  uint32_t r0=micros();
  uint8_t mask=0, idx=7; float a[3], g[3];
  for(uint8_t sid=0;sid<6;sid++){
    if(present[sid]){ readSensor(sid,a,g); mask|=(1<<sid); }
    else { a[0]=a[1]=a[2]=0; g[0]=g[1]=g[2]=0; }
    putI16(&buf[idx],a[0],ACC_SCALE);idx+=2; putI16(&buf[idx],a[1],ACC_SCALE);idx+=2;
    putI16(&buf[idx],a[2],ACC_SCALE);idx+=2; putI16(&buf[idx],g[0],GYR_SCALE);idx+=2;
    putI16(&buf[idx],g[1],GYR_SCALE);idx+=2; putI16(&buf[idx],g[2],GYR_SCALE);idx+=2;
  }
  buf[6]=mask;
  uint32_t r1=micros();
  if(Bluefruit.connected()) bleuart.write(buf,sizeof(buf));
  uint32_t r2=micros();
  accReadUs+=(r1-r0); accWriteUs+=(r2-r1); accN++;
}

void startAdv(){
  Bluefruit.Advertising.addFlags(BLE_GAP_ADV_FLAGS_LE_ONLY_GENERAL_DISC_MODE);
  Bluefruit.Advertising.addTxPower();
  Bluefruit.Advertising.addService(bleuart);
  Bluefruit.Advertising.addName();
  Bluefruit.Advertising.restartOnDisconnect(true);
  Bluefruit.Advertising.setInterval(32,244);
  Bluefruit.Advertising.setFastTimeout(30);
  Bluefruit.Advertising.start(0);
}

void setup(){
  Serial.begin(115200);
  uint32_t t0=millis(); while(!Serial && millis()-t0<1800){}

  Wire.begin(); Wire.setClock(I2C_HZ);
#ifdef PIN_LSM6DS3TR_C_POWER
  pinMode(PIN_LSM6DS3TR_C_POWER,OUTPUT); digitalWrite(PIN_LSM6DS3TR_C_POWER,HIGH); delay(5);
#endif

  // hand
  tcaDisable();
  mcuIMU.settings.gyroRange=500; mcuIMU.settings.accelRange=4;
  present[0]=(mcuIMU.begin()==0);

  // fingers
  for(uint8_t i=0;i<NUM_FING;i++) present[i+1]=initFinger(CH[i]);

  Serial.println("# ---- boot diagnostic ----");
  for(uint8_t sid=0;sid<6;sid++){
    if(present[sid]) livenessCheck(sid);
    else { Serial.print("#   sid "); Serial.print(sid); Serial.println(" NOT FOUND (no ACK)"); }
  }
  Serial.println("# note: fingers should read WHO=0x68 (genuine) or 0x72 (clone), both OK.");
  Serial.println("# -------------------------");

  Bluefruit.begin(); Bluefruit.setTxPower(4); Bluefruit.setName(DEV_NAME);
  Bluefruit.Periph.setConnInterval(6,12);
  bleuart.begin(); startAdv();
  Serial.print("# advertising as "); Serial.println(DEV_NAME);
}

void loop(){
  static uint32_t next=0,rptT=0,frames=0;
  if(next==0){ next=millis(); rptT=millis(); }
  if((int32_t)(millis()-next)<0) return;
  next+=SAMPLE_MS;
  sendFrame(); frames++;
  uint32_t now=millis();
  if(now-rptT>=2000){
    Serial.print("# link="); Serial.print(Bluefruit.connected()?"up":"down");
    Serial.print(" hz="); Serial.print(frames*1000.0f/(now-rptT),1);
    Serial.print(" read_us="); Serial.print(accN?accReadUs/accN:0);
    Serial.print(" write_us="); Serial.println(accN?accWriteUs/accN:0);
    frames=0; rptT=now; accReadUs=accWriteUs=0; accN=0;
  }
}
