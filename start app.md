gunicorn -w 1 -k uvicorn.workers.UvicornWorker app:app --bind 127.0.0.1:7888

uvicorn app:app --host 127.0.0.1 --port 7888

uvicorn app:app --host 127.0.0.1 --port 7888 --loop asyncio



#!/bin/bash

# Set your Downloads folder path.
# For Windows using WSL or Git Bash, the path may look like:
DOWNLOAD_DIR="/c/Users/Administrator/Downloads"  # <-- Replace 'YourUsername' with your actual username

# Define your API endpoint URL.
API_URL="http://example.com/upload"  # <-- Replace with your API endpoint

# Find the latest modified file in the Downloads folder.
LATEST_FILE=$(ls -t "$DOWNLOAD_DIR" | head -n 1)

# Check if a file was found.
if [ -z "$LATEST_FILE" ]; then
    echo "No files found in $DOWNLOAD_DIR"
    exit 1
fi

# Create the full file path.
FILE_PATH="$DOWNLOAD_DIR/$LATEST_FILE"
echo "Uploading file: $FILE_PATH"

# Use cURL to upload the file via a POST request.
curl -X POST -F "file=@$FILE_PATH" "$API_URL"

# Optionally, add authentication or additional fields:
# curl -X POST -H "Authorization: Bearer YOUR_TOKEN" -F "file=@$FILE_PATH" -F "param=value" "$API_URL"


DOWNLOAD_DIR="/c/Users/Administrator/Downloads"; API_URL="http://example.com/upload"; LATEST_FILE=$(ls -t "$DOWNLOAD_DIR" | head -n 1); [ -z "$LATEST_FILE" ] && { echo "No files found in $DOWNLOAD_DIR"; exit 1; }; FILE_PATH="$DOWNLOAD_DIR/$LATEST_FILE"; echo "Uploading file: $FILE_PATH";
