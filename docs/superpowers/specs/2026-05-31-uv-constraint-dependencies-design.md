# Design: Native `constraint-dependencies` im uv-Hook

**Datum:** 2026-05-31
**Status:** Entwurf zur Review

## Problem

mxdev unterstützt externe (HTTP) Constraints im klassischen pip-Pfad: `requirements-in`
wird rekursiv aufgelöst, inklusive `-c`/`-r`-Includes auf lokale Dateien und HTTP(S)-URLs
(mit Caching und Offline-Support). Plone-Releases werden genau so abgebildet — z.B.
`-c https://dist.plone.org/release/6.2.0rc1/constraints.txt`.

Der uv-`sync`-Pfad über `pyproject.toml` unterstützt das **nicht**: uv kennt zwar
`[tool.uv] constraint-dependencies`, akzeptiert dort aber **keine** `-c URL`-Includes,
sondern nur eine flache Liste von inline-PEP-508-Specifiern. Der bestehende mxdev-uv-Hook
([src/mxdev/uv.py](../../../src/mxdev/uv.py)) schreibt aktuell nur `[tool.uv.sources]` und
`[tool.uv] override-dependencies`, aber **kein** `constraint-dependencies`. Dadurch fehlen
beim `uv sync` die externen Constraints (z.B. die Plone-Release-Pins) komplett.

Maik Derstappens Tool [`derico-de/uv-import-constraint-dependencies`](https://github.com/derico-de/uv-import-constraint-dependencies)
löst genau dieses Problem als eigenständiges CLI (liest `-c`-Constraints lokal/HTTP, strippt
Kommentare und `-r`/`-c`-Direktiven, schreibt sortiertes Array nach
`[tool.uv] constraint-dependencies`). Wir wollen das **nativ** in mxdev, ohne das Modul als
Abhängigkeit hereinzuziehen — die Idee und das TOML-Mapping stammen von Maik (Attribution).

## Kern-Insight

mxdev macht die eigentliche Arbeit bereits: Nach der Read-Phase liegt in `state.constraints`
die **vollständig rekursiv aufgelöste** Constraint-Liste vor (HTTP gefetcht + gecacht,
Includes expandiert, aus-Source-entwickelte und via `version-overrides` ersetzte Pakete
bereits als `# ... -> mxdev disabled`-Kommentar markiert). Wir brauchen **keine neue
Fetch-Logik** — der uv-Hook muss diese Daten nur filtern und als `constraint-dependencies`
emittieren.

## Datenfluss

```
read()  →  state.constraints   (rekursiv aufgelöst, HTTP+Cache, disabled-Zeilen auskommentiert)
                  │
write_hooks() → UvPyprojectUpdater.write()
                  ├─ [tool.uv.sources]               (unverändert)
                  ├─ [tool.uv] override-dependencies (unverändert)
                  └─ [tool.uv] constraint-dependencies  ← NEU
```

## Komponenten

### 1. Filter-/Transform-Funktion (rein, testbar)

Leitidee: Das `constraint-dependencies`-Array wird ein **TOML-Spiegel von
`constraints-mxdev.txt`** — gleiche **Quell-Reihenfolge**, Herkunfts-Kommentare erhalten.
Specifier-Zeilen werden zu Array-Einträgen, Kommentarzeilen zu Array-internen Kommentaren.

`_constraints_to_uv(constraints: list[str]) -> list[ConstraintItem]` im uv-Modul, wobei
`ConstraintItem` ein kleines, geordnetes Element ist, das **entweder** einen Kommentar
**oder** einen Specifier trägt (z.B. `("comment", text)` / `("entry", specifier)`). So bleibt
die Funktion rein und testbar und der Writer kann Kommentare + Einträge in Reihenfolge
emittieren.

Pro Zeile aus `state.constraints`, in Original-Reihenfolge:

1. **Specifier-Zeilen** mit `packaging.requirements.Requirement` parsen → als `entry`
   übernehmen. Environment-Markers (`; python_version >= "3.9"`) bleiben erhalten.
   Nicht-parsebare „Zeilen, die wie Specifier aussehen" (z.B. `--hash`, `--index-url`,
   `-e ...`) verwerfen und auf DEBUG loggen.
2. **Herkunfts-Kommentare** (`# begin constraints from: <url>` / `# end constraints from: <url>`)
   als `comment` erhalten — sie liefern die Nachvollziehbarkeit, die der txt-Pfad bietet.
3. **`# <pkg> -> mxdev disabled (...)`-Zeilen** als `comment` erhalten (1:1 wie in
   `constraints-mxdev.txt`). Sie dokumentieren, *warum* ein Pin hier fehlt (das Paket kommt
   über `[tool.uv.sources]` bzw. `override-dependencies`). → **Auf Review verifizieren**, ob
   gewünscht; Alternative wäre, sie wegzulassen.
4. **Dekorative `####…`-Trennlinien und Leerzeilen** verwerfen (reines visuelles Rauschen;
   die begin/end-Header liefern die Gruppierung).
5. **Kein Dedupe, keine Konfliktauflösung** — konsistent mit dem klassischen Pfad
   (`constraints-mxdev.txt` ist reiner Passthrough; pip/uv behandelt Konflikte). Konfligierende
   Versionen desselben Pakets bleiben beide erhalten.
6. **Keine Sortierung** — Quell-Reihenfolge wird beibehalten (Gruppen-Kohärenz vor
   Diff-Minimierung).

### 2. Schreiben nach pyproject.toml

Erweiterung von `_update_pyproject` in [src/mxdev/uv.py](../../../src/mxdev/uv.py):

- Ziel: `[tool.uv] constraint-dependencies` als multiline-Array (analog zum bestehenden
  `override-dependencies`-Block, `uv.py:152-156`), aber mit **Array-internen Kommentaren**
  in Quell-Reihenfolge.
- **Ersetzen + Marker:** Das Array wird vollständig von mxdev verwaltet und bei jedem Lauf
  überschrieben. Eine `# managed by mxdev — do not edit`-Kommentarzeile als erstes Element.
- Leeres Filterergebnis → Key nicht schreiben; ein bestehender, mxdev-verwalteter Key wird in
  dem Fall geleert/entfernt, damit kein veralteter Stand stehen bleibt.

### ⚠️ Technisches Hauptrisiko: tomlkit & Array-interne Kommentare

Array-interne Kommentare über viele Zeilen sind die heikelste tomlkit-Stelle. **Früh im Plan
verifizieren** (kleiner Spike), dass tomlkit interspersed comments in einem multiline-Array
korrekt **und idempotent** serialisiert (zweiter Lauf = byte-identisch).

Falls tomlkit das nicht sauber round-trippt, **Fallback** (Reihenfolge bleibt erhalten):
Herkunft als **Inline-Kommentar pro Eintrag** statt als eigene Kommentarzeile, z.B.
`"Zope==6.0",  # from <url>`. Das unterstützt tomlkit zuverlässig. Die begin/end-Blockheader
werden dann zu einem Inline-`# from <url>`-Suffix pro Eintrag verdichtet; die disabled-Marker
entfallen in diesem Fallback.

### 3. Opt-out

- Default **an**, sobald `[tool.uv] managed = true` (konsistent mit `sources`/`override-dependencies`).
- Abschaltbar über mx.ini-`[settings]`-Eintrag, namespace-konform zur uv-Hook-Konvention:
  `uv-constraint-dependencies = false`.
- Auslesen via `state.configuration.settings.get("uv-constraint-dependencies", "true")` +
  `to_bool(...)`.

## Doku & Attribution

- README-Abschnitt „uv pyproject.toml integration“ um `constraint-dependencies` erweitern,
  inkl. Beispiel mit `-c https://dist.plone.org/...`-Kette und dem Opt-out-Setting.
- CHANGES.md-Eintrag (unreleased).
- Attribution für Maik Derstappen / `derico-de/uv-import-constraint-dependencies` in
  CONTRIBUTORS und/oder README (konzeptionelle Vorlage, mit seinem Einverständnis).

## Tests (TDD)

Reine Funktion `_constraints_to_uv`:
- Specifier-Zeilen → `entry`, in **Quell-Reihenfolge** (keine Sortierung).
- `# begin/end constraints from`-Header → als `comment` erhalten.
- `# ... -> mxdev disabled`-Zeilen → als `comment` erhalten.
- `####`-Trenner und Leerzeilen werden verworfen.
- Nicht-parsebare Zeilen (`--hash`, `-e`, `--index-url`) werden verworfen.
- Environment-Markers bleiben erhalten.
- Konfligierende/doppelte Versionen bleiben beide erhalten (Passthrough).

Hook-Integration:
- `managed=true` → `constraint-dependencies` wird geschrieben.
- `managed=false`/fehlend → nicht geschrieben.
- Opt-out-Setting `uv-constraint-dependencies = false` greift.
- Bestehendes Array wird ersetzt (nicht gemerged).
- Herkunfts-Kommentare landen in Quell-Reihenfolge im Array.
- Idempotenz: zweiter Lauf erzeugt **byte-identisches** Ergebnis (deckt das tomlkit-Risiko ab).
- Leeres Ergebnis → kein/leerer Key.

Ende-zu-Ende:
- `-c URL`-Kette via httpretty-Fixture (wie in bestehenden Tests) → korrekt aufgelöste
  `constraint-dependencies` in Quell-Reihenfolge mit Herkunfts-Kommentaren.

## Bewusst ausgeklammert (YAGNI)

- Kein Merge-Modus mit handgepflegten Einträgen (das Array gehört mxdev; handgepflegte
  Constraints gehören in die requirements/constraints-Kette).
- Keine separate `uv-constraints = URL`-Konfiguration (die bestehende `requirements-in`-Kette
  ist die einzige Quelle der Wahrheit).
- Keine Konflikt-/Dedupe-Logik (Konsistenz mit dem klassischen Pfad).
- Keine alphabetische Sortierung (Quell-Reihenfolge + Gruppen-Header gewählt).
