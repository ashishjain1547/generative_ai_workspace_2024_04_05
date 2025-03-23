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


query_engine = index.as_query_engine()
response = query_engine.query("What do they do to make money?")
print(response)
