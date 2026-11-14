import unittest

from citecheck import check_answer, split_claims, summarize
from citecheck.core import (CONTRADICTION, SUPPORTED, UNSUPPORTED, BM25,
                            content_tokens, numbers, split_sentences)

SRC = {"doc.txt": (
    "The shop opens at 9 a.m. and closes at 5 p.m. on weekdays. "
    "Coffee costs 3 dollars. Pets are not allowed inside. "
    "Staff wear green aprons.")}


class ClaimSplitting(unittest.TestCase):
    def test_sentences_split_on_punctuation(self):
        self.assertEqual(len(split_sentences("One two. Three four? Five six!")), 3)

    def test_questions_and_short_fragments_are_skipped(self):
        answer = "Is it open now? Yes. The shop opens at 9 a.m. on weekdays."
        self.assertEqual(split_claims(answer),
                         ["The shop opens at 9 a.m. on weekdays."])


class Tokens(unittest.TestCase):
    def test_numbers_ignore_commas(self):
        self.assertEqual(numbers("about 1,200 bikes and 3.5 km"), {"1200", "3.5"})

    def test_stemming_matches_forms(self):
        self.assertEqual(content_tokens("makes making"), content_tokens("make make"))

    def test_negations_are_not_content(self):
        self.assertNotIn("not", content_tokens("pets are not allowed"))


class Ranking(unittest.TestCase):
    def test_bm25_prefers_matching_document(self):
        docs = [["coffee", "cost"], ["pet", "allow"], ["apron", "green"]]
        scores = BM25(docs).scores(["coffee"])
        self.assertEqual(scores.index(max(scores)), 0)


class Checking(unittest.TestCase):
    def label(self, claim):
        return check_answer(claim, SRC)[0].label

    def test_supported_claim(self):
        self.assertEqual(self.label("Coffee costs 3 dollars."), SUPPORTED)

    def test_wrong_number_is_unsupported(self):
        r = check_answer("Coffee costs 5 dollars.", SRC)[0]
        self.assertEqual(r.label, UNSUPPORTED)
        self.assertIn("5", " ".join(r.reasons))

    def test_fabricated_claim_is_unsupported(self):
        self.assertEqual(self.label("The shop sells fresh pastries daily."),
                         UNSUPPORTED)

    def test_negation_mismatch_is_flagged(self):
        self.assertEqual(self.label("Pets are allowed inside the shop."),
                         CONTRADICTION)

    def test_unrelated_negation_does_not_taint(self):
        self.assertEqual(self.label("Staff wear green aprons."), SUPPORTED)

    def test_no_sources(self):
        r = check_answer("Coffee costs 3 dollars.", {})[0]
        self.assertEqual(r.label, UNSUPPORTED)

    def test_summary_counts(self):
        res = check_answer("Coffee costs 3 dollars. Coffee costs 9 dollars.", SRC)
        s = summarize(res)
        self.assertEqual((s[SUPPORTED], s[UNSUPPORTED]), (1, 1))


if __name__ == "__main__":
    unittest.main()
