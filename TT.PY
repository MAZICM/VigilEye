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

face_recognition = FaceRecognition()

# MQTT settings
mqtt_broker_address = "192.168.11.154"  # Update with your MQTT broker address
mqtt_topic = "rfid/cards"  # Update with your MQTT topic

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
        logging.warning("No face detected.")

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
    global latest_cardID  # Use the global variable to store the latest card ID
    logging.info("Received MQTT message: %s", str(message.payload.decode("utf-8")))
    logging.info("\n\n")
    if message.topic == "rfid/cards":
        cardID = message.payload.decode('utf-8')
        logging.info("Detected CardID: %s", cardID)
        
        # Update latest_cardID
        latest_cardID = cardID
        socketio.emit("latest_cardID", {"cardID": cardID})
        detected_face = f_rec(face_recognition)
        if detected_face:
            expected_cardID = get_expected_cardID(detected_face)
            logging.info("Expected CardID: %s", expected_cardID)
            if expected_cardID == cardID:
                logging.info("ACCESS Granted for 5 secs")
                # Emit event to the client
                threading.Thread(target=delayed_publish, args=(client, "Access refused", 5)).start()
            else:
                logging.info("ACCESS Refused")
                logging.info("\n\nScan Card Please : ")

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
    client = MongoClient('mongodb://localhost:27017/')
    db = client['2FA']
    collection = db['users']

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
    socketio.run(app, host="192.168.11.154", port=5000)
