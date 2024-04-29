import logging
from flask_cors import CORS
from flask_socketio import SocketIO
import paho.mqtt.client as mqtt
from f3 import FaceRecognition
from pymongo import MongoClient
import threading
import time
import base64
from flask import Flask, jsonify, request, send_file
from io import BytesIO

# Configure logging
logging.basicConfig(level=logging.DEBUG)


def image_to_base64(image_path):
    with open(image_path, "rb") as img_file:
        base64_str = base64.b64encode(img_file.read()).decode('utf-8')
    return base64_str

# MQTT settings
mqtt_broker_address = "192.168.0.103"  # Update with your MQTT broker address
mqtt_topic = "rfid/cards"  # Update with your MQTT topic
# Set up MongoDB connection
client = MongoClient('mongodb://localhost:27017/')
db = client['2FA']
collection = db['users']
# Initialize Flask app and SocketIO
app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")
CORS(app)


latest_cardID = "0000"  # Initialize latest_cardID variable



def f_rec(face_recognition):
    detected_face = face_recognition.run_recognition()
    if detected_face:
        
        return detected_face
    else:
        base64_image = image_to_base64("icons8-error-80.jpg")
        socketio.emit("ai_frame", {"frame": base64_image})
        logging.warning("No face detected 1.")

def delayed_publish(client, message, delay):
    time.sleep(delay)
    logging.info("5 secs Done .... Door Closed")
    client.publish("2FA/results", message)
    logging.info("\n\nScan Card Please : ")

def get_expected_cardID(detected_face):
    client = MongoClient('mongodb://localhost:27017/')
    db = client['2FA']
    collection = db['users']
    
    user = collection.find_one({'name': detected_face})
    if user:
        expected_cardID = user['cardID']
        return expected_cardID
    else:
        logging.warning(f"No user found with the name: {detected_face}")
        return None


def on_message(client, userdata, message):
    global latest_cardID
    logging.info("Received MQTT message: %s", str(message.payload.decode("utf-8")))

    if message.topic == "rfid/cards":
        cardID = message.payload.decode('utf-8')
        logging.info("Detected CardID: %s", cardID)
        latest_cardID = cardID
        
        # Get the owner's name based on card ID from MongoDB
        user = collection.find_one({'cardID': cardID})
        owner_name = user['name'] if user else 'Unknown'
        logging.info("Owner name: %s", owner_name)

        # Emit both cardID and owner's name
        socketio.emit("latest_cardID", {"cardID": cardID, "ownerName": owner_name})

        # Ensure synchronous operation with f_rec
        face_recognition = FaceRecognition(socketio=socketio)
        detected_face = f_rec(face_recognition)
        
        if detected_face is None:
            base64_image = image_to_base64("icons8-error-80.jpg")
            socketio.emit("ai_frame", {"frame": base64_image})
            logging.warning("No face detected 2")
            socketio.emit("face_detection_error", {"error": "No face detected. Please try again."})
            return  # Early exit if no face is detected

        logging.info("Detected face: %s", detected_face)

        expected_cardID = get_expected_cardID(detected_face)
        if expected_cardID is None:
            logging.warning("No user found with the detected face: %s", detected_face)
            socketio.emit("access_refused", {"status": "refused", "message": "Access denied. No matching user found."})
            return  # Early exit if no expected cardID is found

        logging.info("Expected CardID: %s", expected_cardID)

        # Check if the expected card ID matches the detected card ID
        if expected_cardID == cardID:
            logging.info("ACCESS Granted for 5 secs")
            client.publish("2FA/results", "Access authorised")
            
            # Emit success event
            socketio.emit("access_granted", {"status": "granted"})
            
            # Start a thread to handle delayed actions without blocking
            threading.Thread(
                target=delayed_publish,
                args=(client, "Access refused", 5)  # Message is "Access refused" after 5 seconds
            ).start()

        else:
            logging.info("ACCESS Refused")
            socketio.emit("access_refused", {"status": "refused","reason": "Card ID does not match.",})

        # Final message for the console log
        logging.info("End of on_message processing")

# Set up MQTT client
mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
mqtt_client.on_message = on_message
mqtt_client.connect(mqtt_broker_address)
mqtt_client.subscribe(mqtt_topic)
mqtt_client.loop_start()

# Endpoint to retrieve the latest card ID
@app.route('/latest_cardID', methods=['GET'])
def get_latest_cardID():
    global latest_cardID
    if latest_cardID:
        return jsonify({'latest_cardID': latest_cardID})
    else:
        return jsonify({'error': 'No card ID received'}), 404
    
@app.route('/api/getOwnerName', methods=['GET'])
def get_owner_name():
    card_id = request.args.get('cardID')
    
    if card_id:
        user = collection.find_one({'cardID': card_id})
        if user:
            logging.info("Owner Name: %s", user['name'])
            return jsonify({'ownerName': user['name']})
        else:
            return jsonify({'error': 'User not found'}), 404
    else:
        return jsonify({'error': 'Missing cardID parameter'}), 400


from flask import send_file

# MongoDB setup
client = MongoClient('mongodb://localhost:27017/')
db = client['2FA']
collection = db['users']

@app.route('/api/getOwnerImage', methods=['GET'])
def get_owner_image():
    card_id = request.args.get('cardID')

    if card_id:
        user = collection.find_one({'cardID': card_id})
        if user and 'data' in user:
            try:
                image_data = user['data']
                image_data_decoded = base64.b64decode(image_data)
                # Create a BytesIO object
                image_stream = BytesIO(image_data_decoded)
                # Return the image data directly
                return send_file(image_stream, mimetype='image/png')
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        else:
            return jsonify({'error': 'User not found or image data not available'}), 404
    else:
        return jsonify({'error': 'Missing cardID parameter'}), 400

if __name__ == '__main__':
    socketio.run(app, host="192.168.0.103", port=5000)
