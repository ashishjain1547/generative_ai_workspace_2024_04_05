import pickle
import json

with open("3B_out/llama_index.pickle", "rb") as f:
    index = pickle.load(f)


# with open("../../../api_keys_in_laptop.json", "r") as f:
#     api_keys = json.load(f)

# OPENAI_API_KEY = api_keys['openai']

import google.generativeai as genai
#from llama_index.llms.generic_utils import CustomLLM
from llama_index.llms.base import LLM

class GeminiLLM(LLM):
    def complete(self, prompt: str) -> str:
        model = genai.GenerativeModel("gemini-1.5-pro")  # You can use "gemini-1.5-flash" for faster responses
        response = model.generate_content(prompt)
        return response.text  # Extract the response text

# Create the LlamaIndex query engine with Gemini
llm = GeminiLLM()
query_engine = index.as_query_engine(llm=llm)

response = query_engine.query("What does this book teach about life?")
print(response)
