import dill
from llama_index.core import VectorStoreIndex
# from llama_index.core.embeddings import HuggingFaceEmbedding
# from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.embeddings import HuggingFaceEmbedding

# Load parsed content from dill file
with open('2_out/parsed_content_20250323.dill', 'rb') as f:
    parsed_content_dill = dill.load(f)

# Convert to llama index nodes
nodes = parsed_content_dill.to_llama_index_nodes()

# Create index with local embedding model
index = VectorStoreIndex(
    nodes=nodes,
    embed_model=HuggingFaceEmbedding(model_name="sentence-transformers/all-MiniLM-L6-v2")
)

# Save the index
index.write_to_disk("2_out/llama_index")

print("Index created and saved successfully!")
