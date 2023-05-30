#include <MFRC522.h>
#include <SPI.h>

/*
  PINOUT for EPS D1 Mini

  RST  - WHITE  - D1
  SDA  - ORANGE - D2
  SCK  - YELLOW - D5
  MOSI - GREEN  - D7
  MISO - BROWN  - D6
*/
#define SDA_PIN D2
#define RST_PIN D1
 
// Instance of the class
MFRC522 rfid(SDA_PIN, RST_PIN);
MFRC522::MIFARE_Key key; 

void setup() {
  // Init Serial Port
  Serial.begin(9600);

  // Init SPI bus
  SPI.begin(); 

  // Init MFRC522 
  rfid.PCD_Init();

  // Flash the LED
  pinMode(LED_BUILTIN, OUTPUT);
  digitalWrite(LED_BUILTIN, LOW);

  Serial.println("CARD READER STARTED");
}

void loop() {  
  if(! rfid.PICC_IsNewCardPresent()) {
    delay(100);
    return;
  }

  rfid.PICC_ReadCardSerial();

  // Check the header
  MFRC522::PICC_Type piccType = rfid.PICC_GetType(rfid.uid.sak);
  if (piccType != MFRC522::PICC_TYPE_MIFARE_MINI && piccType != MFRC522::PICC_TYPE_MIFARE_1K && piccType != MFRC522::PICC_TYPE_MIFARE_4K) {
    // tag is a MIFARE Classic
    return;
  }  
    
  // Read the cardID
  uint32_t cardID = rfid.uid.uidByte[0];
  cardID <<= 8; cardID |= rfid.uid.uidByte[1];
  cardID <<= 8; cardID |= rfid.uid.uidByte[2];  
  cardID <<= 8; cardID |= rfid.uid.uidByte[3]; 
  
  // Write the Card ID on Serial Console
  Serial.println("[" + String(cardID) + "]");

  // Flash LED
  digitalWrite(LED_BUILTIN, HIGH);
  delay(1000);
  digitalWrite(LED_BUILTIN, LOW);

  // Halt PICC
  rfid.PICC_HaltA();

  // Stop encryption on PCD
  rfid.PCD_StopCrypto1();
}