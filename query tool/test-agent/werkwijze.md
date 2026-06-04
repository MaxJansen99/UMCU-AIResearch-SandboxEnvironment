# Werkwijze Test-Agent

## Doel

De test-agent ondersteunt het team in de laatste workflow-stap: test/review/verify. De agent vervangt geen teamverantwoordelijkheid, maar helpt om sneller en consistenter te controleren of een taak klaar is voor Done.

De agent beoordeelt niet op gevoel, maar op expliciete input: user story, context, acceptatiecriteria en het opgeleverde product.

## Stappen

1. Pak een user story of taak uit de test/review/verify kolom.
2. Verzamel de user story, context en acceptatiecriteria.
3. Voeg het opgeleverde product toe:
   - codefragment of pull request diff
   - documenttekst of specificatie
   - diagram in Mermaid, PlantUML, screenshot of tekstuele beschrijving
4. Plak alles onder de prompt uit `test-agent-prompt.md`.
5. Laat de AI-review uitvoeren.
6. Bespreek het eindoordeel in het team.
7. Verwerk de verbetervoorstellen of leg bewust vast waarom iets niet wordt opgepakt.
8. Zet de taak pas op Done als het oordeel `Goedgekeurd` is, of als `Goedgekeurd met opmerkingen` bewust is geaccepteerd.

## Beslisregels

| Status | Betekenis | Actie |
| --- | --- | --- |
| Goedgekeurd | Alle belangrijke acceptatiecriteria zijn aantoonbaar gehaald. | Taak mag naar Done. |
| Goedgekeurd met opmerkingen | De kern voldoet, maar er zijn kleine verbeterpunten of restrisico's. | Team beslist of de taak naar Done mag of eerst aangepast wordt. |
| Afgekeurd | Een of meer belangrijke acceptatiecriteria zijn niet gehaald of niet aantoonbaar. | Taak blijft in review/test en moet aangepast worden. |

## Wat wordt vastgelegd?

Leg bij de taak of pull request minimaal vast:

- het eindoordeel;
- de controle per acceptatiecriterium;
- de belangrijkste problemen of risico's;
- de verbetervoorstellen;
- de beslissing van het team.

## Definition of Done toevoeging

Voeg deze regel toe aan de Definition of Done:

```text
Voor elke user story is een AI-test-agent review uitgevoerd op basis van de acceptatiecriteria. Het eindoordeel en de belangrijkste verbeterpunten zijn vastgelegd bij de taak of pull request.
```

## Praktische afspraak voor het scrumbord

Een taak mag niet direct van development naar Done. Eerst gaat de taak naar test/review/verify. In die stap voert iemand de test-agent review uit en plakt de uitkomst bij de taak. Daarna verwerkt het team de feedback of accepteert bewust de resterende opmerkingen.
