import os
import io
import base64
import pathlib
import numpy as np
import soundfile as sf
from flask import Flask, render_template
from flask_socketio import SocketIO, emit
import google.generativeai as genai

# Configure your API key for Gemini
genai.configure(api_key="YOUR_API_KEY_HERE")

# Initialize Gemini 2.0 Flash model
model = genai.GenerativeModel('models/gemini-2.0-flash')

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

@app.route("/")
def index():
    return render_template("index.html")

@socketio.on("audio_chunk")
def handle_audio_chunk(data):
    try:
        # Get the base64 encoded audio chunk from the client
        audio_b64 = data.get("chunk")
        if not audio_b64:
            emit("transcription", {"error": "No audio chunk received."})
            return

        # Decode the base64 string into bytes
        audio_bytes = base64.b64decode(audio_b64)

        # Optional: Convert the bytes into an audio array if you need to preprocess.
        # In this example, we'll pass the raw audio bytes (as received) to Gemini.
        # If required, you can use soundfile to load and verify:
        audio_io = io.BytesIO(audio_bytes)
        audio_array, sampling_rate = sf.read(audio_io, dtype="float64")
        # (Add any resampling or preprocessing here if needed.)

        # Define the prompt. Adjust the prompt as needed for your use case.
        prompt = "Please transcribe the following audio:"

        # Call Gemini with the prompt and audio content.
        # Note: Gemini expects a list of inputs where one entry is a text prompt
        # and the other is a dict containing the audio data and its MIME type.
        response = model.generate_content([
            prompt,
            {
                "mime_type": "audio/ogg; codecs=opus",  # Ensure this matches your client's format.
                "data": audio_bytes
            }
        ])

        # Extract the transcription text from the response.
        transcription = response.text if response.text else ""
        emit("transcription", {"text": transcription})
    except Exception as e:
        emit("transcription", {"error": str(e)})

if __name__ == "__main__":
    socketio.run(app, debug=True)
