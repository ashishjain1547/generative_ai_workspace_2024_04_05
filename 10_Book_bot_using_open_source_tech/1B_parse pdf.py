from langchain.text_splitter import SemanticChunker
from langchain.embeddings import HuggingFaceEmbeddings

embedding_model = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
semantic_splitter = SemanticChunker(embedding_model)

chunks = semantic_splitter.split_text(long_text)
