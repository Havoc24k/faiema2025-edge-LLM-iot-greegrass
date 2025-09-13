#!/usr/bin/env python3

import os
import logging

try:
    from transformers import AutoTokenizer, AutoModelForCausalLM
except ImportError:
    print("Transformers library not available. Install with: pip install transformers")
    AutoTokenizer = None
    AutoModelForCausalLM = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def download_model():
    """Download and cache the TinyLlama model for offline use"""
    
    if AutoTokenizer is None or AutoModelForCausalLM is None:
        logger.error("Transformers library not available. Inference will run in mock mode.")
        return
    
    model_name = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
    cache_dir = "/greengrass/v2/packages/artifacts/com.edge.llm.InferenceEngine/1.0.0/models/TinyLlama-1.1B-Chat"
    
    os.makedirs(cache_dir, exist_ok=True)
    
    try:
        logger.info(f"Downloading model: {model_name}")
        
        # Download tokenizer
        tokenizer = AutoTokenizer.from_pretrained(
            model_name,
            cache_dir=cache_dir
        )
        tokenizer.save_pretrained(cache_dir)
        
        # Download model
        model = AutoModelForCausalLM.from_pretrained(
            model_name,
            cache_dir=cache_dir,
            torch_dtype="auto"
        )
        model.save_pretrained(cache_dir)
        
        logger.info(f"Model downloaded successfully to {cache_dir}")
        
    except Exception as e:
        logger.error(f"Failed to download model: {e}")
        logger.info("Inference will run in mock mode without actual model")

if __name__ == "__main__":
    download_model()