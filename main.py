import paho.mqtt.client as mqtt
from f_recognition import FaceRecognition
import time
import threading
face_recognition = FaceRecognition()




def f_rec(face_recognition):
    detected_face = face_recognition.run_recognition()
    if detected_face:
        print(f"Detected Face: {detected_face}")
        return detected_face
    else:
        print("No face detected .")
# Callback function to handle messages received from MQTT broker



def delayed_publish(client, message, delay):
    time.sleep(delay)
    print("5 secs Done .... Door Closed")
    
    client.publish("2FA/results", message)
    print("\n\nScan Card Please : ")


def on_message(client, userdata, message) :
    print("\n\n")
    if message.topic == "rfid/cards":
        CardID = message.payload.decode('utf-8')
        print("detected CardID: "+CardID)

        # Call facial recognition function from f_recognition.py
        print("Face Detection Process .... ")
        result = faceID = f_rec(face_recognition)
        if result == CardID:
            print("ACCESS Granted for 5 secs")
            client.publish("2FA/results", "Access authorised")
            # Schedule publishing of "Access refused" after 5 seconds
            threading.Thread(target=delayed_publish, args=(client, "Access refused", 5)).start()
        else:
            print("ACCESS Refused")
            client.publish("2FA/results", "Access refused")
            print("\n\nScan Card Please : ")
            
    
    


# Initialize MQTT client
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
print("Scan Card Please : ")
client.on_message = on_message

# Connect to MQTT broker
client.connect("192.168.11.101", 1883)

# Subscribe to topics
client.subscribe("rfid/cards")

# Start the MQTT client loop
client.loop_forever()


