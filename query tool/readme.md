# UMC Radiologie Query Tool PoC

Dit document beschrijft de huidige technische staat van de Query Tool PoC. Gebruik dit als context voor developers of AI agents die willen sparren over het project.

## Doel

De PoC laat zien hoe een onderzoeker DICOM metadata kan doorzoeken, series/scans kan selecteren en een selectie-aanvraag kan indienen bij een datamanager. De datamanager kan aanvragen beoordelen en goedkeuren of afwijzen.

Het project gebruikt lokale/public testdata en draait volledig via Docker Compose.

## Huidige Functionaliteit

### Researcher

- Login met demo researcher account.
- Query/filter DICOM metadata uit Orthanc.
- Filters op o.a. modality, body part/region en study date.
- Resultaten in tabel met checkbox selectie per zichtbare series/scan.
- `All` checkbox selecteert alle resultaten over alle pagina's van de huidige query.
- Selecties blijven onthouden over meerdere zoek/filter-rondes.
- Submit flow:
  1. `POST /requests`
  2. `POST /requests/{id}/items`
  3. `POST /requests/{id}/submit`
- Onderzoeker ziet eigen aanvragen in "Mijn aanvragen".
- Status zichtbaar: `DRAFT`, `SUBMITTED`, `APPROVED`, `REJECTED`.
- Approval/reject reason wordt zichtbaar bij eigen aanvragen.
- Bij goedkeuring wordt een server-side approved export manifest klaargezet.

### Datamanager

- Login met demo datamanager account.
- Ziet alle pending requests van alle researchers.
- Klik op request opent detail view.
- Detail view toont:
  - titel
  - status
  - filters JSON
  - selected studies
  - basic Orthanc study info: date, modality/modalities, description
- Kan request goedkeuren.
- Kan request afwijzen met verplichte reason.
- Na beslissing verdwijnt request uit pending inbox en status wordt opgeslagen.
- Na goedkeuring ziet de datamanager de exportstatus van het manifest.

## Demo Accounts

```text
Researcher
username: researcher_demo
password: researcher_demo

Datamanager
username: datamanager_demo
password: datamanager_demo
```

Wachtwoorden staan niet plain in de database. Ze worden als bcrypt hash opgeslagen.

## Architectuur

De frontend en backend zijn gesplitst in aparte containers.

```text
dicom-frontend
- React frontend
- NGINX static hosting
- bereikbaar op http://localhost:3000
- proxyt /api/* naar dicom-query:8000

dicom-query
- Python backend API
- bereikbaar op http://localhost:8000 voor debug/direct API
- praat met Postgres en Orthanc

dicom-postgres
- PostgreSQL database
- host poort localhost:5433
- container poort 5432

orthanc
- Orthanc PACS
- host poort localhost:8042

dicom-importer
- tijdelijke container
- importeert DICOM files uit ./idc-data naar Orthanc
- stopt daarna
- draait alleen expliciet met profile `import`

test-client
- curl healthcheck container
- draait alleen expliciet met profile `test`
```

## Starten

Vanaf deze map:

```powershell
cd "C:\dev\UMC\query tool"
docker compose up --build
```

Dit start standaard alleen de vaste services: frontend, backend, Postgres en Orthanc.
De DICOM importer en test-client draaien niet standaard mee, zodat normale starts sneller zijn.

Nieuwe of opnieuw gevulde DICOM data importeren:

```powershell
docker compose --profile import up dicom-importer
```

Healthcheck test-client handmatig draaien:

```powershell
docker compose --profile test up test-client
```

Open de applicatie:

```text
http://localhost:3000/login
```

Backend direct debuggen:

```text
http://localhost:8000/health
http://localhost:8000/health/db
```

Orthanc:

```text
http://localhost:8042
username: orthanc
password: orthanc
```

## Docker Compose Services

File:

```text
query tool/docker-compose.yml
```

Belangrijkste services:

```text
frontend       React + NGINX, poort 3000
dicom-query    Python backend API, poort 8000
postgres       PostgreSQL, poort 5433 op host
orthanc        PACS, poort 8042
dicom-importer DICOM import job, profile import
test-client    curl healthcheck, profile test
approved_exports Docker volume met approved exports, DICOM files en manifests
```

Een andere developer heeft lokaal in principe alleen Docker Desktop nodig. Node/npm en Python dependencies worden binnen Docker geinstalleerd.

## Frontend

Pad:

```text
query tool/query/frontend
```

Tech:

```text
React
TypeScript
Vite
Tailwind CSS
shadcn/ui achtige componenten
NGINX container voor production static hosting
```

Belangrijke files:

```text
src/app/App.tsx
- client-side routing
- route guard
- researcher dashboard
- selectie + submit flow
- mijn aanvragen

src/app/components/LoginPage.tsx
- login form
- role-based redirect

src/app/components/DatamanagerPage.tsx
- pending inbox
- detail view
- approve/reject

src/app/components/DynamicFilters.tsx
- filter UI

src/app/components/DynamicTable.tsx
- result table
- row checkboxes
- All checkbox over alle query resultaten

src/app/utils/authClient.ts
- login
- /auth/me
- localStorage token

src/app/utils/queryClient.ts
- /query API client
- backend response mapping naar frontend rows

src/app/utils/requestClient.ts
- /requests workflow API client

Dockerfile
- frontend Docker build

nginx.conf
- serves React dist
- proxies /api/* naar backend
```

Frontend API calls gaan via:

```text
/api/auth/login
/api/auth/me
/api/query
/api/requests/...
```

NGINX verwijdert `/api/` en proxyt naar de backend routes:

```text
/api/auth/login -> dicom-query:8000/auth/login
```

## Backend

Pad:

```text
query tool/query/app
```

Tech:

```text
Python 3.11
http.server / ThreadingHTTPServer
requests voor Orthanc
psycopg voor Postgres
passlib + bcrypt voor password hashing
server-side in-memory bearer sessions
```

Belangrijke files:

```text
app/main.py
- start backend
- initialiseert database
- maakt services aan

app/api/server.py
- HTTP routes
- JSON request/response handling
- auth endpoints
- request workflow endpoints
- /query endpoint
- health endpoints

app/core/config.py
- env vars
- Orthanc config
- Postgres config

app/services/database.py
- Postgres connectie
- schema init
- seed users
- user lookup

app/services/auth.py
- login
- bearer token sessions
- public user response
- require_role helper

app/services/request_workflow.py
- create request
- add selected studies
- submit
- list own requests
- list pending requests
- approve/reject
- status rules

app/services/query_service.py
- query Orthanc metadata
- filter matching
- stats aggregation
- returns matched series

app/services/orthanc_client.py
- HTTP client voor Orthanc
```

## Backend API

Health:

```text
GET /health
GET /health/db
```

Auth:

```text
POST /auth/login
GET  /auth/me
```

Body login:

```json
{
  "username": "researcher_demo",
  "password": "researcher_demo"
}
```

Query:

```text
POST /query
```

Request workflow:

```text
POST /requests
POST /requests/{id}/items
POST /requests/{id}/submit
GET  /requests/mine
GET  /requests/pending
POST /requests/{id}/decision
```

Decision body:

```json
{
  "decision": "APPROVED",
  "reason": "Looks good"
}
```

Reject requires reason:

```json
{
  "decision": "REJECTED",
  "reason": "Missing justification"
}
```

## Authorization Rules

```text
researcher
- can create requests
- can add items to own DRAFT requests
- can submit own DRAFT requests
- can see own request history via /requests/mine

datamanager
- can see all SUBMITTED requests from all researchers
- can approve/reject any SUBMITTED request
```

There is currently no per-datamanager assignment. Every datamanager sees all pending requests.

## Database

Postgres runs in Docker service:

```text
postgres / dicom-postgres
```

Connect:

```powershell
cd "C:\dev\UMC\query tool"
docker compose exec postgres psql -U dicom_query -d dicom_query
```

Tables:

```text
users
selection_requests
selection_items
approvals
```

Schema overview:

```sql
\dt
\d users
\d selection_requests
\d selection_items
\d approvals
```

Useful queries:

```sql
SELECT id, username, role, left(password_hash, 12) AS hash_prefix
FROM users
ORDER BY id;

SELECT id, created_by_user_id, title, status, filters_json, created_at
FROM selection_requests
ORDER BY id;

SELECT id, request_id, orthanc_study_id
FROM selection_items
ORDER BY request_id, id;

SELECT id, request_id, decided_by_user_id, decision, reason, decided_at
FROM approvals
ORDER BY request_id, id;
```

## Data Model

```text
users
- id
- username
- password_hash
- role: researcher | datamanager

selection_requests
- id
- created_by_user_id -> users.id
- title
- status: DRAFT | SUBMITTED | APPROVED | REJECTED
- filters_json
- created_at

selection_items
- id
- request_id -> selection_requests.id
- orthanc_study_id

approvals
- id
- request_id -> selection_requests.id
- decided_by_user_id -> users.id
- decision: APPROVED | REJECTED
- reason
- decided_at

request_exports
- id
- request_id -> selection_requests.id
- request_hash
- reused_from_export_id -> request_exports.id
- status: PENDING | READY | FAILED
- export_path
- manifest_path
- error
- created_at
- updated_at

request_export_items
- id
- export_id -> request_exports.id
- orthanc_study_id
- orthanc_series_id
- orthanc_instance_id
- stored_file
- linked_file
- created_at
```

## Status Flow

```text
DRAFT -> SUBMITTED -> APPROVED
DRAFT -> SUBMITTED -> REJECTED
```

Researchers create DRAFT requests, add selected studies, then submit. Datamanagers only see SUBMITTED requests.

## Approved Exports

Story 9 prepares approved DICOM files after a datamanager approves a request, with hash-based reuse for identical selections.

On approval, the backend:

```text
1. computes request_hash from the selected Orthanc study IDs
2. checks whether a previous READY export exists for the same hash
3. if found, reuses stored files and creates new hardlinks only
4. if not found, resolves studies to series/instances and downloads missing files
5. writes /approved_exports/requests/<request_id>/manifest.json
6. stores export status, request_hash and exported items in Postgres
```

Storage layout:

```text
/approved_exports/
  instances/
    <orthanc_instance_id>.dcm
  requests/
    <request_id>/
      manifest.json
      <orthanc_instance_id>.dcm
```

The manifest contains:

```text
request id
title
approved by
filters_json
selected Orthanc study ids
basic study info
exported instance files
request_hash
reused_from_export_id when cache reuse happened
```

Export status is stored in Postgres table `request_exports` and returned in request API responses as `export`.
Exported files are stored in `request_export_items`.

Inspect from inside the backend container:

```powershell
docker compose exec dicom-query ls /approved_exports/requests
docker compose exec dicom-query ls /approved_exports/instances
docker compose exec dicom-query cat /approved_exports/requests/<request_id>/manifest.json
```

Inspect in Postgres:

```sql
SELECT id, request_id, request_hash, reused_from_export_id, status, export_path, manifest_path, error
FROM request_exports
ORDER BY id;

SELECT export_id, orthanc_study_id, orthanc_series_id, orthanc_instance_id, stored_file, linked_file
FROM request_export_items
ORDER BY export_id, id;
```

## Query Flow

High-level flow:

```text
DynamicFilters.tsx
-> App.tsx handleSearch
-> queryClient.ts queryOrthancMetadata
-> POST /api/query
-> NGINX proxy
-> backend POST /query
-> QueryService
-> Orthanc /tools/find
-> Orthanc /series/{id}
-> optional instance tags
-> backend returns stats + matched_series
-> frontend renders DynamicTable + DynamicStatsPanel
```

## Selection Behavior

The results table shows series/scans rows.

Selection is row-based in the UI:

```text
one checkbox = one visible series/scan row
```

Selections are remembered across filter/search rounds:

```text
select MR rows
clear/apply another filter
select US rows
submit all remembered selections together
```

On submit, the frontend deduplicates selected rows into unique `orthanc_study_id`s before calling:

```text
POST /requests/{id}/items
```

## Demo Flow

Researcher:

```text
1. Open http://localhost:3000/login
2. Login as researcher_demo / researcher_demo
3. Filter metadata, e.g. Modality = MR
4. Select one or more rows
5. Optionally search/filter again and select more rows
6. Fill request title
7. Click Submit for approval
8. Check "Mijn aanvragen"
```

Datamanager:

```text
1. Logout
2. Login as datamanager_demo / datamanager_demo
3. Open /datamanager
4. Click a pending request
5. Inspect filters and selected studies
6. Approve or reject with reason
```

Researcher again:

```text
1. Login as researcher
2. Check "Mijn aanvragen"
3. Status and reason should be visible
```

## Known Notes / Current Limitations

- Sessions are server-side in-memory. Restarting `dicom-query` invalidates login tokens.
- There is no user management UI yet.
- Only two seed users are created automatically.
- Datamanagers see all pending requests; no assignment model exists yet.
- Request history for datamanagers currently focuses on pending inbox, not a full archive UI.
- Frontend bundle is large because the UI dependency set is broad; build warning is known.
- Some smoke-test requests may exist in local Postgres volumes.

Clean local demo data:

```powershell
cd "C:\dev\UMC\query tool"
docker compose down -v
docker compose up --build
```

This deletes Postgres and Orthanc volumes, then rebuilds/reimports everything.

## Ports

```text
3000 frontend
8000 backend direct API/debug
8042 Orthanc
5433 Postgres on host
```

## Commands

Start:

```powershell
cd "C:\dev\UMC\query tool"
docker compose up --build
```

Start sneller zonder rebuild als images al bestaan:

```powershell
docker compose up
```

Run in background:

```powershell
docker compose up -d --build
```

Importeer DICOM data alleen wanneer nodig:

```powershell
docker compose --profile import up dicom-importer
```

Draai de test-client alleen wanneer nodig:

```powershell
docker compose --profile test up test-client
```

Stop:

```powershell
docker compose down
```

Clean stop including volumes:

```powershell
docker compose down -v
```

Check containers:

```powershell
docker compose ps
```

Logs:

```powershell
docker compose logs frontend
docker compose logs dicom-query
docker compose logs postgres
docker compose logs orthanc
```

Frontend checks locally:

```powershell
cd "C:\dev\UMC\query tool\query\frontend"
npm.cmd run typecheck
npm.cmd run build
```

Backend Python compile check:

```powershell
cd "C:\dev\UMC"
.\.venv\Scripts\python.exe -m py_compile "query tool\query\app\main.py"
```
