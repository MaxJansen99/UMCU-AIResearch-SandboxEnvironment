# Voorbeeld Code-Review

Dit voorbeeld is een demo-run/simulatie van de test-agent. Het toont dat de test-agent code kan beoordelen op basis van acceptatiecriteria.

## Input

User story:
Als datamanager wil ik een selectie-aanvraag kunnen goedkeuren of afwijzen, zodat alleen gecontroleerde DICOM-selecties geëxporteerd worden.

Acceptatiecriteria:
1. Een datamanager kan alleen ingediende aanvragen beoordelen.
2. Bij afwijzen is een reden verplicht.
3. Na goedkeuring wordt een exportmanifest aangemaakt.
4. De onderzoeker kan de status en reden terugzien.

Producttype:
Code

Opgeleverd product:

```python
def decide_request(request_id, decision, reason=None):
    if decision == "REJECTED" and not reason:
        raise ValueError("Reject reason is required")

    request = repository.get_request(request_id)
    if request["status"] != "SUBMITTED":
        raise ValueError("Only submitted requests can be decided")

    repository.store_decision(request_id, decision, reason)

    if decision == "APPROVED":
        export_service.prepare_export(request_id)
```

## Output van test-agent

## Eindoordeel
Status: Goedgekeurd met opmerkingen

Korte onderbouwing:
De belangrijkste workflowregels zijn aanwezig: alleen `SUBMITTED` aanvragen worden beoordeeld, afwijzen vereist een reden en goedkeuren start exportvoorbereiding. Niet alle acceptatiecriteria zijn volledig aantoonbaar vanuit dit fragment, vooral het terugzien van status en reden door de onderzoeker.

## Controle per acceptatiecriterium
- AC1: Gehaald
  Uitleg: De code controleert expliciet dat de status `SUBMITTED` is.
- AC2: Gehaald
  Uitleg: Bij `REJECTED` zonder reden wordt een fout gegooid.
- AC3: Gehaald
  Uitleg: Bij `APPROVED` wordt `export_service.prepare_export(request_id)` aangeroepen.
- AC4: Deels gehaald
  Uitleg: De beslissing wordt opgeslagen, maar dit fragment toont niet of de onderzoeker status en reden kan ophalen.

## Gevonden problemen
- Probleem: Geen autorisatiecontrole zichtbaar.
  Impact: Zonder rolcontrole zou een niet-datamanager mogelijk een aanvraag kunnen beoordelen.
  Bewijs of locatie: In het fragment wordt geen gebruiker of rol meegegeven.

## Risico's
- Risico: Exportfouten worden niet zichtbaar afgehandeld.
  Waarom dit relevant is: Als `prepare_export` faalt, is onduidelijk of de aanvraag alsnog als approved opgeslagen blijft.

## Verbetervoorstellen
- Voorstel: Voeg een expliciete `require_role(user, "datamanager")` controle toe voor de beslissing.
  Verwacht effect: Voorkomt dat researchers of anonieme gebruikers aanvragen kunnen beoordelen.
- Voorstel: Voeg tests toe voor goedkeuren, afwijzen zonder reden en beslissen op een `DRAFT` request.
  Verwacht effect: Borgt de belangrijkste acceptatiecriteria automatisch.

## Advies voor het team
Controleer de API-route waar deze functie wordt aangeroepen op autorisatie en voeg tests toe voor de statusovergangen. Daarna kan deze taak naar Done.
