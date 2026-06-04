# Inleveren Canvas - Sprint 5 AI Test-Agent

## Korte samenvatting van de opdracht

De opdracht was om een AI test-agent te maken voor de test/review/verify stap van het scrumbord. De agent moet op basis van een taak, user story en acceptatiecriteria beoordelen of het opgeleverde product voldoet. Het product kan code, documentatie of een diagram zijn. De agent moet een duidelijk eindoordeel geven en altijd verbetervoorstellen doen.

## Wat wij hebben opgeleverd

Wij hebben een complete test-agent oplevering gemaakt in de map `test-agent`.

De oplevering bestaat uit:

- een vaste prompt voor de AI test-agent;
- een werkwijze voor gebruik in het teamproces;
- beslisregels voor `Goedgekeurd`, `Goedgekeurd met opmerkingen` en `Afgekeurd`;
- drie uitgewerkte demo-runs/simulaties van de test-agent voor code, documentatie en diagrammen;
- een optionele proces- en pipeline-integratie;
- dit Canvas-inleverdocument.

De drie demo-runs/simulaties staan in:

- `voorbeeld-code-review.md`;
- `voorbeeld-document-review.md`;
- `voorbeeld-diagram-review.md`.

Deze voorbeelden laten zien dat de test-agent dezelfde promptstructuur kan toepassen op verschillende soorten producten: code, documenten en diagrammen.

## Hoe de test-agent werkt

De test-agent krijgt vier soorten input:

1. de user story of taak;
2. relevante context;
3. concrete acceptatiecriteria;
4. het opgeleverde product.

Daarna controleert de agent elk acceptatiecriterium apart. De agent benoemt gevonden problemen, risico's en verbeterpunten. Aan het einde geeft de agent een van deze eindoordelen:

- `Goedgekeurd`;
- `Goedgekeurd met opmerkingen`;
- `Afgekeurd`.

De output is bewust gestandaardiseerd, zodat het team de review makkelijk kan vastleggen bij een taak of pull request.

## Voldoen aan de kwaliteitscriteria

| Kwaliteitscriterium | Hoe dit is aangetoond |
| --- | --- |
| 1. De test-agent krijgt zinvolle acceptatiecriteria in de prompt mee. | `test-agent-prompt.md` bevat een verplicht acceptatiecriteria-blok en controleert elk criterium apart. |
| 2. De test-agent werkt op code, documenten en diagrammen. | De prompt bevat beoordelingsregels per producttype. De drie demo-runs/simulaties tonen dat de agent code, documentatie en een Mermaid-diagram kan beoordelen. |
| 3. De test-agent kan goedkeuren, afkeuren of goedkeuren met opmerkingen. | Het verplichte outputformat bevat precies deze drie eindoordelen. |
| 4. De test-agent geeft altijd relevante verbetervoorstellen. | Het outputformat bevat altijd de sectie `Verbetervoorstellen`, ook als het product wordt goedgekeurd. |
| 5. Er is een optionele proces- of pipeline-integratie beschreven. | `werkwijze.md` beschrijft procesintegratie in het scrumbord. `pipeline-integratie.md` beschrijft een mogelijke PR- en GitHub Actions-aanpak. |

## Wat de docent kan bekijken

Voor de beoordeling zijn vooral deze bestanden relevant:

- `README.md`: overzicht van de oplevering;
- `test-agent-prompt.md`: de daadwerkelijke prompt van de test-agent;
- `werkwijze.md`: toepassing in het teamproces;
- `voorbeeld-code-review.md`: demo-run/simulatie en bewijs dat de agent code kan beoordelen;
- `voorbeeld-document-review.md`: demo-run/simulatie en bewijs dat de agent documenten kan beoordelen;
- `voorbeeld-diagram-review.md`: demo-run/simulatie en bewijs dat de agent diagrammen kan beoordelen;
- `pipeline-integratie.md`: optionele integratie in proces of pipeline.

## Conclusie

Met deze oplevering is een bruikbare AI test-agent gemaakt voor de test/review/verify stap. De agent helpt het team om user stories consequenter te controleren op acceptatiecriteria en geeft altijd een onderbouwd oordeel met verbeterpunten. Daarmee sluit de oplossing aan op de agentic mindset uit het gastcollege en op de kwaliteitscriteria van de opdracht.
