import pickle
import json

import sys
print("Python version:", sys.version)
# Python version: 3.9.21 | packaged by conda-forge | (main, Dec  5 2024, 13:51:40) 

print("Pickle version:", pickle.format_version) # 4.0 dated 20250323

with open('parsed_content_20250323.pickle', 'rb') as f:
    parsed_content = pickle.load(f)

# print(parsed_content)

parsed_dict = None

# other ways to dump the object

# 1. dill
import dill
with open('2_out/parsed_content_20250323.dill', 'wb') as f:
    dill.dump(parsed_content, f)

# 2. yaml
import yaml
with open('2_out/parsed_content_20250323.yaml', 'w') as f:
    yaml.dump(parsed_content, f)


# load the dill object
with open('2_out/parsed_content_20250323.dill', 'rb') as f:
    parsed_content_dill = dill.load(f)

# load the yaml object
with open('2_out/parsed_content_20250323.yaml', 'r') as f:
    parsed_content_yaml = yaml.load(f, Loader=yaml.FullLoader)
