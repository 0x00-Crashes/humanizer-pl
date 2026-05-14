# Humanizer-PL

Skill dla Claude Code i OpenCode, który usuwa ślady tekstu generowanego przez AI/LLM z tekstów w **języku polskim**. Polski fork (z dużą dawką inwencji własnej) projektu [blader/humanizer](https://github.com/blader/humanizer).

## Po co osobny skill dla polskiego?

Polskie teksty AI mają własne, dodatkowe znaczniki, których nie ma w anglojęzycznym katalogu Wikipedii:

- **Kalki składniowe z angielskiego** — *oferta dedykowana, adresować problem, dostarczać wartość, w kontekście...*
- **Polskie GPT-izmy** — *W dzisiejszym dynamicznym świecie..., Warto podkreślić..., Podsumowując...*
- **Błędy typograficzne** — `"..."` zamiast `„..."`, em-dash bez spacji zamiast półpauzy ze spacjami
- **Błędy fleksyjne** — *Wielu pisarzy starali się* zamiast *starało się*
- **Brak lokalnego kontekstu** — pomylone polskie skrótowce, halucynacje w obszarze polskiego prawa, brak polskich idiomów

Detektory automatyczne (GPTZero, Originality, Copyleaks) mają w polskim margines błędu rzędu 10–15% — znacznie większy niż w angielskim. Dlatego analiza manualna z dobrym przewodnikiem ma realną wartość.

## Instalacja

### Claude Code

```bash
mkdir -p ~/.claude/skills
git clone https://github.com/0x00-Crashes/humanizer-pl ~/.claude/skills/humanizer-pl
```

Albo ręcznie:

```bash
mkdir -p ~/.claude/skills/humanizer-pl
cp SKILL.md ~/.claude/skills/humanizer-pl/
```

### OpenCode

```bash
mkdir -p ~/.config/opencode/skills
git clone https://github.com/0x00-Crashes/humanizer-pl ~/.config/opencode/skills/humanizer-pl
```

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

### Wsparcie dla LaTeX i tekstów akademickich

Skill jest szczególnie przydatny dla:
- prac magisterskich, doktorskich, MBA pisanych w LaTeX
- artykułów naukowych, których "AI smell" może wzbudzić podejrzenia recenzentów
- raportów branżowych w cyberbezpieczeństwie, prawie, finansach
- treści marketingowych po polsku, gdy zależy nam, by nie wyglądały generycznie
- maili biznesowych, gdy automatyczne tłumaczenie z angielskiego zostawiło kalki

## Co skill wykrywa

### Część A: Wzorce uniwersalne (29 wzorców z Wikipedia: Signs of AI writing)

Pompowanie znaczenia, promocyjny ton, powierzchowne analizy z `-ąc/-ając`, formuliczne sekcje "Wyzwania", AI-słownictwo (*kluczowy, istotny, dynamiczny, w kontekście*), unikanie *jest*/*są* na rzecz *stanowi*/*pełni funkcję*, paralelizmy negatywne, reguła trzech, cykl synonimów, fałszywe zakresy, em-dash, pogrubienia, Title Case W Nagłówkach, emoji, curly quotes, artefakty czatu, sycofantyczny ton, frazy-wypełniacze, nadmierne hedging, generyczne pozytywne zakończenia, manieryczne pary z łącznikiem, tropy "prawdziwej autorytetu", sygnalizowanie zamiast działania, fragmentaryczne nagłówki.

### Część B: Polska specyfika (najważniejsza)

**30. Kalki składniowe z angielskiego** — tabela 16 najczęstszych kalk z poprawnymi polskimi odpowiednikami.

**31. Polskie GPT-izmy** — zwroty otwierające (*W dzisiejszym dynamicznym świecie...*), łączniki (*Warto podkreślić...*), domykacze (*Dzięki temu..., Co ostatecznie prowadzi do...*), zakończenia (*Podsumowując...*).

**32. Polska typografia** — cudzysłowy „...", myślnik vs półpauza vs dywiz, spacje wokół półpauzy, anti-pattern em-dasha bez spacji, sygnały NASK (pusta spacja na początku akapitu, wielka litera po dwukropku w listach).

**33. Błędy fleksyjne** — zgodność podmiotu z orzeczeniem przy liczbie nieokreślonej, aspekt czasownika, rekcja przyimkowa, szyk wyrazów, odmiana nazw własnych.

**34. Brak lokalnego kontekstu** — generyczne przykłady, pomylone polskie realia prawne (klasyk z NASK: *PKP — Polska Kolej Prywatna*), brak polskich idiomów.

**35. Monotonny rytm i "podejrzana czystość"** — zbyt równe zdania, brak literówek, idealna interpunkcja, brak głosu osobistego.

## O personie

Persona skilla — *John Miodek* — to ironiczny ukłon w stronę prof. Jana Miodka, kanonicznego polskiego językoznawcy. Anglicyzowane imię "John" to celowy żart: pierwsze ostrzeżenie przed zaglikadnieniem polszczyzny, którego sam udziela. Profesjonalna polonistyka z dystansem.

## Bazy źródłowe

- [Wikipedia: Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing) — utrzymywany przez WikiProject AI Cleanup
- [blader/humanizer](https://github.com/blader/humanizer) — oryginalny anglojęzyczny humanizer (MIT)
- Rafał Mazur, *O poprawności językowej tekstów generowanych przez SI na przykładzie ChatuGPT*, "LingVaria", Wydział Polonistyki UJ
- NASK — analizy tekstów AI w polskim (Ewelina Bartuzi-Trokielewicz, Aleksandra Krasnodębska)
- Robert Chwałowski, *Typografia typowej książki*
- Poradnia Językowa PWN — sjp.pwn.pl/poradnia
- Analizy polskie: Senuto, Top Online, DBest Content, Pracownie Orange, NASK/Wirtualnemedia, o-jezyku.pl

## Historia wersji

- **1.0.0** — Pierwsze wydanie. Pełna część A (29 wzorców uniwersalnych z humanizera Bladera, spolszczone). Pełna część B (6 dużych sekcji polskiej specyfiki — kalki, GPT-izmy, typografia, fleksja, kontekst, rytm).

## Licencja

MIT — w duchu oryginalnego [blader/humanizer](https://github.com/blader/humanizer).
