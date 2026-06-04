# AI Test-Agent

Deze map bevat de Sprint 5 oplevering voor de AI test-agent.

De test-agent is een vaste AI-reviewprompt met werkwijze en voorbeelden. De agent beoordeelt een user story, acceptatiecriteria en het opgeleverde product. Daarna geeft de agent een onderbouwd eindoordeel: `Goedgekeurd`, `Goedgekeurd met opmerkingen` of `Afgekeurd`.

De oplevering is bedoeld om direct in Canvas te kunnen uploaden. Het bestand `INLEVEREN_CANVAS.md` bevat de korte samenvatting voor de docent.

## Inhoud

- `INLEVEREN_CANVAS.md`: korte Canvas-samenvatting van de opdracht, oplevering en kwaliteitscriteria.
- `test-agent-prompt.md`: de vaste prompt die in ChatGPT, Copilot Chat of een andere AI-tool gebruikt kan worden.
- `werkwijze.md`: hoe de agent in het teamproces gebruikt wordt.
- `voorbeeld-code-review.md`: echte demo-run/simulatie van de test-agent op code.
- `voorbeeld-document-review.md`: echte demo-run/simulatie van de test-agent op een document.
- `voorbeeld-diagram-review.md`: echte demo-run/simulatie van de test-agent op een Mermaid-diagram.
- `pipeline-integratie.md`: optionele manier om de agent later in een pull request of pipeline op te nemen.

## Demo-runs

De drie voorbeeldbestanden zijn uitgewerkte demo-runs/simulaties van de test-agent. In elk voorbeeld krijgt de agent een user story, acceptatiecriteria, een producttype en een opgeleverd product. Daarna volgt de review-output in het vaste format van de prompt.

Hiermee is aangetoond dat de agent kan werken op:

- code: `voorbeeld-code-review.md`;
- documenten: `voorbeeld-document-review.md`;
- diagrammen: `voorbeeld-diagram-review.md`.

## Koppeling met kwaliteitscriteria

| Kwaliteitscriterium | Oplossing |
| --- | --- |
| De test-agent krijgt zinvolle acceptatiecriteria in de prompt mee. | De prompt heeft een verplicht blok voor acceptatiecriteria en controleert elk criterium apart. |
| De test-agent werkt op code, documenten en diagrammen. | De prompt bevat beoordelingsregels per producttype. De drie demo-runs/simulaties tonen code, documentatie en een diagram. |
| De test-agent kan goedkeuren, afkeuren of goedkeuren met opmerkingen. | Het outputformat verplicht een eindoordeel met precies deze drie statussen. |
| De test-agent geeft altijd relevante verbetervoorstellen. | Het outputformat bevat altijd de sectie `Verbetervoorstellen`, ook bij goedkeuring. |
| Er is een optionele proces- of pipeline-integratie beschreven. | `werkwijze.md` beschrijft procesintegratie en `pipeline-integratie.md` beschrijft een mogelijke pull request- of pipeline-aanpak. |

## Gebruik

Gebruik de test-agent als laatste controle voordat een taak naar Done gaat:

1. Open `test-agent-prompt.md`.
2. Vul de user story, context, acceptatiecriteria, producttype en het opgeleverde product in.
3. Laat de AI de review uitvoeren.
4. Bespreek het oordeel in de test/review/verify kolom.
5. Verwerk verbeterpunten of leg vast waarom opmerkingen bewust worden geaccepteerd.
6. Verplaats de taak pas naar Done als de review is verwerkt.

## Canvas

Voor Canvas kan de volledige map `test-agent` worden ingeleverd, of het zipbestand `test-agent-sprint5-canvas-inlevering.zip` uit de repo-root of `deliverables` map.
