#!/usr/bin/env python3
"""Download Qwen2.5-Coder-7B model for offline use"""

from transformers import AutoTokenizer, AutoModelForCausalLM
import torch
import os
import shutil

model_name = "Qwen/Qwen2.5-Coder-7B-Instruct"
save_path = "./model_artifacts/qwen2.5-coder-7b"

print(f"Downloading {model_name}...")
print("This will take a while (model is ~15GB)...")

# Create directory
os.makedirs(save_path, exist_ok=True)

# Download tokenizer
print("Downloading tokenizer...")
tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
tokenizer.save_pretrained(save_path)

# Download model
print("Downloading model...")
model = AutoModelForCausalLM.from_pretrained(
    model_name,
    torch_dtype=torch.float16,
    trust_remote_code=True
)

# Save model
print(f"Saving model to {save_path}...")
model.save_pretrained(save_path)

print(f"Model saved successfully to {save_path}")
print(f"Size: {shutil.disk_usage(save_path).used / (1024**3):.2f} GB")