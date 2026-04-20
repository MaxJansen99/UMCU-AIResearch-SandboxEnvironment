# DICOM Datamanager

Asynchronous DICOM image review and preparation service for machine learning training.

## Overview

The datamanager accepts requests for DICOM instances, allows review and approval via an approver interface, then prepares the data:
- Checks `depersonalized_data/instances/` for existing files
- Fetches missing instances from PACS and stores them
- Creates a request folder with hardlinks to avoid duplicate storage

## Quick Start

### 1. Start services

```bash
docker compose up --build -d
```

Verify services are running:
```bash
curl http://localhost:8001/health
```

### 2. Query and collect instance IDs

Query the DICOM query service to find instances:

```bash
curl -k -X POST https://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "filters": [["Modality", "==", "MR"]],
    "stats_tags": ["Modality", "Manufacturer"]
  }' | jq .
```

Example response excerpt:
```json
{
  "instances": [
    {
      "id": "01b64ace-3149-4705-8eac-17b127a0822e",
      "series_id": "series-123",
      "uid": "1.2.840.10008.1.1",
      "name": "Instance 1"
    },
    {
      "id": "0541ac73-4b34-4213-a8a2-a85a4a111817",
      "series_id": "series-124",
      "uid": "1.2.840.10008.1.2",
      "name": "Instance 2"
    }
  ]
}
```

### 3. Create a review request

Submit your email and the instance IDs you want:

```bash
curl -X POST http://localhost:8001/review \
  -H "Content-Type: application/json" \
  -d '{
    "userID": "researcher@university.edu",
    "instance_ids": [
      "01b64ace-3149-4705-8eac-17b127a0822e",
      "0541ac73-4b34-4213-a8a2-a85a4a111817"
    ]
  }'
```

Response:
```json
{
  "ok": true,
  "message": "Request received and pending review.",
  "request_hash": "abc123def456..."
}
```

Save the `request_hash` for the next step.

### 4. View pending requests

Approvers can see all pending and processed requests:

```bash
# View all requests
curl http://localhost:8001/requests | jq .

# View only pending requests
curl "http://localhost:8001/requests?status=pending" | jq .
```

Example response:
```json
{
  "ok": true,
  "requests": [
    {
      "user_id": "researcher@university.edu",
      "request_hash": "abc123def456...",
      "requested_images": ["01b64ace...", "0541ac73..."],
      "status": "pending",
      "created_at": 1713072000.0,
      "processed_by": null,
      "decision_message": null,
      "processed_at": null,
      "instances": null
    }
  ]
}
```

### 5. Approve or reject

Approvers make a decision on the request:

**Accept:**
```bash
curl -X POST http://localhost:8001/review/decision \
  -H "Content-Type: application/json" \
  -d '{
    "request_hash": "abc123def456...",
    "decision": "accept",
    "message": "Approved for training dataset",
    "processed_by": "admin@university.edu"
  }'
```

**Reject:**
```bash
curl -X POST http://localhost:8001/review/decision \
  -H "Content-Type: application/json" \
  -d '{
    "request_hash": "abc123def456...",
    "decision": "reject",
    "message": "Sensitive PHI identified",
    "processed_by": "admin@university.edu"
  }'
```

Response:
```json
{
  "ok": true,
  "status": "accepted",
  "request_hash": "abc123def456...",
  "instances": [
    {
      "instance_id": "01b64ace-3149-4705-8eac-17b127a0822e",
      "stored_file": "/depersonalized/instances/01b64ace-3149-4705-8eac-17b127a0822e.dcm",
      "linked_file": "/depersonalized/requests/abc123.../01b64ace-3149-4705-8eac-17b127a0822e.dcm"
    }
  ]
}
```

## Email Setup

To enable email notifications, create a `.env` file in the project root:

```env
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
```

### Gmail Setup
1. Enable 2-Factor Authentication
2. Generate an app password at https://myaccount.google.com/apppasswords
3. Use the 16-character password as `SMTP_PASSWORD`

## API Endpoints

### GET /health
Health check endpoint.

**Response:**
```json
{
  "ok": true,
  "service": "dicom-datamanager"
}
```

### GET /requests
List all stored requests (pending, accepted, rejected).

**Query Parameters:**
- `status` (optional): Filter by status (`pending`, `accepted`, `rejected`, `failed`). If omitted, returns all requests.

**Examples:**
```bash
# Get all requests
curl http://localhost:8001/requests | jq .

# Get only pending requests
curl "http://localhost:8001/requests?status=pending" | jq .

# Get only accepted requests
curl "http://localhost:8001/requests?status=accepted" | jq .

# Get only rejected requests
curl "http://localhost:8001/requests?status=rejected" | jq .
```

**Response:**
```json
{
  "ok": true,
  "requests": [...]
}
```

### POST /review
Create a new review request.

**Request body:**
```json
{
  "userID": "user@example.com",
  "instance_ids": ["id1", "id2"],
  "uids": [],
  "ids": [],
  "requested_ids": []
}
```

At least one of `instance_ids`, `uids`, `ids`, or `requested_ids` must be present as a list of strings.

**Response:**
```json
{
  "ok": true,
  "message": "Request received and pending review.",
  "request_hash": "sha256_hash"
}
```

### POST /review/decision
Approve or reject a pending request.

**Request body:**
```json
{
  "request_hash": "sha256_hash",
  "decision": "accept|reject",
  "message": "optional message",
  "processed_by": "approver@example.com"
}
```

**Response (accept):**
```json
{
  "ok": true,
  "status": "accepted",
  "request_hash": "...",
  "instances": [...]
}
```

**Response (reject):**
```json
{
  "ok": true,
  "status": "rejected"
}
```

## Storage Layout

```
depersonalized_data/
├── instances/                          # Depersonalized DICOM files
│   ├── 01b64ace-3149-4705-8eac-17b127a0822e.dcm
│   ├── 0541ac73-4b34-4213-a8a2-a85a4a111817.dcm
│   └── ...
├── requests/                           # Request-specific hardlinks
│   ├── abc123def456.../
│   │   ├── 01b64ace-3149-4705-8eac-17b127a0822e.dcm -> ../../../instances/01b64ace...
│   │   └── 0541ac73-4b34-4213-a8a2-a85a4a111817.dcm -> ../../../instances/0541ac73...
│   └── ...
└── records.json                        # Request audit log
```

## Request Record Structure

```json
{
  "user_id": "researcher@university.edu",
  "request_hash": "sha256_hash_of_sorted_ids",
  "requested_images": ["id1", "id2"],
  "status": "pending|accepted|rejected|failed",
  "created_at": 1713072000.0,
  "processed_by": "approver@example.com",
  "decision_message": "Approved for training",
  "processed_at": 1713078000.0,
  "instances": [
    {
      "instance_id": "id1",
      "stored_file": "/path/to/stored/id1.dcm",
      "linked_file": "/path/to/request/id1.dcm"
    }
  ],
  "request_folder": "/depersonalized/requests/hash/",
  "error": null
}
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATAMANAGER_PORT` | 8001 | Service port |
| `DATAMANAGER_HOST` | 0.0.0.0 | Bind address |
| `DATAMANAGER_PACS_URL` | http://orthanc:8042 | PACS server URL |
| `DATAMANAGER_PACS_USER` | orthanc | PACS username |
| `DATAMANAGER_PACS_PASSWORD` | orthanc | PACS password |
| `DEPERSONALIZED_ROOT` | /depersonalized | Storage root directory |
| `RECORDS_FILE` | /depersonalized/records.json | Request records file |
| `SMTP_SERVER` | smtp.gmail.com | Email server |
| `SMTP_PORT` | 587 | Email server port |
| `SMTP_USER` | - | Email username (required for email) |
| `SMTP_PASSWORD` | - | Email password (required for email) |