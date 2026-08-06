# ROLE

Expert AI Developer

# TASK

Write code to generate embeddings for some text data

# INPUT

SQLite DB: /home/jain/Desktop/ws/public/generative_ai_workspace_2024_04_05/14_topic_classification_of_blog_posts_using_sqlite-vector/link_to_blog (20260703_0755).db

Table Name: blog_posts

Column to vectorize: original_text

# MODEL

RUN DIFFERENT, MULTIPLE MODELS FROM HUGGINGFACE
- THAT I CAN LATER COMPARE AND EVALUATE

# CODE SPEC

- Use HuggingFace's Python package

# STORE THE EMBEDDINGS BACK TO DB 

Store the embedding back to DB:
SQLite DB: /home/jain/Desktop/ws/public/generative_ai_workspace_2024_04_05/14_topic_classification_of_blog_posts_using_sqlite-vector/link_to_blog (20260703_0755).db


NEW COLUMN NAMES: <model_name>_<dim_size>

Using this extension called SQLite-Vector:

/home/jain/Desktop/cupboard/program_files/vector-linux-x86_64-1.0.0/vector.so

Read Docs: https://github.com/sqliteai/sqlite-vector

# CODE FILE TO EDIT

/home/jain/Desktop/ws/public/generative_ai_workspace_2024_04_05/14_topic_classification_of_blog_posts_using_sqlite-vector/1_generate_and_store_vector_embeddings.ipynb

# SOME DEPENDENCIES THAT I HAVE INSTALLED

## torch

$ python -c "import torch; print(torch.__version__)"
2.12.1+cpu

## transformers

$ python -c "import transformers; print(transformers.__version__)"
5.12.1

## sentence_transformers

$ python -c "import sentence_transformers; print(sentence_transformers.__version__)"
5.6.0