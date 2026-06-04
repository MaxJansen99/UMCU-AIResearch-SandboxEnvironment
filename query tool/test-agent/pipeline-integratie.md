# Optionele Pipeline-Integratie

De minimale oplevering is de prompt plus werkwijze. Later kan dezelfde test-agent ook in het proces of een pipeline worden ingebed.

## Procesintegratie zonder code

Gebruik deze afspraak in het scrumbord:

```text
Een taak mag pas van test/review/verify naar Done als de test-agent review is uitgevoerd en het eindoordeel is vastgelegd bij de taak.
```

Voor pull requests:

```text
Plak de test-agent output als PR-comment.
Een reviewer controleert of openstaande opmerkingen zijn verwerkt of bewust geaccepteerd.
```

Deze procesintegratie is direct uitvoerbaar zonder extra tooling of API key.

## Mogelijke GitHub Actions stap

Onderstaande schets kan later worden uitgewerkt als het team een AI-provider en veilige secret-opslag beschikbaar heeft. Deze repo bevat bewust geen secret of werkende API-call.

```yaml
name: AI Test Agent Review

on:
  pull_request:
    types: [opened, synchronize, reopened]

jobs:
  ai-test-agent:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Build review input
        run: |
          git diff origin/main...HEAD > review-diff.txt
          cp "query tool/test-agent/test-agent-prompt.md" prompt.md

      - name: Run AI review
        env:
          AI_API_KEY: ${{ secrets.AI_API_KEY }}
        run: |
          echo "Hier kan later een script komen dat prompt.md en review-diff.txt naar een AI-model stuurt."
```

## Mogelijke pull request checklist

```text
- [ ] User story is toegevoegd aan de PR-beschrijving.
- [ ] Acceptatiecriteria zijn toegevoegd aan de PR-beschrijving.
- [ ] Test-agent review is uitgevoerd.
- [ ] Eindoordeel is vastgelegd.
- [ ] Verbetervoorstellen zijn verwerkt of bewust geaccepteerd.
```

## Waarom nog niet automatisch

Automatische pipeline-integratie heeft extra keuzes nodig:

- Welke AI-provider gebruikt wordt.
- Waar secrets veilig worden opgeslagen.
- Of de review blokkerend moet zijn of alleen adviserend.
- Hoe diagrammen en documenten uit taken of designs worden opgehaald.

Daarom is voor Sprint 5 de prompt- en procesvariant het meest haalbaar en aantoonbaar. De pipeline-schets laat zien hoe de agent later technisch ingebed kan worden.
