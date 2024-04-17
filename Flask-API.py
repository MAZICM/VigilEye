from flask import Flask, request, jsonify
from model_trainer import ModelTrainer
from f3 import FaceRecognition
from flask_cors import CORS

app = Flask(__name__)
cors = CORS(app, resources={r"*": {"origins": "http://localhost:3000"}})

face_recognition = FaceRecognition()

# Instantiate the ModelTrainer to access the get_expected_cardID function
model_trainer = ModelTrainer()

@app.route('/get_expected_cardID', methods=['POST'])
def get_expected_cardID_api():
    data = request.get_json()
    detected_face = data.get('detected_face')
    expected_cardID = model_trainer.get_expected_cardID(detected_face)
    if expected_cardID:
        return jsonify({'expected_cardID': expected_cardID})
    else:
        return jsonify({'error': 'User not found'}), 404

@app.route('/run_face_recognition', methods=['POST'])
def run_face_recognition_api():
    image_data = request.files['image'].read()
    detected_face = face_recognition.run_recognition(image_data)
    if detected_face:
        return jsonify({'detected_face': detected_face})
    else:
        return jsonify({'error': 'No face detected'}), 404

@app.route('/train_model', methods=['GET'])
def train_model_api():
    # Train the model
    model_trainer.train_and_save_model()
    return jsonify({'message': 'Model trained successfully'})

if __name__ == '__main__':
    from waitress import serve
    #app.run(debug=True, threaded=True)  # Enable threaded mode
    serve(app, host="127.0.0.1", port=5000)
