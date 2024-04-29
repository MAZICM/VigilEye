#include <SPI.h>
#include <MFRC522.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <WiFiManager.h> // https://github.com/tzapu/WiFiManager

#define SS_PIN    21
#define RST_PIN   22

#define LedB_PIN   25
#define LedG_PIN   26
#define LedR_PIN   27

#define MQTT_BROKER "192.168.0.103"
#define MQTT_PORT   1883
#define MQTT_TOPIC  "rfid/cards"
#define MQTT_RESULT_TOPIC "2FA/results"
String cardID = "";
String payloadString = "";

WiFiClient espClient;
PubSubClient client(espClient);

MFRC522 rfid(SS_PIN, RST_PIN);
MFRC522::MIFARE_Key key;

void setup() {
  WiFi.mode(WIFI_STA); // explicitly set mode, esp defaults to STA+AP
    // it is a good practice to make sure your code sets wifi mode how you want it.
 
    // put your setup code here, to run once:
    Serial.begin(115200);
  pinMode(LedB_PIN, OUTPUT);
  pinMode(LedG_PIN, OUTPUT);
  pinMode(LedR_PIN, OUTPUT);
  digitalWrite(LedB_PIN, HIGH);
  digitalWrite(LedG_PIN, HIGH);
  digitalWrite(LedR_PIN, HIGH);
  pinMode(5, OUTPUT);
  digitalWrite(5, HIGH);
  

  SPI.begin();
  rfid.PCD_Init();

  digitalWrite(LedB_PIN, LOW);
  digitalWrite(LedG_PIN, LOW);
  digitalWrite(LedR_PIN, HIGH);
  Serial.print("AP Start .....");
    //WiFiManager, Local intialization. Once its business is done, there is no need to keep it around
    WiFiManager wm;
 
    // reset settings - wipe stored credentials for testing
    // these are stored by the esp library
    wm.resetSettings();
 
    // Automatically connect using saved credentials,
    // if connection fails, it starts an access point with the specified name ( "AutoConnectAP"),
    // if empty will auto generate SSID, if password is blank it will be anonymous AP (wm.autoConnect())
    // then goes into a blocking loop awaiting configuration and will return success result
 
    bool res;
    // res = wm.autoConnect(); // auto generated AP name from chipid
    // res = wm.autoConnect("AutoConnectAP"); // anonymous ap
    res = wm.autoConnect("DoorAPID","VigilEye"); // password protected ap
    
    if(!res) {
        Serial.println("Failed to connect");
        delay(1000);
        //ESP.restart();
    } else
    {
        //if you get here you have connected to the WiFi    
        Serial.println("connected...yeey :)");
        digitalWrite(LedB_PIN, HIGH);
        digitalWrite(LedG_PIN, LOW);
        digitalWrite(LedR_PIN, LOW);
        client.setServer(MQTT_BROKER, MQTT_PORT);
        client.setCallback(callback); // Set callback function for incoming messages

    }
             
        
    

 

}

void loop() {
  if (!client.connected()) {
    reconnect();
  }

  client.loop();
  
  // Only attempt RFID read if no card has been read in the current scan
  if (cardID == "" && rfid.PICC_IsNewCardPresent() && rfid.PICC_ReadCardSerial()) {
    sendCardID(rfid.uid.uidByte, rfid.uid.size);
    digitalWrite(LedB_PIN, HIGH);
    delay(500);
    digitalWrite(LedB_PIN, LOW);
    delay(500);
    digitalWrite(LedB_PIN, HIGH);
    delay(500);
    digitalWrite(LedB_PIN, LOW);
    delay(500);
    digitalWrite(LedB_PIN, HIGH);

  }
}

void connectWiFi() {
  Serial.println("Connecting to WiFi...");
  //WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  while (WiFi.status() != WL_CONNECTED) {
    Serial.print(".");
    delay(500);
  }
  Serial.println("\nConnected to WiFi");
}

void reconnect() {
  while (!client.connected()) {
    Serial.println("Attempting MQTT connection...");
    if (client.connect("ESP32Client")) {
      Serial.println("Connected to MQTT broker");
      client.subscribe(MQTT_RESULT_TOPIC); // Subscribe to the result topic
    } else {
      Serial.print("Failed, rc=");
      Serial.print(client.state());
      Serial.println(" trying again in 1 second");
      delay(1000);
    }
  }
}
void sendCardID(byte *buffer, byte bufferSize) {
  Serial.println("Card detected");

  for (byte i = 0; i < bufferSize; i++) {
    if (buffer[i] < 0x10) cardID += "0";
    cardID += String(buffer[i], HEX);
  }
  
  // Publish card ID to MQTT topic without quotes and b' prefix
  if (client.publish(MQTT_TOPIC, cardID.c_str())) {
    Serial.println("Card ID sent to MQTT broker: " + cardID);

    cardID = ""; // Clear cardID only after successful publishing
    delay(1000);
  } else {
    Serial.println("Failed to send card ID to MQTT broker");
  }
}



void callback(char* topic, byte* payload, unsigned int length) {
  Serial.print("Message arrived [");
  Serial.print(topic);
  Serial.print("] ");
  Serial.println();
  Serial.println("Payload: ");

  for (int i = 0; i < length; i++) {
    payloadString += (char)payload[i];
  }
  Serial.print(payloadString);

  if (payloadString == "Access authorised") {
    digitalWrite(5, LOW);
    Serial.print("open");
    digitalWrite(LedB_PIN, LOW);
    digitalWrite(LedG_PIN, HIGH);
    delay(500);
    digitalWrite(LedG_PIN, LOW);
    delay(500);
    digitalWrite(LedG_PIN, HIGH);
    delay(500);
    digitalWrite(LedG_PIN, LOW);
    delay(500);
    digitalWrite(LedB_PIN, HIGH);
  }
  if (payloadString == "Access refused") {
    digitalWrite(5, HIGH);
    Serial.print("close");
    digitalWrite(LedB_PIN, LOW);
    digitalWrite(LedR_PIN, HIGH);
    delay(500);
    digitalWrite(LedR_PIN, LOW);
    delay(500);
    digitalWrite(LedR_PIN, HIGH);
    delay(500);
    digitalWrite(LedR_PIN, LOW);
    delay(500);
    digitalWrite(LedR_PIN, HIGH);
  }

  // Reset variables
  payloadString = "";

  // Resubscribe to the topic
  //client.subscribe(MQTT_RESULT_TOPIC);
}
