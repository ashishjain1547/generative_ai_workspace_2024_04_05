# pip install transformers gguf torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from huggingface_hub import hf_hub_download

# 1. Download the GGUF file (same as before)
repo_id = "prism-ml/Bonsai-27B-gguf"
filename = "bonsai-27b-Q1_K_M.gguf"
model_path = hf_hub_download(repo_id, filename)

# 2. Load with Transformers (GGUF support built-in)
tokenizer = AutoTokenizer.from_pretrained(repo_id, gguf_file=filename)
model = AutoModelForCausalLM.from_pretrained(
    repo_id,
    gguf_file=filename,
    device_map="auto"   # or "cpu"
)

# 3. Generate
inputs = tokenizer("Once upon a time,", return_tensors="pt")
outputs = model.generate(**inputs, max_new_tokens=32)
print(tokenizer.decode(outputs[0], skip_special_tokens=True))