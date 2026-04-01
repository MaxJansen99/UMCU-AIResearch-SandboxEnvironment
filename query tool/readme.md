# Haal DICOM bestanden op, en run docker tegelijk

Door docker compose up command word de dicom data opgehaald als dat nog niet zo is.
Hierdoor runt en docker en de benodigde data wordt opgehaald.

command:
-cd naar de map van query tool
-docker compose up -d --build (Dicom data ophalen, )
-check de http://localhost:8000/dashboard of die werkt

# PROJECT — UMC Radiologie Query Tool PoC

## 1. Context
Binnen radiologie is er behoefte om sneller en gecontroleerd inzicht te krijgen in welke scan-data beschikbaar is voor onderzoek/innovatie (o.a. binnen de “accelerator” studie met toestemmingen). Daarnaast is er behoefte aan een veilige manier van werken met externe partijen zonder dat data kan lekken.

Deze repository focust primair op de **Query Tool** proof-of-concept (PoC). Secure access voor bedrijven kan als tweede spoor worden onderzocht/gedocumenteerd, maar valt buiten de kern van deze codebase tenzij expliciet toegevoegd.

## 2. Doel
Een werkende PoC die laat zien dat we:
1) een scan-overzicht (metadata/index) kunnen opbouwen (met fake/public data),
2) daarop kunnen filteren en zoeken,
3) aantallen en resultaten kunnen tonen,
4) (optioneel) een selectie/cohort kunnen opslaan voor vervolggebruik (bv. dataset-aanvraag/sandbox).
