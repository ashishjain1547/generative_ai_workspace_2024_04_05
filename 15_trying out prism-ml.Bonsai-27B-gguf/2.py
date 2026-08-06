import os
from huggingface_hub import hf_hub_download, list_repo_files
from llama_cpp import Llama

import json 

api_keys = json.load('/home/jain/Desktop/ws/api_keys_in_laptop.json')

# Authenticate with Hugging Face Hub
os.environ["HF_TOKEN"] = api_keys["hugging chat"]['value']

repo_id = "prism-ml/Bonsai-27B-gguf"

# Find the correct file
all_files = list_repo_files(repo_id)
gguf_files = sorted([f for f in all_files if f.endswith(".gguf")])

print("All GGUF Files...")
print(gguf_files)

# 2026-JUL-19 1600
# ['Bonsai-27B-F16.gguf', 'Bonsai-27B-Q1_0.gguf', 'Bonsai-27B-dspark-Q4_1.gguf', 'Bonsai-27B-dspark-bf16.gguf', 'Bonsai-27B-mmproj-BF16.gguf', 'Bonsai-27B-mmproj-Q8_0.gguf']
# Sizes: [53.8G, 3.80G, ]

if not gguf_files:
    raise FileNotFoundError("No GGUF files found in the repository")
filename = gguf_files[1]   # or pick the one you want from the printed list

print(f"Using: {filename}")
model_path = hf_hub_download(repo_id, filename)

llm = Llama(
    model_path=model_path,
    n_ctx=512,
    n_gpu_layers=-1,
    verbose=False
)

output = llm("Once upon a time,", max_tokens=32, temperature=0.0, echo=True)
print(output["choices"][0]["text"])