/*********************************************************************
 This is an example for our nRF51822 based Bluefruit LE modules

 Pick one up today in the adafruit shop!

 Adafruit invests time and resources providing this open source code,
 please support Adafruit and open-source hardware by purchasing
 products from Adafruit!

 MIT license, check LICENSE for more information
 All text above, and the splash screen below must be included in
 any redistribution
*********************************************************************/

/*
    Please note the long strings of data sent mean the *RTS* pin is
    required with UART to slow down data sent to the Bluefruit LE!
*/

#include <Arduino.h>
#include <SPI.h>
#if not defined (_VARIANT_ARDUINO_DUE_X_) && not defined (_VARIANT_ARDUINO_ZERO_)
  #include <SoftwareSerial.h>
#endif

#include "Adafruit_BLE.h"
#include "Adafruit_BluefruitLE_SPI.h"
#include "Adafruit_BluefruitLE_UART.h"

#include "BluefruitConfig.h"

#include "DHT.h"          // DHT & AM2302 library

// Data pin connected to AM2302
#define DHTPIN 2
#define DHTTYPE DHT22       // DHT 22  (AM2302)

// Initialize DHT sensor
DHT dht(DHTPIN, DHTTYPE);

// Create the bluefruit object, either software serial...uncomment these lines
/*
SoftwareSerial bluefruitSS = SoftwareSerial(BLUEFRUIT_SWUART_TXD_PIN, BLUEFRUIT_SWUART_RXD_PIN);

Adafruit_BluefruitLE_UART ble(bluefruitSS, BLUEFRUIT_UART_MODE_PIN,
                      BLUEFRUIT_UART_CTS_PIN, BLUEFRUIT_UART_RTS_PIN);
*/

/* ...or hardware serial, which does not need the RTS/CTS pins. Uncomment this line */
// Adafruit_BluefruitLE_UART ble(BLUEFRUIT_HWSERIAL_NAME, BLUEFRUIT_UART_MODE_PIN);

/* ...hardware SPI, using SCK/MOSI/MISO hardware SPI pins and then user selected CS/IRQ/RST */
Adafruit_BluefruitLE_SPI ble(BLUEFRUIT_SPI_CS, BLUEFRUIT_SPI_IRQ, BLUEFRUIT_SPI_RST);

/* ...software SPI, using SCK/MOSI/MISO user-defined SPI pins and then user selected CS/IRQ/RST */
//Adafruit_BluefruitLE_SPI ble(BLUEFRUIT_SPI_SCK, BLUEFRUIT_SPI_MISO,
//                             BLUEFRUIT_SPI_MOSI, BLUEFRUIT_SPI_CS,
//                             BLUEFRUIT_SPI_IRQ, BLUEFRUIT_SPI_RST);


// A small helper
void error(const __FlashStringHelper*err) {
  Serial.println(err);
  while (1);
}

/* The service information */

int32_t hrmServiceId;
int32_t batServiceId;
int32_t hrmMeasureCharId;
int32_t hrmLocationCharId;
int32_t batMeasureCharId;

uint8_t batteryTimer = 100; //100 x 3 sec = 5 min
/**************************************************************************/
/*!
    @brief  Sets up the HW an the BLE module (this function is called
            automatically on startup)
*/
/**************************************************************************/
void setup(void)
{
  //while (!Serial); // required for Flora & Micro
  delay(500);

  boolean success;

  Serial.begin(115200);
  
  dht.begin();
  
  Serial.println(F("Adafruit Bluefruit - Comfstat"));
  Serial.println(F("---------------------------------------------------"));

  randomSeed(micros());

  /* Initialise the module */
  Serial.print(F("Initialising the Bluefruit LE module: "));

  if ( !ble.begin(VERBOSE_MODE) )
  {
    error(F("Couldn't find Bluefruit, make sure it's in CoMmanD mode & check wiring?"));
  }
  Serial.println( F("OK!") );

  /* Perform a factory reset to make sure everything is in a known state */
  Serial.println(F("Performing a factory reset: "));
  if (! ble.factoryReset() ){
       error(F("Couldn't factory reset"));
  }

  /* Disable command echo from Bluefruit */
  ble.echo(false);

  Serial.println("Requesting Bluefruit info:");
  /* Print Bluefruit information */
  ble.info();

  // this line is particularly required for Flora, but is a good idea
  // anyways for the super long lines ahead!
  // ble.setInterCharWriteDelay(5); // 5 ms

  /* Change the device name to make it easier to find */
  Serial.println(F("Setting device name to 'Bluefruit Environment': "));

  if (! ble.sendCommandCheckOK(F("AT+GAPDEVNAME=Bluefruit ENV-Y")) ) {
    error(F("Could not set device name?"));
  }

  /* Add the Environment Sensing Service definition */
  /* Service ID should be 1 */
  Serial.println(F("Adding the Environment Service definition (UUID = 0x181A): "));
  success = ble.sendCommandWithIntReply( F("AT+GATTADDSERVICE=UUID=0x181A"), &hrmServiceId);
  if (! success) {
    error(F("Could not add Environment Sensing service"));
  }

  /* Add the Temperature characteristic */
  /* Chars ID for Measurement should be 1 */
  Serial.println(F("Adding the Temperature characteristic (UUID = 0x2A6E): "));
  success = ble.sendCommandWithIntReply( F("AT+GATTADDCHAR=UUID=0x2A6E, PROPERTIES=0x10, MIN_LEN=3, MAX_LEN=5"), &hrmMeasureCharId);
    if (! success) {
    error(F("Could not add Temperature characteristic"));
  }

  /* Add the Humidity characteristic */
  /* Chars ID for Humidity should be 2 */
  Serial.println(F("Adding the Humidity characteristic (UUID = 0x2A6F): "));
  success = ble.sendCommandWithIntReply( F("AT+GATTADDCHAR=UUID=0x2A6F, PROPERTIES=0x10, MIN_LEN=3, MAX_LEN=5"), &hrmLocationCharId);
    if (! success) {
    error(F("Could not add BSL characteristic"));
  }

  /* Add the Battery Service definition */
  /* Service ID should be 1 */
  Serial.println(F("Adding the Battery Service definition (UUID = 0x180F): "));
  success = ble.sendCommandWithIntReply( F("AT+GATTADDSERVICE=UUID=0x180F"), &batServiceId);
  if (! success) {
    error(F("Could not add Battery service"));
  }

  /* Add the Battery Level characteristic */
  /* Chars ID for Measurement should be 1 */
  Serial.println(F("Adding Battery Level characteristic (UUID = 0x2A19): "));
  success = ble.sendCommandWithIntReply( F("AT+GATTADDCHAR=UUID=0x2A19, PROPERTIES=0x10, MIN_LEN=1,VALUE=100"), &batMeasureCharId);
    if (! success) {
    error(F("Could not add HRM characteristic"));
  }
  
  /* Add Environmental Sensing Service to the advertising data (needed for Nordic apps to detect the service) */
  Serial.print(F("Adding Environmental Sensing Service to the advertising payload: "));
  ble.sendCommandCheckOK( F("AT+GAPSETADVDATA=03-02-1A-18") );
  //ble.sendCommandCheckOK( F("AT+GAPSETADVDATA=03-02-1A-18") );

    /* Add the Battery Service to the advertising data (needed for Nordic apps to detect the service) */
  Serial.print(F("Adding Battery Service UUID to the advertising payload: "));
  ble.sendCommandCheckOK( F("AT+GAPSETADVDATA=03-02-0F-18") );

  /* Reset the device for the new service setting changes to take effect */
  Serial.print(F("Performing a SW reset (service changes require a reset): "));
  ble.reset();

  Serial.println();
}

/** Send randomized heart rate data continuously **/
void loop(void)
{
  // Wait a few seconds between measurements.
  delay(3000);

  // Reading temperature or humidity takes about 250 milliseconds!
  // Sensor readings may also be up to 2 seconds 'old' (its a very slow sensor)
  float h = dht.readHumidity();
  float t = dht.readTemperature();

  // check if returns are valid, if they are NaN (not a number) then something went wrong!
  if (isnan(t) || isnan(h)) {
    Serial.println(F("Failed to read from DHT sensor!"));
  }
  else {
    Serial.print(F("Humidity: ")); 
    Serial.print(h);
    Serial.print(F(" %\t"));
    Serial.print(F("Temperature: ")); 
    Serial.print(t);
    Serial.println(F(" C"));

    /*double myFloat = random(1, 500) / 100.0;
    char myBuffer[16];
    dtostrf(myFloat, 5, 2, myBuffer);*/
  
    Serial.print(F("Updating temperature value to "));
    Serial.print(t);
    Serial.println(F(" Temperature"));
  
    /* Command is sent when \n (\r) or println is called */
    /* AT+GATTCHAR=CharacteristicID,value */
    ble.print( F("AT+GATTCHAR=") );
    ble.print( hrmMeasureCharId );
    ble.print( F(",") );
    ble.println(t, HEX);
    //ble.println(myBuffer);

    ble.print( F("AT+GATTCHAR=") );
    ble.print( hrmLocationCharId );
    ble.print( F(",") );
    ble.println(h, HEX);
  
    /* Check if command executed OK */
    if ( !ble.waitForOK() )
    {
      Serial.println(F("Failed to get response!"));
    }
  
  }

  #define VBATPIN A9

   if (batteryTimer == 0) {
    float measuredvbat = analogRead(VBATPIN);
    measuredvbat *= 2;    // we divided by 2, so multiply back
    measuredvbat *= 3.3;  // Multiply by 3.3V, our reference voltage
    measuredvbat /= 1024; // convert to voltage
    Serial.print("VBat: " ); Serial.println(measuredvbat);
    int battery = (measuredvbat * 100)/4.2;
  
    Serial.print(F("Updating Baterry value to "));
    Serial.print(battery);
    Serial.println(F(" %"));
  
    /* Command is sent when \n (\r) or println is called */
    /* AT+GATTCHAR=CharacteristicID,value */
    ble.print( F("AT+GATTCHAR=") );
    ble.print( batMeasureCharId );
    ble.print( F(",") );
    ble.println(battery);

    batteryTimer = 100;
   }

   batteryTimer = batteryTimer -1;
 
}
