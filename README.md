# UMC Radiologie Query Tool PoC

Actuele projectdocumentatie voor de UMC Radiologie Query Tool proof of concept.

De oude Docker Registry sandbox-documentatie is vervangen door deze README, omdat de repository nu draait om de Query Tool PoC. De test-agent documentatie staat apart in `query tool/test-agent/README.md` en is bewust niet samengevoegd.

## Doel

De applicatie laat zien hoe onderzoekers DICOM-metadata kunnen doorzoeken, resultaten kunnen filteren, studies/series kunnen selecteren en een selectie-aanvraag kunnen indienen bij een datamanager. De datamanager kan aanvragen beoordelen, goedkeuren of afwijzen.

De querylaag ondersteunt meerdere databronnen:

- Orthanc/PACS als primaire bron.
- CSV als fallback of demo/testbron.
- Auto mode: eerst Orthanc proberen, daarna CSV als fallback.

De frontend blijft hetzelfde werken, ongeacht of de querydata uit Orthanc of CSV komt.

## Demo Accounts

```text
Researcher
username: researcher_demo
password: researcher_demo

Datamanager
username: datamanager_demo
password: datamanager_demo
```

Wachtwoorden worden als bcrypt hash opgeslagen in Postgres.

## Snel Starten

Vanaf de repository root:

```powershell
cd "C:\dev\UMC\query tool"
docker compose up --build
```

Open daarna:

```text
Frontend: http://localhost:3000/login
Backend health: http://localhost:8000/health
Database health: http://localhost:8000/health/db
Orthanc: http://localhost:8042
```

Orthanc login:

```text
username: orthanc
password: orthanc
```

## Docker Services

De Docker Compose file staat in:

```text
query tool/docker-compose.yml
```

Belangrijkste containers:

```text
dicom-frontend   React frontend via NGINX, host poort 3000
dicom-query      Python backend API, host poort 8000
dicom-postgres   PostgreSQL database, host poort 5433
orthanc          Orthanc PACS, host poort 8042
dicom-importer   optionele DICOM import job, profile import
test-client      optionele curl healthcheck, profile test
```

Normaal starten:

```powershell
docker compose up --build
```

Starten zonder rebuild:

```powershell
docker compose up
```

Stoppen:

```powershell
docker compose down
```

Alles resetten inclusief volumes:

```powershell
docker compose down -v
docker compose up --build
```

## Databronnen Voor Query

De backend kiest de querybron via environment variables.

```text
QUERY_DATA_SOURCE=orthanc  # alleen Orthanc/PACS
QUERY_DATA_SOURCE=csv      # alleen CSV
QUERY_DATA_SOURCE=auto     # Orthanc eerst, CSV fallback bij fout
QUERY_CSV_FILE=/csv/metadata.csv
```

In Docker Compose wordt `/csv` gemount vanaf:

```text
query tool/csv-data
```

Voor CSV mode:

```powershell
cd "C:\dev\UMC\query tool"
mkdir csv-data
# plaats metadata.csv in csv-data
docker compose up --build
```

De CSV-loader accepteert DICOM-achtige kolomnamen en logische aliases, bijvoorbeeld:

```text
Modality / modality
StudyDate / study_date / date
BodyPartExamined / body_part_examined / body_part / bodypart
PatientBirthDate / patient_birth_date / birth_date / date_of_birth
PatientSex / patient_sex / sex / gender
StudyInstanceUID / study_instance_uid / study_uid
SeriesInstanceUID / series_instance_uid / series_uid
Images / images / instances / instance_count
```

CSV-data wordt intern omgezet naar een Orthanc-achtig querymodel met dezelfde responsevelden voor de frontend:

```text
matched_series
stats
match_count
total_series_found
total_instances
source
source_info
```

Belangrijke beperking: CSV ondersteunt zoeken, filteren en resultaten tonen, maar levert geen DICOM instance files voor approved exports. De request/exportflow blijft Orthanc-gebaseerd.

## Frontend Functionaliteit

Researcher:

- Login met researcher account.
- DICOM-metadata zoeken en filteren via dezelfde querytool voor Orthanc en CSV.
- Filtersecties voor Modality, Body Part, Study Date en Patient.
- Modality blijft standaard open; andere filtersecties zijn inklapbaar.
- Resetoptie per filtersectie.
- Active filter chips zijn verwijderbaar met een kruisje.
- Age ondersteunt meerdere zelfgekozen leeftijdsranges.
- Study Date ondersteunt meerdere zelfgekozen datumranges.
- Body Part wordt dynamisch gevuld vanuit beschikbare data.
- Body Part is alfabetisch gesorteerd en doorzoekbaar.
- Lege bodypart-waarden worden alleen als `Unknown` getoond als ze echt in de data voorkomen.
- Resultaten staan in een tabel met selectie-checkboxes.
- Selecties blijven onthouden over filter/search rondes.
- Onderzoeker kan een aanvraag indienen en eigen aanvragen volgen via "Mijn aanvragen".

Datamanager:

- Login met datamanager account.
- Ziet pending aanvragen van researchers.
- Kan details bekijken: titel, status, filters, selected studies en basis metadata.
- Kan aanvragen goedkeuren of afwijzen.
- Afwijzen vereist een reden.
- Na goedkeuring wordt een server-side approved export manifest voorbereid.

## Frontend Code

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
lucide-react icons
NGINX static hosting in Docker
```

Belangrijke files:

```text
src/app/App.tsx
- route guard
- researcher dashboard
- filter state naar query mapping
- selectie en submit flow
- mijn aanvragen

src/app/components/DynamicFilters.tsx
- filter UI
- reset/chips
- multiple Age ranges
- multiple Study Date ranges
- dynamische BodyPart filter

src/app/components/DynamicTable.tsx
- result table
- row selectie

src/app/components/DatamanagerPage.tsx
- pending inbox
- detail view
- approve/reject flow

src/app/utils/queryClient.ts
- /query API client
- frontend filters naar backend filters
- response mapping naar frontend rows

src/app/utils/requestClient.ts
- request workflow API client
```

Frontend API calls lopen via NGINX:

```text
/api/auth/login    -> backend /auth/login
/api/auth/me       -> backend /auth/me
/api/query         -> backend /query
/api/requests/...  -> backend /requests/...
```

## Backend Functionaliteit

Pad:

```text
query tool/query/app
```

Tech:

```text
Python 3.11
ThreadingHTTPServer
requests voor Orthanc
psycopg voor Postgres
passlib + bcrypt voor password hashing
server-side in-memory bearer sessions
```

Belangrijke files:

```text
app/main.py
- start backend
- bouwt datasource: orthanc, csv of auto
- initialiseert database en services

app/core/config.py
- environment configuratie
- QUERY_DATA_SOURCE
- QUERY_CSV_FILE
- Orthanc en Postgres settings

app/api/server.py
- HTTP routes
- JSON request/response
- auth endpoints
- query endpoint
- request workflow endpoints

app/services/query_service.py
- query uitvoeren op gekozen datasource
- filter matching
- stats aggregatie
- frontend-compatible response

app/services/orthanc_client.py
- Orthanc HTTP client

app/services/csv_data_source.py
- CSV inlezen
- tolerante kolommapping
- CSV naar Orthanc-achtig metadata model
- CSV-validatie en waarschuwingen

app/services/fallback_data_source.py
- auto mode fallback van Orthanc naar CSV

app/services/request_workflow.py
- create request
- add selected studies
- submit
- list mine/pending
- approve/reject
- statusregels

app/services/export_service.py
- approved export manifest
- DICOM file export vanuit Orthanc
- hash-based reuse voor identieke exports
- RFS-ready delivery naar een gebruiker-specifieke map na datamanager approval
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

Query:

```text
POST /query
```

Voorbeeld query body:

```json
{
  "filters": [
    ["Modality", "in", ["MR"]]
  ],
  "stats_tags": ["Modality", "StudyDate", "BodyPartExamined", "PatientSex", "PatientBirthDate"]
}
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
  "reason": "Akkoord"
}
```

Reject body:

```json
{
  "decision": "REJECTED",
  "reason": "Onderbouwing ontbreekt"
}
```

## Database

Postgres draait in Docker service `postgres` met containernaam `dicom-postgres`.

Connect via terminal:

```powershell
cd "C:\dev\UMC\query tool"
docker compose exec postgres psql -U dicom_query -d dicom_query
```

Connect via database tool vanaf host:

```text
Type: PostgreSQL
Host: localhost
Port: 5433
Database: dicom_query
Username: dicom_query
Password: dicom_query
```

Tabellen:

```text
users
selection_requests
selection_items
approvals
request_exports
request_export_items
```

Kernmodel:

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

Handige queries:

```sql
SELECT id, username, role FROM users ORDER BY id;

SELECT id, created_by_user_id, title, status, filters_json, created_at
FROM selection_requests
ORDER BY id;

SELECT id, request_id, orthanc_study_id
FROM selection_items
ORDER BY request_id, id;

SELECT id, request_id, decided_by_user_id, decision, reason, decided_at
FROM approvals
ORDER BY request_id, id;

SELECT id, request_id, request_hash, reused_from_export_id, status, export_path, manifest_path, error
FROM request_exports
ORDER BY id;
```

## Status Flow

```text
DRAFT -> SUBMITTED -> APPROVED
DRAFT -> SUBMITTED -> REJECTED
```

Researchers maken DRAFT requests, voegen selected studies toe en submitten daarna. Datamanagers zien alleen SUBMITTED requests in de pending inbox.

## Approved Exports

Na approval probeert de backend approved DICOM files klaar te zetten vanuit Orthanc.

Proces:

```text
1. bereken request_hash op basis van selected Orthanc study IDs
2. check of een READY export met dezelfde hash bestaat
3. hergebruik bestaande files via links wanneer mogelijk
4. download anders DICOM instances vanuit Orthanc
5. schrijf manifest.json onder /approved_exports/requests/<request_id>
6. bereid een RFS-ready kopie/link voor onder de gebruiker-specifieke map
7. sla exportstatus en export items op in Postgres
```

Storage layout in container:

```text
/approved_exports/
  instances/
    <orthanc_instance_id>.dcm
  requests/
    <request_id>/
      manifest.json
      <orthanc_instance_id>.dcm
  rfs/
    <researcher_username>/
      request_<request_id>/
        study_<orthanc_study_id>/
          A_ShortDescription/
          B_Documentation/
          C_PersonalData/
          D_DataPreparation/
          E_ResearchData/
            manifest.json
            <orthanc_instance_id>.dcm
          F_DataAnalysis/
          G_Output/
          H_Hidden/
```

Bij opnieuw uitvoeren van dezelfde request wordt de RFS-ready `request_<request_id>` map opnieuw opgebouwd. Voor nu worden alleen `E_ResearchData` mappen gevuld; de overige RFS-studiemappen worden leeg aangemaakt.

De prototype RFS-mapping staat in:

```text
query tool/query/app/config/rfs_folders.yml
```

Voorbeeld:

```yaml
researcher_demo:
  folder: researcher_demo
```

Er staat ook een uitgebreid voorbeeldbestand voor latere echte gebruikers/projectmappen:

```text
query tool/query/app/config/rfs_folders.example.yml
```

De backend leest deze mapping via:

```text
RFS_EXPORT_ROOT=/approved_exports/rfs
RFS_FOLDER_MAP_FILE=/app/app/config/rfs_folders.yml
RFS_REQUIRE_EXPLICIT_MAPPING=true
```

Dit is bewust een veilige prototype-inrichting: er wordt niet automatisch naar een echte externe RFS gepusht. De datamanager-approval is de HITL-stap; pas daarna wordt de RFS-ready map binnen de approved export volume voorbereid. Voor RFS/Samba staat expliciete user-folder mapping standaard aan, zodat de backend niet per ongeluk naar een ongecontroleerde fallbackmap schrijft.

Wanneer technisch cluster een echte Samba share beschikbaar maakt, moet die share eerst op de Docker-host worden gemount, bijvoorbeeld op `/mnt/rfs`. Daarna kan de backend die mount gebruiken via een Docker volume. Er staat een voorbeeld override in:

```text
query tool/docker-compose.rfs-example.yml
```

De querytool beheert dus geen Samba credentials en mount de share niet zelf. De applicatie verwacht alleen dat `/rfs` in de container naar de juiste servermap wijst.

Inspecteren:

```powershell
docker compose exec dicom-query ls /approved_exports/requests
docker compose exec dicom-query ls /approved_exports/instances
docker compose exec dicom-query cat /approved_exports/requests/<request_id>/manifest.json
```

Let op: dit exportdeel is afhankelijk van Orthanc en is nog niet bron-onafhankelijk voor CSV.

## Demo Flow

Researcher:

```text
1. Open http://localhost:3000/login
2. Login als researcher_demo
3. Filter metadata, bijvoorbeeld Modality = MR
4. Gebruik eventueel BodyPart search, Age ranges of Study Date ranges
5. Selecteer een of meer rows
6. Vul een aanvraag titel in
7. Klik Submit for approval
8. Controleer status in "Mijn aanvragen"
```

Datamanager:

```text
1. Logout
2. Login als datamanager_demo
3. Open /datamanager
4. Klik een pending request
5. Bekijk filters en selected studies
6. Approve of reject met reden
```

## Tests En Checks

Frontend:

```powershell
cd "C:\dev\UMC\query tool\query\frontend"
npm.cmd run typecheck
npm.cmd run build
```

Backend compile check:

```powershell
cd "C:\dev\UMC"
.\.venv\Scripts\python.exe -m py_compile "query tool\query\app\main.py"
```

Functionele checks die gebruikt zijn:

```text
Orthanc mode: QUERY_DATA_SOURCE=orthanc, querytool gebruikt Orthanc.
CSV mode: QUERY_DATA_SOURCE=csv, querytool gebruikt metadata.csv.
Auto mode: QUERY_DATA_SOURCE=auto, Orthanc eerst en CSV fallback bij bronfout.
Filter UI: reset per sectie, verwijderbare chips, multiple Study Date ranges.
BodyPart: dynamische waarden, alfabetisch en doorzoekbaar.
```

## Ports

```text
3000 frontend
8000 backend direct API/debug
8042 Orthanc
5433 Postgres op host
```

## Huidige Beperkingen

- Sessions zijn server-side in-memory. Restart van `dicom-query` maakt login tokens ongeldig.
- Er is nog geen user management UI.
- Alleen demo users worden automatisch aangemaakt.
- Datamanagers zien alle pending requests; er is geen assignment model.
- Datamanager history is nog geen volledige archive UI.
- CSV ondersteunt query/filter/resultaten, maar geen DICOM instance download/export.
- Approved export is afhankelijk van Orthanc en moet voor echte UMC-infra nog afgestemd worden.
- RFS-delivery is een lokaal prototypepad binnen `/approved_exports/rfs`; echte RFS-mounts en CI/CD approvals moeten nog apart worden ontworpen.
- Frontend build geeft een bekende Vite chunk-size warning door de brede UI dependency set.
- Er kunnen lokale smoke-test aanvragen in Postgres volumes blijven staan.

## Test-Agent

De test-agent documentatie staat apart en is niet samengevoegd:

```text
query tool/test-agent/README.md
```

Deze map hoort bij de Sprint 5 test/review/verify werkwijze.
