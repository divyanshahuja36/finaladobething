# download_model.py
from sentence_transformers import SentenceTransformer

# Define the model we want to use
model_name = 'all-MiniLM-L6-v2'
# Define the local path where we want to save it
save_path = './models/all-MiniLM-L6-v2'

print(f"Downloading model: {model_name}...")

# Create a SentenceTransformer model object, which downloads the model
model = SentenceTransformer(model_name)

print(f"Saving model to: {save_path}...")

# Save the model files to the specified local directory
model.save(save_path)

print("Model downloaded and saved successfully!")
