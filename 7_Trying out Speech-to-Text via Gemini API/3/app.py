import os
import pathlib
import google.generativeai as genai
from flask import Flask, request, jsonify, render_template

# Configure the API key for the Gemini model

import json


with open('/home/ashish/Desktop/ws/gh/api_keys.json', mode='r') as f:
    api_keys = json.load(f)

genai.configure(api_key=api_keys['KeshavPawar'])

# Initialize the Gemini model
model = genai.GenerativeModel('models/gemini-2.0-flash')

app = Flask(__name__)

# Directory to store uploaded audio files
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Function to process and transcribe audio
def transcribe_audio(audio_path):
    if not audio_path:
        return {"error": "No audio provided. Please try again."}
    try:
        # Read the audio file as binary data
        audio_data = pathlib.Path(audio_path).read_bytes()

        # Define the prompt for Gemini
        prompt = "Please summarize the audio."

        # Send audio data (with Opus MIME type) to the Gemini model
        response = model.generate_content([
            prompt,
            {
                "mime_type": "audio/ogg; codecs=opus",  # Opus format
                "data": audio_data
            }
        ])

        return {"transcription": response.text}

    except Exception as e:
        return {"error": f"Error processing audio: {str(e)}"}

# Render the HTML interface
@app.route("/")
def index():
    return render_template("index.html")

# Endpoint to receive audio file upload and transcribe it
@app.route("/upload", methods=["POST"])
def upload():
    if "audio" not in request.files:
        return jsonify({"error": "No audio file provided."}), 400

    audio_file = request.files["audio"]
    if audio_file.filename == "":
        return jsonify({"error": "No file selected."}), 400

    # Save the uploaded file to disk
    filepath = os.path.join(UPLOAD_FOLDER, audio_file.filename)
    audio_file.save(filepath)

    # Process the saved audio file
    result = transcribe_audio(filepath)
    return jsonify(result)

if __name__ == "__main__":
    app.run(debug=True)
