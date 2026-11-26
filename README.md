# Humanizer-PL

Skill dla Claude Code i OpenCode, który usuwa ślady tekstu generowanego przez AI/LLM z tekstów w **języku polskim**. Polski fork (z dużą dawką inwencji własnej) projektu [blader/humanizer](https://github.com/blader/humanizer).

## Po co osobny skill dla polskiego?

Polskie teksty AI mają własne, dodatkowe znaczniki, których nie ma w anglojęzycznym katalogu Wikipedii:

- **Kalki składniowe z angielskiego** — *oferta dedykowana, adresować problem, dostarczać wartość, w kontekście...*
- **Polskie GPT-izmy** — *W dzisiejszym dynamicznym świecie..., Warto podkreślić..., Podsumowując...*
- **Błędy typograficzne** — `"..."` zamiast `„...”`, em-dash bez spacji zamiast myślnika ze spacjami
- **Błędy fleksyjne** — *Wielu pisarzy starali się* zamiast *starało się*
- **Brak lokalnego kontekstu** — pomylone polskie skrótowce, halucynacje w obszarze polskiego prawa, brak polskich idiomów

Skill nie służy do omijania detektorów i nie daje gwarancji, że tekst przestanie być rozpoznawany jako wygenerowany. Na polskim zbiorze Śmigiel najlepszy system PolEval 2025 (https://aclanthology.org/2025.poleval-main.2.pdf) miał około 97% trafności na danych podobnych do treningowych, 91% na nowych gatunkach, 84% przy nowym modelu i 61% przy obu naraz. Pojedyncze sygnały stylu są słabe i pojawiają się też u ludzi, dlatego skill redaguje dopiero przy co najmniej dwóch niezależnych sygnałach.

### Przeciw czemu ten skill działa

| Kto albo co ocenia tekst | Na co patrzy | Co zmienia skill |
|---|---|---|
| Czytelnik z listą wzorców: promotor, recenzent, redaktor | zwroty-wytrychy, kalki, typografia, rytm zdań | To jedyny odbiorca, przeciw któremu skill działa. Usuwa wzorce z list. |
| Detektor oparty na przewidywalności tekstu: moduł SI w JSA (próg perplexity), Plagiat.pl (producent wymienia przewidywalność tekstu i długość zdań) | na ile kolejne słowa są przewidywalne dla modelu językowego | Prawie nic. W pomiarze na pięciu tekstach maszynowych perplexity zmieniła się po redakcji z 18,6 na 19,2 przy progu 29,4 i cztery z pięciu tekstów zostały poniżej progu. Pomiar robiono modelem `polish-gpt2-small`; model i próg JSA nie są publiczne. |
| Klasyfikator dostrojony, np. Pangram | cechy wyuczone na tekstach ludzi i modeli | Nie wiadomo. Nie było pomiaru. |
| Znak wodny dostawcy modelu | statystyczny ślad w doborze słów | Nie usuwa go. Zdania przepisane przez skill dostają znak modelu, na którym skill działa; w tekście oddanym prawie bez zmian znak nie ma się do czego przyczepić. Znak nie odróżnia tekstu napisanego przez model od tekstu mocno przez niego zredagowanego. |
| Zasady uczelni | oświadczenie o użyciu AI, rozmowa o pracy | Nic. Redakcja stylu przez model sama podlega ujawnieniu. Raport skilla (wykaz zmian i audyt) warto zachować jako dokumentację. |

Źródła i zastrzeżenia do tabeli:

- **JSA:** baza wiedzy OPI PIB — fragment jest podejrzany, „gdy jego wartość Perplexity jest mniejsza niż zadana wartość progowa” ([jsa-cp.opi.org.pl](https://jsa-cp.opi.org.pl/baza-wiedzy-skroty/uzycie-sztucznej-inteligencji)).
- **Plagiat.pl:** deklaracje producenta — detektor patrzy m.in. na „przewidywalność tekstu, długość zdań” ([strona produktu](https://plagiat.pl/wykrywanie-uzycia-ai/), [pomoc dla instytucji](https://instytucje-raport.plagiat.pl/detekcja-ai)). Producent definiuje „wyniki fałszywie pozytywne” niespójnie, więc nie podajemy jego odsetka fałszywych alarmów.
- **Perplexity:** pomiar przeglądu z 26.11.2026 na tekstach z PolEval 2025 Śmigiel, każdy przez pełną procedurę skilla; próg 29,4 to 5. percentyl 16 innych tekstów ludzkich. Dla wersji 1.2.0 wynik był podobny (18,6 → 19,5). **To tylko pięć tekstów i jeden model oceniający**, więc traktuj liczby jako ilustrację, nie pomiar skuteczności.
- **Pangram:** karta modelu deklaruje obsługę polskiego ([Pangram 4](https://www.pangram.com/research/model-card/pangram-4)).
- **Znak wodny:** Anthropic — „The watermark only applies to words Claude chooses.” i „It cannot distinguish «Claude wrote this» from «Claude heavily edited this.»” ([ogłoszenie](https://www.anthropic.com/news/claude-text-watermark), [pomoc](https://support.claude.com/en/articles/16266773-how-claude-marks-ai-generated-content)). Wiersz dotyczy modeli, które znakują tekst.
- **Uczelnie:** patrz sekcja „Użycie w pracach akademickich” niżej.

## Instalacja

### Claude Code

```bash
mkdir -p ~/.claude/skills
git clone --branch v1.3.0 --depth 1 https://github.com/0x00-Crashes/humanizer-pl ~/.claude/skills/humanizer-pl
git -C ~/.claude/skills/humanizer-pl rev-parse HEAD   # porównaj z SHA podanym w opisie wydania v1.3.0
```

Instalacja jest przypięta do wydania. Claude Code wczytuje zmiany w katalogu skilli na bieżąco, więc `git pull` na gałęzi `main` podmieniałby instrukcje modelu bez przeglądu. Po klonie z tagu repo nie jest na żadnej gałęzi (detached HEAD), więc `git pull` i tak nie zadziała. Aktualizacja do nowego wydania (przykład dla v1.4.0):

```bash
cd ~/.claude/skills/humanizer-pl
git fetch --depth 1 origin tag v1.4.0
git diff v1.3.0 v1.4.0 -- SKILL.md   # przeczytaj zmiany, zanim je włączysz
git checkout v1.4.0
git rev-parse HEAD                   # porównaj z SHA z opisu wydania
```

Albo ręcznie:

```bash
mkdir -p ~/.claude/skills/humanizer-pl
cp SKILL.md ~/.claude/skills/humanizer-pl/
```

### OpenCode

```bash
mkdir -p ~/.config/opencode/skills
git clone --branch v1.3.0 --depth 1 https://github.com/0x00-Crashes/humanizer-pl ~/.config/opencode/skills/humanizer-pl
git -C ~/.config/opencode/skills/humanizer-pl rev-parse HEAD   # porównaj z SHA z opisu wydania
```

Aktualizacja jak dla Claude Code: `git fetch --depth 1 origin tag <nowy-tag>`, `git diff`, `git checkout <nowy-tag>`, `git rev-parse HEAD`.

> **Note:** OpenCode skanuje też `~/.claude/skills/` dla kompatybilności, więc pojedynczy klon do `~/.claude/skills/humanizer-pl/` działa dla obu narzędzi.

## Użycie

### Claude Code

```
/humanizer-pl

[wklej swój polski tekst tutaj]
```

### OpenCode

```
/humanizer-pl

[wklej swój polski tekst tutaj]
```

Albo poproś model bezpośrednio:

```
Zhumanizuj ten polski tekst: [tekst]
```

Skill włącza się tylko na wyraźną prośbę o redakcję albo ocenę polskiego tekstu pod kątem śladów AI, np. *„zhumanizuj”*, *„usuń AI”*, *„popraw po AI”*, *„brzmi jak ChatGPT”*, *„za dużo myślników”*, *„sprawdź, czy to brzmi jak AI”*. Sama ocena bez redakcji: *„sprawdź”*, *„oceń”* albo `--detect`.

### Kalibracja głosu

Aby dopasować redakcję do Twojego osobistego stylu, dostarcz próbkę:

```
/humanizer-pl

Oto próbka mojego pisania do dopasowania głosu:
[wklej 2-3 akapity własnego pisania]

Teraz zhumanizuj ten tekst:
[wklej tekst AI do humanizacji]
```

Skill przeanalizuje rytm zdań, dobór słów i nawyki interpunkcyjne, a następnie zastosuje je w redakcji zamiast generycznego "czystego" outputu.

### Do jakich tekstów

- raportów branżowych w cyberbezpieczeństwie, prawie, finansach
- treści marketingowych po polsku, gdy zależy nam, by nie wyglądały generycznie
- maili biznesowych, gdy automatyczne tłumaczenie z angielskiego zostawiło kalki

### Użycie w pracach akademickich

Jeśli piszesz pracę zaliczeniową albo dyplomową, sprawdź zasady swojej uczelni, zanim użyjesz tego skilla. Redakcja stylu przez model językowy to użycie AI, które zwykle trzeba ujawnić, a skill tego obowiązku nie zdejmuje.

- **Uniwersytet Warszawski**, uchwała nr 75 URK z 11.09.2026, obowiązuje od 1.10.2026: student dołącza oświadczenie o użytych narzędziach AI oraz celu i zakresie ich użycia (§6), a użycie AI w pracy dyplomowej uzgadnia z opiekunem i opisuje we wstępie (§7). Wyjątek dotyczy tylko narzędzi służących wyłącznie standardowej korekcie pisowni, interpunkcji i gramatyki (§1 pkt 2). [Dokument](https://dokumenty.uw.edu.pl/dziennik/DURK/Lists/Dziennik/Attachments/248/DURK.2026.75.UURK.75.pdf)
- **Uniwersytet Gdański**, zarządzenie nr 109/R/26 z 28.09.2026 i wytyczne: tekst napisany samodzielnie, a potem zredagowany przez AI w zakresie stylu lub przeformułowania zdań, wymaga przypisu i pozycji w bibliografii (cz. III pkt 3). Prompty mogą być udostępnione linkiem albo w załączniku. Autor zachowuje dokumentację pracy z narzędziem, a brak udokumentowania użycia AI podlega odpowiedzialności dyscyplinarnej (cz. II pkt 7). [Zarządzenie](https://bip.ug.edu.pl/akty_normatywne/120511/zarzadzenie_nr_109r26_rektora_uniwersytetu_gdanskiego_z_dnia_28_wrzesnia_2026_roku_w_sprawie_zasad_korzystania_z_systemow_i_narzedzi_sztucznej), [wytyczne](https://bip.ug.edu.pl/sites/default/files/nodes/akty_normatywne/120511/files/z_aktywnymi_linkami_wytyczne_ai_ksztalcenie.pdf)

Raport skilla (wykaz zmian i audyt semantyczny) przydaje się jako dokumentacja użycia narzędzia.

## Co skill wykrywa

### Część A: Wzorce uniwersalne (29 wzorców z Wikipedia: Signs of AI writing)

Pompowanie znaczenia, promocyjny ton, powierzchowne analizy z `-ąc/-ając`, formuliczne sekcje "Wyzwania", AI-słownictwo (*kluczowy, istotny, dynamiczny, w kontekście*), unikanie *jest*/*są* na rzecz *stanowi*/*pełni funkcję*, paralelizmy negatywne, reguła trzech, cykl synonimów (słaby sygnał), fałszywe zakresy, myślnik (sekcja 14: typografia, nie sygnał AI — liczba myślników i ich łańcuchy nie liczą się jako sygnał), pogrubienia, Title Case W Nagłówkach, emoji, curly quotes, artefakty czatu, sycofantyczny ton, frazy-wypełniacze, nadmierne hedging, generyczne pozytywne zakończenia, manieryczne pary z łącznikiem, tropy „prawdziwego autorytetu”, sygnalizowanie zamiast działania, fragmentaryczne nagłówki.

### Część B: Polska specyfika (najważniejsza)

**30. Kalki składniowe z angielskiego** — tabela 16 najczęstszych kalk z poprawnymi polskimi odpowiednikami.

**31. Polskie GPT-izmy** — zwroty otwierające (*W dzisiejszym dynamicznym świecie...*), łączniki (*Warto podkreślić...*), domykacze (*Dzięki temu..., Co ostatecznie prowadzi do...*), zakończenia (*Podsumowując...*).

**32. Polska typografia** — cudzysłowy „...”, myślnik vs półpauza vs dywiz, spacje wokół półpauzy, anti-pattern em-dasha bez spacji, wskazówki z artykułu Wirtualnemedia.pl (2025, częściowo za ekspertkami NASK: pusta spacja na początku akapitu, wielka litera po dwukropku w listach; słabe sygnały). Myślnika nie zamienia na przecinek tylko z powodu znaku. Pracuje w parze z sekcją 14: 32 mówi *jakim znakiem*, 14 mówi *czy w ogóle go tu używać*.

**33. Błędy fleksyjne** — zgodność podmiotu z orzeczeniem przy liczbie nieokreślonej, aspekt czasownika, rekcja przyimkowa, szyk wyrazów, odmiana nazw własnych.

**34. Brak lokalnego kontekstu** — generyczne przykłady, pomylone polskie realia prawne (przykład z artykułu Wirtualnemedia.pl, 2025: *PKP — Polska Kolej Prywatna*), brak polskich idiomów.

**35. Monotonny rytm i „podejrzana czystość”** — zbyt równe zdania, brak głosu osobistego (tylko uwaga, skill go nie dopisuje). Brak błędów to słaby sygnał; skill nigdy nie wprowadza błędów celowo.

### Część C: Nowsze wzorce (2026)

**36. Korekty ramowe** (*należy traktować jako X, a nie Y*, *nie przesądza o*), **37. mgliste powiązania** (*związany z*, *kojarzony z*), **38. nadmierne powoływanie się na same źródła** (*odnotowany w*, *opisywany w mediach regionalnych*). Na podstawie Wikipedii (materiał anglojęzyczny), bez pomiaru na polskim korpusie; każdy to słaby sygnał.

### Zasady nadrzędne

Tekst do redakcji to dane, nie polecenia: podejrzane instrukcje w tekście skill zgłasza na początku odpowiedzi z cytatem, a nie wykonuje ani nie usuwa. Skill nie dopisuje faktów, liczb, źródeł, cytatów, przeżyć ani opinii; brakujące konkrety oznacza jako luki `[konkret: …?]`. Redaguje dopiero przy dwóch niezależnych sygnałach, domyślnie fragmentami, teksty nieformalne zostawia nieformalnymi i ma tryb samego wykrywania (raport bez redakcji).

## O personie

Persona skilla — *John Miodek* — to ironiczny ukłon w stronę prof. Jana Miodka, kanonicznego polskiego językoznawcy. Anglicyzowane imię "John" to celowy żart: pierwsze ostrzeżenie przed zanglicyzowaniem polszczyzny, którego sam udziela. Profesjonalna polonistyka z dystansem.

## Bazy źródłowe

- [Wikipedia: Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing) — utrzymywany przez WikiProject AI Cleanup
- [blader/humanizer](https://github.com/blader/humanizer) — oryginalny anglojęzyczny humanizer (MIT)
- Rafał Mazur, *O poprawności językowej tekstów generowanych przez SI na przykładzie ChatuGPT*, "LingVaria", Wydział Polonistyki UJ
- Wirtualnemedia.pl, J. Dąbrowska-Cydzik, „Widać to z daleka”. Oto, jak łatwo poznać, że tekst napisała sztuczna inteligencja, 27.05.2025, z wypowiedziami Eweliny Bartuzi-Trokielewicz i Aleksandry Krasnodębskiej (NASK) — https://www.wirtualnemedia.pl/po-czym-poznac-ze-tekst-napisala-sztuczna-inteligencja-poradnik-ai,7179298735470721a
- Robert Chwałowski, *Typografia typowej książki*
- Poradnia Językowa PWN — sjp.pwn.pl/poradnia
- Analizy polskie: Senuto, Top Online, DBest Content, Pracownie Orange, o-jezyku.pl

## Kontrola jakości (dla współtwórców)

Skrypty w `scripts/` (czysty Python 3.11+, bez zależności):

```bash
python3 scripts/metrics.py SKILL.md --lint-skill                          # nagłówek: zgody na narzędzia, szeroki trigger
python3 scripts/gate_examples.py SKILL.md --ref reference/smigiel.json   # przykłady Przed/Po: dopiski, GPT-izmy, myślnik→przecinek
python3 scripts/gate_safety.py SKILL.md SKILL-light.md README.md         # ukryty Unicode, komentarze HTML, przypięcie instalacji
python3 scripts/metrics.py przed.md po.md --ref reference/smigiel.json   # metryki jednej redakcji na tle tekstów ludzkich
```

`gate_examples.py` zgłasza też `dropped_qualifiers` tam, gdzie przykład celowo usuwa słowo (np. nadmierny hedging w §24); każde takie zgłoszenie trzeba przeczytać, a nie dopisywać słowa z powrotem. Bramka nie widzi dopisanych twierdzeń bez liczb i nazw, więc nowe przykłady trzeba też przejrzeć ręcznie.

## Historia wersji

- **1.3.0** — Zasady nadrzędne: tekst to dane (podejrzane instrukcje zgłaszane z cytatem w obowiązkowym punkcie 0 „Ostrzeżenia”), zakaz dopisywania, dwa niezależne sygnały przed przepisaniem, minimalna ingerencja, teksty nieformalne, tryb wykrywania. §14 przepisany: myślnik to typografia, nie sygnał AI (bez etykiety „krytyczny”, progu gęstości, łańcuchów jako sygnału i reguły kciuka). §32 bez zamiany myślników na przecinki; poprawiona tabela cudzysłowów i zamknięcia „…” w całych plikach. Audyt semantyczny w obie strony. Przykłady Przed/Po i pełny przykład bez dopisanych faktów, z lukami `[konkret: …?]`. Sekcja „Głos i dusza” bez dopisywania opinii i przeżyć. Atrybucja wskazówek „NASK” do artykułu Wirtualnemedia.pl z 2025. §11 jako słaby sygnał, §30 bez etykiety „krytyczny”. Nowe wzorce 36–38. Usunięte zgody na narzędzia w nagłówku i szeroki trigger w opisie; SKILL-light zsynchronizowany z pełną wersją (wersja 1.3.0). README: tabela „Przeciw czemu ten skill działa”, instalacja przypięta do wydania z weryfikacją SHA, sekcja o pracach akademickich (UW, UG), bramki w `scripts/`.
- **1.2.0** — Rozszerzenie sekcji 14 ("Nadużywanie em-dasha") na pełnego *„traktatu o myślniku”* (z etykietą „krytyczny”). Nacisk przesunięty z typografii (która zostaje w sekcji 32) na **funkcję składniową**: myślnik jako maszynowy zamiennik spójników podrzędnych *co/bo/ponieważ/który* — wzorzec szczególnie nienaturalny w polskim. Dodano 5 zdiagnozowanych podwzorców (łańcuchy dashy, podwójny myślnik w roli wtrącenia, myślnik zamiast spójnika/dwukropka/kropki), strategię redakcji "myślnikowej" (m.in. próg gęstości: 2-3/100 słów = sygnał, 5+ = prawie pewnie AI), regułę kciuka oraz świadomość rejestru (kropka vs spójnik). Triggery rozszerzone o *"za dużo myślników"*, *"usuń dashy"*, *"em-dash overuse"*.
- **1.0.0** — Pierwsze wydanie. Pełna część A (29 wzorców uniwersalnych z humanizera Bladera, spolszczone). Pełna część B (6 dużych sekcji polskiej specyfiki — kalki, GPT-izmy, typografia, fleksja, kontekst, rytm).

## Licencja

MIT — w duchu oryginalnego [blader/humanizer](https://github.com/blader/humanizer).
