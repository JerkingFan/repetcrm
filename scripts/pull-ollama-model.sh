#!/bin/sh
echo "Pulling qwen2.5:3b model (may take several minutes)..."
docker compose exec ollama ollama pull qwen2.5:3b
echo "Done."
