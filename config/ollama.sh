#!/bin/bash
# Ollama configuration for MacBook Pro M5 Pro
# Source this file before running Ollama to enable optimizations

# Enable MLX backend (Apple Silicon optimized)
export OLLAMA_MLX=1

# Keep model resident in memory (avoid reload overhead)
export OLLAMA_KEEP_ALIVE=-1

# Set number of threads (M5 Pro has 12 cores)
export OLLAMA_NUM_THREAD=10

# Increase context window for long-form evidence
export OLLAMA_NUM_PREDICT=4096

echo "✓ Ollama M5 Pro optimizations enabled"
echo "  - MLX backend (faster inference)"
echo "  - Model persistence (avoid reload)"
echo "  - Thread count: 10"
echo "  - Context window: 4096 tokens"
