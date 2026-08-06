           ^^^^^^^^^^^^^^^^^^^
  File "/home/jain/anaconda3/envs/myenv/lib/python3.12/site-packages/huggingface_hub/file_download.py", line 1591, in get_hf_file_metadata
    response = _httpx_follow_relative_redirects_with_backoff(
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/jain/anaconda3/envs/myenv/lib/python3.12/site-packages/huggingface_hub/utils/_http.py", line 692, in _httpx_follow_relative_redirects_with_backoff
    hf_raise_for_status(response)
  File "/home/jain/anaconda3/envs/myenv/lib/python3.12/site-packages/huggingface_hub/utils/_http.py", line 781, in hf_raise_for_status
    raise _format(RemoteEntryNotFoundError, message, response, repo_type=repo_type, repo_id=repo_id) from e
huggingface_hub.errors.RemoteEntryNotFoundError: 404 Client Error. (Request ID: Root=1-6a5ca376-041e2b740b519d2d5938e6c4;676c66cc-dd18-490b-abea-da75408d053d)

Entry Not Found for url: https://huggingface.co/prism-ml/Bonsai-27B-gguf/resolve/main/bonsai-27b-Q1_K_M.gguf.