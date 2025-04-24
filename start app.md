gunicorn -w 1 -k uvicorn.workers.UvicornWorker app:app --bind 127.0.0.1:7888

uvicorn app:app --host 127.0.0.1 --port 7888

uvicorn app:app --host 127.0.0.1 --port 7888 --loop asyncio

start /B uvicorn app:app --host 127.0.0.1 --port 7888 --loop asyncio > uvicorn.log 2>&1
tasklist /v | findstr /i uvicorn
taskkill /F /IM python.exe

cd computer_use_ootb && .venv\Scripts\activate && uvicorn app:app --host 127.0.0.1 --port 7888 --loop asyncio
cd computer_use_ootb && .venv\Scripts\activate


setx /M PATH "%PATH%;C:\nssm\win64"



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

curl -X 'POST' 'https://dev-api.via.link/api/llm-agent/job/b5471937-a348-4cae-b99d-ded11e61ea56/upload-output-file' -H 'accept: */*' -H 'Content-Type: multipart/form-data' -F "file=@$FILE_PATH"


{{FileUploadCallbackUrl}} --> API_URL

DOWNLOAD_DIR="/c/Users/Administrator/Downloads"; API_URL="https://dev-api.via.link/api/llm-agent/job/ae4fef85-d2f4-462e-9238-10d4c40bbacb/upload-output-file"; LATEST_FILE=$(ls -t "$DOWNLOAD_DIR" | head -n 1); [ -z "$LATEST_FILE" ] && { echo "No files found in $DOWNLOAD_DIR"; exit 1; }; FILE_PATH="$DOWNLOAD_DIR/$LATEST_FILE"; echo "Uploading file: $FILE_PATH"; curl -X 'POST' "$API_URL" -H 'accept: */*' -H 'Content-Type: multipart/form-data' -F "file=@$FILE_PATH"

DOWNLOAD_DIR="/c/Users/Administrator/Downloads"; API_URL="https://ktkt97kpqa.ap-southeast-1.awsapprunner.com/api/llm-agent/job/ae4fef85-d2f4-462e-9238-10d4c40bbacb/upload-output-file"; LATEST_FILE=$(ls -t "$DOWNLOAD_DIR" | head -n 1); [ -z "$LATEST_FILE" ] && { echo "No files found in $DOWNLOAD_DIR"; exit 1; }; FILE_PATH="$DOWNLOAD_DIR/$LATEST_FILE"; echo "Uploading file: $FILE_PATH"; curl -X 'POST' "$API_URL" -H 'accept: */*' -H 'Content-Type: multipart/form-data' -F "file=@$FILE_PATH"

https://ktkt97kpqa.ap-southeast-1.awsapprunner.com/


{
    "tooluse_log" [
        [
            {
                "FillItemDetailsTool": {'item_barcode': '8ZP0447700100', 'item_qty': '59', 'item_unit': 'EA'}
            }   ### สินค้าพอ
        ],
        [
            {
                "FillItemDetailsTool": {'item_barcode': '8ZP0447700102', 'item_qty': '19', 'item_unit': 'EA'}
            },
            {
                "CreditSalesContinueTool": {}
            }   ### Stock ในระบบไม่พอ
        ],
        [
            {
                "FillItemDetailsTool": {'item_barcode': '8ZP0447700101', 'item_qty': '70', 'item_unit': 'EA'}
            },
            {
                "CreditSalesOneTimeDeliveryTool": {"item_confirm_qty": '29}
            }   ### สินค้าไม่พอ
        ],
        [
            {
                "FillItemDetailsTool": {'item_barcode': '8ZP0447700101', 'item_qty': '70', 'item_unit': 'EA'}
            },
            {
                "ProductAllocationPopupDismissTool": {}
            },
            {
                "CreditSalesContinueTool": {}
            }   ### product allocation แบบ Stock เป็น 0
        ],
        [
            {
                "FillItemDetailsTool": {'item_barcode': '8ZP0447700101', 'item_qty': '70', 'item_unit': 'EA'}
            },
            {
                "ProductAllocationPopupDismissTool": {}
            },
            {
                "CreditSalesOneTimeDeliveryTool": {"item_confirm_qty": '29}
            }   ### product allocation แบบสินค้าไม่พอ
        ],
        [
            {
                "FillItemDetailsTool": {'item_barcode': '8ZP0447700103', 'item_qty': '5', 'item_unit': 'EA'}
            },
            {
                "NotPossibleToDeteminePopupDismissTool": {}
            }   ### หา Material code ในระบบไม่เจอ ไม่สามารถ Mapping ได้
        ],
    ]
}