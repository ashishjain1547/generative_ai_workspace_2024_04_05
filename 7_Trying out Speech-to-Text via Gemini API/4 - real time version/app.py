import os
import io
import base64
import pathlib
import numpy as np
import soundfile as sf
from flask import Flask, render_template
from flask_socketio import SocketIO, emit
import google.generativeai as genai
from pydub import AudioSegment

# Configure your API key for Gemini
import json

with open('/home/ashish/Desktop/ws/gh/api_keys.json', mode='r') as f:
    api_keys = json.load(f)

genai.configure(api_key=api_keys['KeshavPawar'])



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

        # Use pydub to convert the raw WebM data to WAV in memory.
        audio_io = io.BytesIO(audio_bytes)
        audio_segment = AudioSegment.from_file(audio_io, format="webm")
        
        # Export to WAV in-memory
        wav_io = io.BytesIO()
        audio_segment.export(wav_io, format="wav")
        wav_io.seek(0)
        
        # Read the WAV data using soundfile.
        audio_array, sampling_rate = sf.read(wav_io, dtype="float64")
        
        # Define the prompt
        prompt = "Please transcribe the following audio:"
        
        # Call Gemini with the prompt and the original audio bytes (adjust MIME type if necessary)
        response = model.generate_content([
            prompt,
            {
                "mime_type": "audio/ogg; codecs=opus",  # adjust this if Gemini expects WAV
                "data": audio_bytes
            }
        ])
        
        transcription = response.text if response.text else ""
        emit("transcription", {"text": transcription})
    except Exception as e:
        msg = str(e)
        if "Decoding failed." in msg:
            emit("transcription", {"error": "Decoding failed. Please try again.", "complete_msg": msg})
        else:
            emit("transcription", {"error": msg})

if __name__ == "__main__":
    socketio.run(app, debug=True)


"""

"""
