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
from model_trainer import ModelTrainer  

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
logs_collection = db['logs'] 
# Initialize Flask app and SocketIO
app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")
CORS(app)
global add_user_mon 
add_user_mon = 0
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


from datetime import datetime
mongo_client = MongoClient('mongodb://localhost:27017/')
db = mongo_client['2FA']
users_collection = db['users']

# Global variable to store form data
form_data = None  # Initially, no form data
def on_message(client, userdata, message):
    global latest_cardID
    global add_user_mon
    logging.info("Received MQTT message: %s", str(message.payload.decode("utf-8")))
    if add_user_mon == 0:
        if message.topic == "rfid/cards":
            cardID = message.payload.decode('utf-8')
            logging.info("Detected CardID: %s", cardID)
            latest_cardID = cardID
            
            # Get the owner's name based on card ID from MongoDB
            user = db['users'].find_one({'cardID': cardID})
            owner_name = user['name'] if user else 'Unknown'
            logging.info("Owner name: %s", owner_name)
            owner_image_data = user.get("data", None)
            base64_image = owner_image_data if owner_image_data else None 

            # Record the scan time and create the base log entry
            scan_time = datetime.now()  # Record the current date and time
            log_entry = {
                "scan_time": scan_time,
                "cardID": cardID,
                "owner_name": owner_name,
            }
            socketio.emit("latest_cardID", {
                    'cardID': cardID,
                    'ownerName': owner_name,
                    'ownerImage': base64_image
            })
            # Ensure synchronous operation with f_rec
            face_recognition = FaceRecognition(socketio=socketio)
            detected_face = f_rec(face_recognition)

            # Add base log information
            log_entry["detected_face"] = detected_face

            if detected_face is None:
                base64_image = image_to_base64("icons8-error-80.jpg")
                log_entry["image_data"] = base64_image  # Save the error image
                logs_collection.insert_one(log_entry)  # Save the log entry
                socketio.emit("face_detection_error", {"error": "No face detected. Please try again."})
                return  # Exit early if no face is detected

            logging.info("Detected face: %s", detected_face)

            expected_cardID = get_expected_cardID(detected_face)

            # Add the expected card ID and detected image
            log_entry["expected_cardID"] = expected_cardID
            detected_image_path = "detected_face.jpg"
            base64_detected_image = image_to_base64(detected_image_path)
            log_entry["image_data"] = base64_detected_image  # Save the detected image

            if expected_cardID is None:
                logging.warning("No user found with the detected face: %s", detected_face)
                log_entry["access_decision"] = "No matching user found"
                logs_collection.insert_one(log_entry)  # Save the log entry
                socketio.emit("access_refused", {"status": "refused", "message": "Access denied. No matching user found."})
                return

            # Check if the expected card ID matches the detected card ID
            if expected_cardID == cardID:
                logging.info("ACCESS Granted for 5 secs")
                socketio.emit("access_granted", {"status": "granted"})
                
                # Save the final access decision
                log_entry["access_decision"] = "Access granted"
                
                # Insert the log with the granted decision
                logs_collection.insert_one(log_entry)
                
                threading.Thread(
                    target=delayed_publish,
                    args=(mqtt_client, "Access refused", 5)  # Message is "Access refused" after 5 seconds
                ).start()
                
            else:
                logging.info("ACCESS Refused")
                socketio.emit("access_refused", {"status": "refused", "reason": "Card ID does not match."})
                
                # If access is refused, save that decision with the card ID mismatch reason
                log_entry["access_decision"] = "Card ID does not match"
                logs_collection.insert_one(log_entry)
    elif add_user_mon == 1 : 
        add_user_mon = 0
        global form_data  # Use the global form_data variable
        cardID = message.payload.decode('utf-8')
        socketio.emit("scanned_card_id", {"cardID": cardID})
        logging.info("Received MQTT message with Card ID: %s", cardID   )
        
        if form_data and 'cardID' not in form_data:
            # Update form_data with the received card ID
            form_data['cardID'] = cardID
            
            # Insert into MongoDB
            users_collection.insert_one(form_data)

            logging.info("New user added with Card ID: %s", cardID)
            
            # Reset form_data after successful insertion
            form_data = None

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

@app.route('/api/add-user', methods=['POST'])
def add_user():
    global form_data
    user_name = request.form.get('name')
    
    print(user_name)
    image_data = request.form.get('image')
      # Base64 image data
    global add_user_mon 
    
    print("heeere")
    print(image_data)
    type(image_data)
    raw_base64 = image_data.replace("data:image/png;base64,", "")
    if not user_name or not image_data :
        return jsonify({'error': 'Missing required fields'}), 400  # Check for required fields

    #image_base64 = base64.b64encode(image_binary).decode('utf-8')  # Encode into Base64 and decode for storage
    
    add_user_mon = 1
    # Store the form data globally (waiting for card ID from MQTT)
    form_data = {
        'name': user_name,
        'data': raw_base64,
        'scan_time': datetime.now().isoformat(),  # Record the current time
    }

    logging.info("Received form data. Waiting for Card ID...")
    return jsonify({'success': True, 'message': 'Form data received, waiting for Card ID'}), 200

users_collection = db['users']


@app.route('/api/get-users', methods=['GET'])
def get_users():
    users = users_collection.find({})  # Fetch all users
    users_list = []

    for user in users:
        # Create a user dictionary with necessary details
        user_info = {
            '_id': str(user['_id']),  # Convert ObjectId to string
            'name': user['name'],
            'cardID': user['cardID'],
            'filename': user.get('filename', 'N/A'),
            'image_data': user.get('data', None),  # Include Base64 image data
        }
        users_list.append(user_info)

    return jsonify(users_list)  # Return all users as a JSON array

@app.route('/api/train-model', methods=['POST'])
def train_model():
    try:
        trainer = ModelTrainer()  # Initialize your model trainer
        trainer.train_and_save_model()  # Run the training logic

        return jsonify({'success': True, 'message': 'Model trained successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500  # Handle errors



# Define an endpoint to get model history
@app.route('/api/model-history', methods=['GET'])
def get_model_history():
    try:
        # Get the collection
        collection = db["AI-Models"]

        # Fetch all documents in reverse order (newest first)
        model_docs = collection.find({}).sort({"datetime": -1})

        # Convert to a list of dictionaries
        model_history = [
            {"id": str(doc["_id"]), "datetime": doc["datetime"]}
            for doc in model_docs
        ]

        # Return the result as JSON
        return jsonify(model_history), 200

    except Exception as e:
        # Handle errors
        return jsonify({"error": str(e)}), 500    

if __name__ == '__main__':

    socketio.run(app, host="192.168.0.103", port=5000)
