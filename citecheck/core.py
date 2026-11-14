"""Core logic. Standard library only.

Idea: split an answer into claims (sentences), find the source passage that
best matches each claim (BM25 ranking), then label the claim by how much of its
wording the passage covers. Two cheap safety rules catch common mistakes:
numbers in the claim must appear in the passage, and a negation mismatch
("do not hibernate" vs "hibernate") is flagged as a possible contradiction.

This measures *overlap*, not *meaning*. See the README for what it misses.
"""
import math
import re
from collections import Counter
from dataclasses import dataclass, field

STOP = frozenset("""a an the and or but if of to in on at by for with from as is
are was were be been being it its this that these those he she they them their
his her we you i not no do does did have has had will would can could than then
there here what which who whom when where why how all any each more most some
such only own same too very just into over under again about also so up out
may might must should shall""".split())

NEGATIONS = frozenset(["not", "no", "never", "none", "cannot", "without",
                       "neither", "nor"])
NUM_RE = re.compile(r"\d+(?:[.,]\d+)*")
WORD_RE = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?")
SENT_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(])")

SUPPORTED = "Supported"
PARTLY = "Partly supported"
UNSUPPORTED = "Unsupported"
CONTRADICTION = "Possible contradiction"


def _stem(word):
    """Very light stemmer so 'makes', 'making' and 'made' do not all differ."""
    w = word
    if w.endswith("ies") and len(w) > 4:
        w = w[:-3] + "y"
    elif w.endswith("ing") and len(w) > 5:
        w = w[:-3]
    elif w.endswith("ed") and len(w) > 3:
        w = w[:-2]
    elif w.endswith("es") and len(w) > 4:
        w = w[:-2]
    elif w.endswith("s") and len(w) > 3 and not w.endswith("ss"):
        w = w[:-1]
    if w.endswith("e") and len(w) > 2:
        w = w[:-1]
    return w


def words(text):
    return [w.lower() for w in WORD_RE.findall(text)]


def _is_negation(w):
    return w in NEGATIONS or w.endswith("n't")


def content_tokens(text):
    """Stemmed content words. Negations are handled separately, not here."""
    return [_stem(w) for w in words(text)
            if w not in STOP and len(w) > 1 and not _is_negation(w)]


def numbers(text):
    return {n.replace(",", "") for n in NUM_RE.findall(text)}


def has_negation(text):
    return any(_is_negation(w) for w in words(text))


def negated_near(passage, claim_tokens, window=3):
    """True if a negation word sits within `window` words of a word that the
    passage shares with the claim. Negations elsewhere in the passage are
    ignored, so 'helmets are not required' does not taint 'riders must be 16'."""
    qset = set(claim_tokens)
    ws = words(passage)
    hits = [i for i, w in enumerate(ws) if _stem(w) in qset]
    neg = [i for i, w in enumerate(ws) if _is_negation(w)]
    return any(abs(i - j) <= window for i in hits for j in neg)


def split_sentences(text):
    text = re.sub(r"\s+", " ", text.strip())
    return [s.strip() for s in SENT_SPLIT.split(text) if s.strip()]


def split_claims(answer):
    """Each sentence with at least four words (numbers count), minus questions."""
    claims = []
    for s in split_sentences(answer):
        if s.endswith("?"):
            continue
        if len(words(s)) + len(NUM_RE.findall(s)) >= 4:
            claims.append(s)
    return claims


@dataclass
class Passage:
    source: str
    text: str
    tokens: list = field(repr=False)


def build_passages(sources):
    """One passage per sentence, plus each sentence joined with the next."""
    passages = []
    for name, text in sources.items():
        sents = split_sentences(text)
        for i, s in enumerate(sents):
            passages.append(Passage(name, s, content_tokens(s)))
            if i + 1 < len(sents):
                joined = s + " " + sents[i + 1]
                passages.append(Passage(name, joined, content_tokens(joined)))
    return passages


class BM25:
    def __init__(self, docs, k1=1.5, b=0.75):
        self.docs, self.k1, self.b = docs, k1, b
        self.n = len(docs)
        self.avg = sum(len(d) for d in docs) / self.n if self.n else 0.0
        df = Counter(t for d in docs for t in set(d))
        self.idf = {t: math.log(1 + (self.n - c + 0.5) / (c + 0.5))
                    for t, c in df.items()}
        self.tf = [Counter(d) for d in docs]

    def scores(self, query):
        out = []
        for i, d in enumerate(self.docs):
            s = 0.0
            for t in set(query):
                f = self.tf[i].get(t, 0)
                if f:
                    denom = f + self.k1 * (1 - self.b + self.b * len(d) / (self.avg or 1))
                    s += self.idf.get(t, 0.0) * f * (self.k1 + 1) / denom
            out.append(s)
        return out


@dataclass
class Result:
    claim: str
    label: str
    coverage: float
    source: str = ""
    passage: str = ""
    reasons: list = field(default_factory=list)


def check_answer(answer, sources, supported_at=0.75, partly_at=0.5, top_k=3):
    """Check every claim in `answer` against `sources` ({name: text})."""
    claims = split_claims(answer)
    passages = build_passages(sources)
    if not passages:
        return [Result(c, UNSUPPORTED, 0.0, reasons=["no source text given"])
                for c in claims]
    bm25 = BM25([p.tokens for p in passages])
    results = []
    for claim in claims:
        q = content_tokens(claim)
        if not q:
            continue
        scores = bm25.scores(q)
        ranked = sorted(range(len(passages)), key=lambda i: scores[i],
                        reverse=True)[:top_k]
        qset = set(q)

        def coverage(i):
            return len(qset & set(passages[i].tokens)) / len(qset)

        best = max(ranked, key=lambda i: (coverage(i), -len(passages[i].tokens),
                                          scores[i]))
        p, cov = passages[best], coverage(best)
        reasons = []
        missing = numbers(claim) - numbers(p.text)
        if missing:
            reasons.append("number not in source: " + ", ".join(sorted(missing)))
        negation_mismatch = (has_negation(claim)
                             != negated_near(p.text, q))

        if missing:
            label = UNSUPPORTED
        elif cov >= partly_at and negation_mismatch:
            label = CONTRADICTION
            reasons.append("negation differs between claim and source")
        elif cov >= supported_at:
            label = SUPPORTED
        elif cov >= partly_at:
            label = PARTLY
            reasons.append("only part of the claim's wording appears in the source")
        else:
            label = UNSUPPORTED
            reasons.append("no passage covers this claim")
        results.append(Result(claim, label, round(cov, 2), p.source, p.text, reasons))
    return results


def summarize(results):
    counts = Counter(r.label for r in results)
    return {k: counts.get(k, 0)
            for k in (SUPPORTED, PARTLY, CONTRADICTION, UNSUPPORTED)}
