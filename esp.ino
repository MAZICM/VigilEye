#include <SPI.h>
#include <MFRC522.h>
#include <WiFi.h>
#include <PubSubClient.h>

#define SS_PIN    21
#define RST_PIN   22

#define WIFI_SSID     "TP-Link_12D4"
#define WIFI_PASSWORD "90623585"

#define MQTT_BROKER "192.168.11.101"
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
  Serial.begin(115200);
  pinMode(5, OUTPUT);
  digitalWrite(5, HIGH);
  connectWiFi();
  client.setServer(MQTT_BROKER, MQTT_PORT);
  client.setCallback(callback); // Set callback function for incoming messages
  SPI.begin();
  rfid.PCD_Init();
}

void loop() {
  if (!client.connected()) {
    reconnect();
  }

  client.loop();
  
  // Only attempt RFID read if no card has been read in the current scan
  if (cardID == "" && rfid.PICC_IsNewCardPresent() && rfid.PICC_ReadCardSerial()) {
    sendCardID(rfid.uid.uidByte, rfid.uid.size);
  }
}

void connectWiFi() {
  Serial.println("Connecting to WiFi...");
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
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
  }
  if (payloadString == "Access refused") {
    digitalWrite(5, HIGH);
  }

  // Reset variables
  payloadString = "";

  // Resubscribe to the topic
  //client.subscribe(MQTT_RESULT_TOPIC);
}
