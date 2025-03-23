import pickle
import json
import os


with open("3B_out/llama_index.pickle", "rb") as f:
    index = pickle.load(f)


with open("../../api_keys_local.json", "r") as f:
    api_keys = json.load(f)

# OPENAI_API_KEY = api_keys['openai']
# ✅ Set the Google Gemini API Key
os.environ["GOOGLE_API_KEY"] = api_keys['Gemini_KeshavPawar']

from langchain_google_genai import ChatGoogleGenerativeAI

llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0.5)


query_engine = index.as_query_engine(llm=llm)

response = query_engine.query("What does this book teach about life?")
print(response)

response = query_engine.query("What is the gist of this book?")
print(response)
