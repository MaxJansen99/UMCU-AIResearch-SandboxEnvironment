# Voorbeeld Document-Review

Dit voorbeeld is een demo-run/simulatie van de test-agent. Het toont dat de test-agent documentatie kan beoordelen op basis van acceptatiecriteria.

## Input

User story:
Als nieuwe developer wil ik duidelijke startinstructies, zodat ik de UMC Radiologie Query Tool lokaal kan draaien.

Acceptatiecriteria:
1. De documentatie noemt alle benodigde tools.
2. De documentatie bevat een startcommando.
3. De documentatie noemt waar de frontend, backend en Orthanc bereikbaar zijn.
4. De documentatie bevat demo-accounts.

Producttype:
Document

Opgeleverd product:
De README beschrijft dat Docker Desktop nodig is. Starten kan met `docker compose up --build` vanuit `query tool`. De applicatie staat op `http://localhost:3000/login`, de backend op `http://localhost:8000/health` en Orthanc op `http://localhost:8042`. Demo-accounts zijn `researcher_demo` en `datamanager_demo`.

## Output van test-agent

## Eindoordeel
Status: Goedgekeurd met opmerkingen

Korte onderbouwing:
De documentatie bevat de belangrijkste informatie om lokaal te starten. Er ontbreekt nog een korte troubleshooting-stap voor bekende problemen zoals bezette poorten of oude Docker-volumes.

## Controle per acceptatiecriterium
- AC1: Gehaald
  Uitleg: Docker Desktop wordt genoemd als benodigde tool.
- AC2: Gehaald
  Uitleg: Het startcommando `docker compose up --build` staat erin.
- AC3: Gehaald
  Uitleg: Frontend, backend en Orthanc URLs worden genoemd.
- AC4: Gehaald
  Uitleg: De demo-accounts voor researcher en datamanager staan erin.

## Gevonden problemen
- Probleem: Geen troubleshooting bij poortconflicten of oude volumes.
  Impact: Nieuwe developers kunnen vastlopen als er nog lokale data of containers draaien.
  Bewijs of locatie: De opgeleverde tekst noemt alleen de happy flow.

## Risico's
- Risico: Het startcommando werkt alleen vanuit de juiste map.
  Waarom dit relevant is: Als iemand vanuit de repo-root draait, gebruikt die mogelijk de verkeerde compose file.

## Verbetervoorstellen
- Voorstel: Voeg expliciet toe: `cd "C:\dev\UMC\query tool"`.
  Verwacht effect: Minder kans dat de verkeerde Docker Compose-configuratie gestart wordt.
- Voorstel: Voeg een clean-start commando toe: `docker compose down -v`.
  Verwacht effect: Sneller herstel bij corrupte of oude demo-data.

## Advies voor het team
De documentatie is bruikbaar. Voeg nog een korte troubleshooting-paragraaf toe voordat deze definitief als onboardingdocument wordt gebruikt.
