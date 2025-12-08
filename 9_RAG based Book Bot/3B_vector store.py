import dill
from llama_index.core import VectorStoreIndex
from langchain.embeddings import HuggingFaceEmbeddings

# Initialize a Hugging Face embedding model (for example, using "all-MiniLM-L6-v2")
embedding_model = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

# Load parsed content from dill file
with open('2_out/parsed_content_20250323.dill', 'rb') as f:
    parsed_content_dill = dill.load(f)

# Convert to llama index nodes
nodes = parsed_content_dill.to_llama_index_nodes()

# Create index with local embedding model
index = VectorStoreIndex(
    nodes=nodes,
    embed_model=embedding_model
)


import pickle

print("Pickle version:", pickle.format_version)

with open("3B_out/llama_index.pickle", "wb") as f:
    pickle.dump(index, f)

with open('3B_out/llama_index.dill', 'wb') as f:
    dill.dump(index, f)

print("Index created and saved successfully!")
