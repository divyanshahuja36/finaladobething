#!/bin/bash
# Build the Docker image and run analysis on a collection.
# Usage:
#   ./run.sh "Collection 1"         # fresh build
#   ./run.sh "Collection 1" --cache # reuse build cache

set -e

IMAGE="adobe-hackathon-solution"
COL="$1"               # collection directory
[[ -z "$COL" ]] && { echo "Usage: $0 \"Collection X\" [--cache]"; exit 1; }
[[ -d "$COL" ]] || { echo "Directory '$COL' not found"; exit 1; }

# sanity-check collection contents
for f in challenge1b_input.json PDFs; do
  [[ -e "$COL/$f" ]] || { echo "Missing '$f' in $COL"; exit 1; }
done

CACHE="" # Use cache by default
if [[ "$2" == "--fresh" ]]; then
CACHE="--no-cache"
fi

echo "▶ Building Docker image…"
docker build $CACHE --platform linux/amd64 -t "$IMAGE" .

echo "▶ Running analysis on '$COL'…"
START=$(date +%s)
docker run --rm --platform linux/amd64 \
  --memory 2g --cpus 2.0 --network none \
  -v "$(pwd)/$COL":/app/data:ro \
  "$IMAGE" python src/main.py /app/data
END=$(date +%s)

OUT="$COL/challenge1b_output.json"
if [[ -f "$OUT" ]]; then
  echo "Output: $OUT   (elapsed $((END-START)) s)"
else
  echo "Analysis completed but output file missing"
fi

