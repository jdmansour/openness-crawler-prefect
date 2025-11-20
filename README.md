

# Scraper für Offenheitskritierien

Dieser Scraper ist im Rahmen einer Studie der Wikimedia Deutschland zum Thema "Offenheit" entstanden. Die Fragestellung ist, wie offen sind öffentliche Einrichtungen in Deutschland wirklich?

Dazu wurde eine Liste von zu evaluierenden Einrichtungen erstellt, zusammen mit Kritieren für die verschiedenen Bereiche (Bildung, Kultur, Forschung, ...). Diese teilen sich in operative Kriterien (was ist die Praxis) und strategische Kriterien (z.B. was steht in einer Leitline).

Für die erste Version des Scrapers haben wir uns das operative Kriterium "Vorhandensein einer quelloffenen Kurs- bzw. Lernplattform" an Hochschulen angeschaut, das zum Faktor "Einsatz offener digitaler Werkzeuge für Lehre und Verwaltung" in der Dimension "Offener Zugang zu Wissen und Lehre" zählt. 

Der Scraper geht eine Liste der Hochschulen durch, wobei für jede Hochschule und Lernplattform (Beispielhaft Moodle, OpenOLAT, Ilias) eine Google-Suche gestartet wird. Die Top 5 Suchergebnisse werden dann mittels eines LLMs nach hinweisen auf die Lernplattform analysisert. Die anderen Kritieren können in analoger Weise abgefragt werden.

## Vorbereitung

Das Skript benötigt eine Liste der Institutionen, welche in einem gesonderten Repository gepflegt wird (TODO: wird noch hochgeladen).

API-Keys für Google und das LLM müssen in einer .env-Datei hinterlegt werden. Lege dazu eine `.env' mit folgendem Inhalt an:

```
GOOGLE_API_KEY=...
GOOGLE_CSE_ID=...
LLM_API_KEY=...
LLM_BASE_URL=https://api.openai.com/v1/
LLM_PROVIDER=gpt-5-mini
```

## Verwendung

Den prefect server starten:

    uv run prefect start

Alle verfügbaren Crawler sehen:

    uv run python baseline.py

Einen Crawler starten:

    uv run python baseline.py open_lms

Man kann den Lauf des Crawlers nun unter http://127.0.0.1:4200 beobachten.

Die aktuell verfügbaren Crawler sind:

| Crawler | Bereich | Faktor | Kriterientyp | Kriterium |
|---------|---------|--------|--------------|-----------|
|`forschungsdatenrepo` | Hochschulen | Offene Forschungsdaten (Open Data) | operativ | Vorhandensein eines Forschungsdaten-Repositoriums |
|`open_lms` | Hochschulen | Einsatz offener digitaler Werkzeuge für Lehre und Verwaltung | operativ | Vorhandensein einer quelloffenen Kurs- bzw. Lernplattform (⚠️ Teilweise implementiert) |
|`open_access` | Hochschulen | Offener Zugang zu Forschungspublikationen (Open Access) | strategisch | Vorhandensein einer öffentlich zugänglichen und klar benannten institutionellen Open-Access-Policy oder Open-Science-Policy |

Die Anzahl paralleler Tasks kann wie folgt eingestellt werden:

    uv run prefect concurrency-limit create google-search 5
    uv run prefect concurrency-limit create handle-uni 5
    uv run prefect concurrency-limit create scrape-url 5

## Hinweise:
- Wenn eine Seite sehr viel Text enthält, teilt der Scraper sie in Stücke (Chunks), und gibt diese dem LLM individuell zur Beurteilung. Dabei werden maximal 5 Chunks betrachtet, damit der Ressourcenverbrauch nicht aus dem Ruder läuft (z.B. wenn ein Vorlesungsverzeichnis mit mehreren hundert Seiten eingelesen wird). Die Chunks werden alle nacheinander betrachtet. Selbst wenn ein positives Ergebnis im ersten Chunk gefunden wird, werden alle Chunks an das LLM gegeben. Das ist eine Beschränkung von der eingesetzten Bibliothek crawl4ai. Eine mögliche Verbesserung wäre abzubrechen nachdem ein positives Ergebnis gefunden wurde.