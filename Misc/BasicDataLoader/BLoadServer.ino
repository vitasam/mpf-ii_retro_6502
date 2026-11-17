/*
 * MPF-II BASIC Data Loader, proof-of-concept
 */
#include <stdint.h>
#include <Wire.h>
#include <Adafruit_GFX.h>     // https://github.com/adafruit/Adafruit-GFX-Library
#include <Adafruit_SH1106.h>  // https://github.com/wonho-maker/Adafruit_SH1106

#define SERIAL_IN_USE

#define OLED_RESET_PIN        4

#define LEFT_UP_KEY_PIN       9   // INPUT_PULLUP
#define ENTER_KEY_PIN         8   // INPUT_PULLUP
#define RIGHT_DOWN_KEY_PIN    7   // INPUT_PULLUP
#define BUSY_PIN              6   // OUTPUT
#define STROBE_PIN            5   // INPUT

#define MAX_DATA_BLOCK_SIZE 32
struct DataBlock {
  uint16_t addressToLoad;
  uint16_t dataSizeToLoad;
  uint8_t dataBuf[MAX_DATA_BLOCK_SIZE];
};

const char ver[] = {"v.1.20"};

const uint8_t helloWorld[] = {
    0xA2, 0x00, 0xBD, 0x11, 0x04, 0xC9, 0xFF, 0xD0,
    0x01, 0x60, 0x20, 0xED, 0xFD, 0xE8, 0x4C, 0x02,
    0x04, 0xC8, 0xC5, 0xCC, 0xCC, 0xCF, 0xA0, 0xD7,
    0xCF, 0xD2, 0xCC, 0xC4, 0x8D, 0xFF, 0xFF, 0x00
};

Adafruit_SH1106 disp(OLED_RESET_PIN);
DataBlock data;
uint8_t *dataPtr = reinterpret_cast<uint8_t *>(&data);
int bitCount = 7;
uint8_t dataByte = 0;
int dataBit = 0;
int strobeZeroToOneCounter = 0;
int bytesCounter = 0;
volatile int strobeSignal = 0;
volatile int prevStrobeSignal = 0;

inline uint16_t swap_uint16(uint16_t val) {
  return (((val & 0x00FF) << 8) | ((val & 0xFF00) >> 8));
}

void swap_endiannes(uint8_t *buf, int buf_size) {
  uint16_t *p = (uint16_t *)buf;
  for (int i = 0; i < buf_size / 2; i++) {
    uint16_t temp = *p;
    *p = swap_uint16(temp);
    p++;
  }
}

void initHW() {
  pinMode(BUSY_PIN, OUTPUT);
  pinMode(STROBE_PIN, INPUT);
  pinMode(LEFT_UP_KEY_PIN, INPUT_PULLUP);
  pinMode(ENTER_KEY_PIN, INPUT_PULLUP);
  pinMode(RIGHT_DOWN_KEY_PIN, INPUT_PULLUP);
}

void splashScreen() {
  disp.clearDisplay();
  disp.setTextSize(1);
  disp.setTextColor(WHITE);
  disp.setCursor(0, 0);
  disp.print(F("BLoader Server,"));
  disp.println(ver);
}

void showStrobe(int val) {
  disp.setCursor(0, 9);
  disp.print(F("STROBE:"));
  disp.println(val);
}

void showByte(int val) {
  disp.setCursor(0, 18);
  disp.print(F("BYTE:0x"));
  disp.println(val, HEX);
}

void showBusy(int val) {
  disp.setCursor(0, 26);
  disp.print(F("BUSY:"));
  disp.println(val);
}

void showBitsSent(int val) {
  disp.setCursor(0, 34);
  disp.print(F("Bits sent:"));
  disp.println(val);
}

void showBytesSent(int val) {
  disp.setCursor(0, 42);
  disp.print(F("Bytes sent:"));
  disp.println(val);
}

void setup() {
  initHW();
  digitalWrite(BUSY_PIN, LOW);

#ifdef SERIAL_IN_USE
  Serial.begin(115200);

  if ((sizeof(DataBlock) % 2) != 0) {
    Serial.print(F("sizeof(DataBlock) should be even!"));
    while (1);
  }

  Serial.print(F("BLoader server test,"));
  Serial.println(ver);
#endif
  
  disp.begin(SH1106_SWITCHCAPVCC, 0x3C);
  splashScreen();
  disp.print(F("Press ENT to stream"));
  disp.display();
  while (digitalRead(ENTER_KEY_PIN) == HIGH);
  disp.clearDisplay();
  disp.display();
  memset(dataPtr, 0, sizeof(data));

  data.addressToLoad = 0x400;
  int sizeOfHelloWorld = (int)sizeof(helloWorld);
  data.dataSizeToLoad = sizeOfHelloWorld;
  memcpy(&data.dataBuf, helloWorld, sizeOfHelloWorld);
 
#ifdef SERIAL_IN_USE  
  Serial.print(F("data.addressToLoad: "));
  Serial.println(data.addressToLoad);
  Serial.print(F("data.dataSizeToLoad: "));
  Serial.println(data.dataSizeToLoad);
  Serial.print(F("data.dataBuf[0]: 0x"));
  Serial.println(data.dataBuf[0], HEX);
  Serial.print(F("data.dataBuf[7]: 0x"));
  Serial.println(data.dataBuf[7], HEX);
#endif

  // Convert the header to big endian
  swap_endiannes(dataPtr, sizeof(uint16_t) * 2);
  dataByte = *dataPtr;
}

void loop() {
  strobeSignal = digitalRead(STROBE_PIN);    
  if (strobeSignal > 0 && prevStrobeSignal == 0) {
    if (bitCount == 7) {
      dataByte = *dataPtr;
      dataPtr++;
      bytesCounter++;
    }

    dataBit = ((dataByte >> bitCount) & 0x01);
    digitalWrite(BUSY_PIN, dataBit);
    bitCount--;

    if (bitCount < 0) {
      bitCount = 7;
    }

#ifdef SERIAL_IN_USE
    Serial.print("#");
    Serial.print(strobeZeroToOneCounter);
    Serial.print(F(",bit:"));
    Serial.println(dataBit);
#endif
    strobeZeroToOneCounter++;
  }

  prevStrobeSignal = strobeSignal;
  showStrobe(strobeSignal);
  showByte(dataByte);
  showBusy(dataBit);
  showBitsSent(strobeZeroToOneCounter);
  showBytesSent(bytesCounter);
  disp.display();
  disp.clearDisplay();
}
