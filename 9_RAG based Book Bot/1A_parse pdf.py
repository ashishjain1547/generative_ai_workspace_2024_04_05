from openparse import processing, DocumentParser
import json

basic_doc_path = "pdf_doc/8_Find Your Why_Simon Sinek.pdf"

with open("../../../api_keys_in_laptop.json", "r") as f:
    api_keys = json.load(f)


semantic_pipeline = processing.SemanticIngestionPipeline(
    openai_api_key=api_keys['openai'],
    model="text-embedding-3-large",
    min_tokens=64,
    max_tokens=1024,
)
parser = DocumentParser(
    processing_pipeline=semantic_pipeline,
)
parsed_content = parser.parse(basic_doc_path)

import pickle

print("Pickle version:", pickle.format_version)

with open("parsed_content.pickle", "wb") as f:
    pickle.dump(parsed_content, f)
