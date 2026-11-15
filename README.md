# Sage : Citation Checker

**Live demo:** https://sage-citation-checker.streamlit.app


Paste an AI answer and the source text it relied on. The tool splits the answer
into claims, finds the closest passage in the source for each one, and labels
it **Supported**, **Partly supported**, **Possible contradiction** or
**Unsupported**, so you know which claims to verify by hand first.

It automates the habit of opening the source and looking for the passage that
backs each claim, which is the first thing to do when you use AI for research.

## Run it

```bash
python3 -m citecheck examples/sample_answer.txt examples/bees.txt   # command line, no installs
python3 -m pip install -r requirements.txt && python3 -m streamlit run app.py   # web interface
python3 -m unittest discover -s tests   # tests
python3 eval/run_eval.py eval/test.json   # accuracy check
```

Example output:

```
[OK]  Supported (1.00)  Honey bees live in colonies with one queen.
[X]   Unsupported (1.00)  The queen can lay up to 5,000 eggs per day.
        best match: The queen can lay up to 2,000 eggs per day in the busiest season.
        note: number not in source: 5000
[!]   Possible contradiction (0.80)  Honey bees hibernate during the winter.
        best match: Honey bees do not hibernate in winter; ...
[X]   Unsupported (0.25)  Drones collect most of the nectar for the hive.
```

## How it works

1. **Split** the answer into sentences (claims) and the sources into passages
   (each sentence, plus each pair of neighbouring sentences).
2. **Rank** passages for each claim with BM25 and take the best of the top 3 by
   how many of the claim's content words they contain (ties go to the shorter
   passage).
3. **Label** by that coverage: 0.75 or more is Supported, 0.5 to 0.75 is
   Partly supported, less is Unsupported.
4. **Two safety rules:** every number in the claim must appear in the passage,
   and a negation that appears near the matched words in only one of the two
   texts is flagged as a possible contradiction. Negations elsewhere in the
   passage are ignored.

Pure Python standard library for the checker. Streamlit is only for the interface.

## How well does it work?

Measured on short labelled claims about invented source texts that I wrote
(`eval/`). A claim is "correct" if the tool says Supported exactly when the
claim is supported.

| Set | Claims | Correct | Unsupported claims wrongly passed |
|---|---|---|---|
| Dev (used to tune rules and thresholds) | 25 | 24 (96%) | 0 |
| Held-out (new source, run once after tuning) | 12 | 9 (75%) | 1 |

**Read the held-out row, not the dev row.** The dev score is inflated because I
adjusted the rules while looking at those examples. 12 claims is far too few
for a firm accuracy figure, and the sources and claims are short and simple.

What went wrong on the held-out set:
- **Wrongly passed:** "The planetarium ticket is included with general
  admission." The source says the ticket is *separate*. The claim reuses the
  same words with the opposite meaning and no negation word, so overlap can't
  tell.
- **Wrongly flagged:** "Children under 5 get in for free" (source: "enter
  free"), a paraphrase, and "Flash photography is not allowed" (source:
  "prohibited"), where the negation rule fires because the source says the same
  thing with a different word.

## Limits

- It measures word overlap, not meaning. Paraphrases can be flagged and
  reworded contradictions can pass. Always read the matched passage.
- A supported label means the source contains similar words, not that the
  source is true.
- English only; simple stemming; spelled-out numbers ("seven") are not compared.
- Sentence-level claims only. A claim that spans two sentences may be split.

## Roadmap

- [ ] Replace the overlap rule with a natural-language-inference model that
      judges whether a passage entails a claim (the main fix for the errors above)
- [ ] Antonym and synonym handling (prohibited / not allowed)
- [ ] A larger labelled set from real AI answers and real sources
- [ ] Load sources from a URL or PDF
- [ ] Highlight the matched words in the passage

## Layout

```
citecheck/core.py   claim splitting, BM25, labels (pure functions)
citecheck/cli.py    command line
app.py              Streamlit interface
tests/              unit tests
eval/               labelled claims and the scoring script
examples/           sample answer and source texts
```
