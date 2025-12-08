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
        # Specify format="webm" so pydub knows how to decode it
        audio_segment = AudioSegment.from_file(audio_io, format="webm")
        
        # Optionally, you can convert the segment to WAV in memory.
        wav_io = io.BytesIO()
        audio_segment.export(wav_io, format="wav")
        wav_io.seek(0)
        
        # Read the WAV data using soundfile. Now it should be recognized.
        audio_array, sampling_rate = sf.read(wav_io, dtype="float64")
        
        # You can now process audio_array if needed (e.g., resampling, normalization, etc.)
        # For demonstration, we send the original audio_bytes to Gemini:
        prompt = "Please transcribe the following audio:"
        response = model.generate_content([
            prompt,
            {
                "mime_type": "audio/ogg; codecs=opus",  # Adjust if Gemini expects a different MIME type
                "data": audio_bytes
            }
        ])
        
        transcription = response.text if response.text else ""
        emit("transcription", {"text": transcription})
    except Exception as e:
        emit("transcription", {"error": str(e)})

if __name__ == "__main__":
    socketio.run(app, debug=True)


"""Error: Decoding failed. ffmpeg returned error code: 183 Output from ffmpeg/avlib: ffmpeg version 7.1 Copyright (c) 2000-2024 the FFmpeg developers built with gcc 13.3.0 (conda-forge gcc 13.3.0-1) configuration: --prefix=/home/ashish/anaconda3/envs/hf_202412 --cc=/home/conda/feedstock_root/build_artifacts/ffmpeg_1735646943276/_build_env/bin/x86_64-conda-linux-gnu-cc --cxx=/home/conda/feedstock_root/build_artifacts/ffmpeg_1735646943276/_build_env/bin/x86_64-conda-linux-gnu-c++ --nm=/home/conda/feedstock_root/build_artifacts/ffmpeg_1735646943276/_build_env/bin/x86_64-conda-linux-gnu-nm --ar=/home/conda/feedstock_root/build_artifacts/ffmpeg_1735646943276/_build_env/bin/x86_64-conda-linux-gnu-ar --disable-doc --enable-openssl --enable-demuxer=dash --enable-hardcoded-tables --enable-libfreetype --enable-libharfbuzz --enable-libfontconfig --enable-libopenh264 --enable-libdav1d --disable-gnutls --enable-libmp3lame --enable-libvpx --enable-libass --enable-pthreads --enable-vaapi --enable-libopenvino --enable-gpl --enable-libx264 --enable-libx265 --enable-libaom --enable-libsvtav1 --enable-libxml2 --enable-pic --enable-shared --disable-static --enable-version3 --enable-zlib --enable-libopus --enable-librsvg --pkg-config=/home/conda/feedstock_root/build_artifacts/ffmpeg_1735646943276/_build_env/bin/pkg-config libavutil 59. 39.100 / 59. 39.100 libavcodec 61. 19.100 / 61. 19.100 libavformat 61. 7.100 / 61. 7.100 libavdevice 61. 3.100 / 61. 3.100 libavfilter 10. 4.100 / 10. 4.100 libswscale 8. 3.100 / 8. 3.100 libswresample 5. 3.100 / 5. 3.100 libpostproc 58. 3.100 / 58. 3.100 [cache @ 0x63ef2e368c40] Inner protocol failed to seekback end : -38 [matroska,webm @ 0x63ef2e368540] EBML header parsing failed [cache @ 0x63ef2e368c40] Statistics, cache hits:1 cache misses:1 [in#0 @ 0x63ef2e368280] Error opening input: Invalid data found when processing input Error opening input file cache:pipe:0. Error opening input files: Invalid data found when processing input

"""