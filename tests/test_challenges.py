"""Tests for challenge parsing and normalization in duo.api."""

import unittest
from unittest import mock

from duo.api import (
    AUDIO_CHALLENGE_TYPES,
    CHALLENGE_TYPES,
    extract_challenge_solution,
)
from duo.practice import normalize_answer


class TestNormalizeAnswer(unittest.TestCase):
    def test_strips_punctuation_and_case(self):
        self.assertEqual(normalize_answer("Hello, World!"), "hello world")

    def test_collapses_whitespace(self):
        self.assertEqual(normalize_answer("  multiple   spaces "), "multiple spaces")

    def test_special_chars(self):
        # Accents are preserved (they matter for language answers); only
        # surrounding punctuation/whitespace/case is normalized.
        self.assertEqual(normalize_answer("¿Qué? ¡Sí!"), "qué sí")


class TestChallengeTypes(unittest.TestCase):
    def test_no_audio_types_requested(self):
        self.assertFalse(
            any(t in CHALLENGE_TYPES for t in AUDIO_CHALLENGE_TYPES),
            "CHALLENGE_TYPES must not include audio/speaking types",
        )

    def test_audio_types_excluded_explicitly(self):
        for t in ["listen", "listenComplete", "listenMatch", "listenIsolation",
                  "listenSpeak", "listenTap", "partialListen", "speak",
                  "selectPronunciation", "selectTranscription"]:
            self.assertNotIn(t, CHALLENGE_TYPES)


class TestExtractMultipleChoice(unittest.TestCase):
    def test_assist_populates_choices_and_answer(self):
        r = extract_challenge_solution({
            "type": "assist",
            "prompt": "cat",
            "choices": ["kočka", "pes", "pták"],
            "correctIndex": 0,
        })
        self.assertEqual(r["choices"], ["kočka", "pes", "pták"])
        self.assertEqual(r["answer"], "kočka")

    def test_radio_select_generic_fallback(self):
        r = extract_challenge_solution({
            "type": "radioSelect",
            "prompt": "Which one?",
            "options": [{"text": "A"}, {"text": "B"}],
            "correctSolutions": ["B"],
        })
        self.assertEqual(r["choices"], ["A", "B"])
        self.assertEqual(r["answer"], "B")


class TestExtractTranslate(unittest.TestCase):
    def test_translate_is_freeform_not_mc(self):
        # Duolingo sends the source sentence words in `choices`; they must NOT
        # be treated as answer options.
        r = extract_challenge_solution({
            "type": "translate",
            "prompt": "Un helado y un té",
            "choices": ["An", "ice", "cream", "and", "a", "tea"],
            "correctSolutions": ["An ice cream and a tea"],
        })
        self.assertEqual(r["choices"], [])
        self.assertEqual(r["answer"], "An ice cream and a tea")
        self.assertIn("Translate", r["prompt"])


class TestExtractMatch(unittest.TestCase):
    def test_match_populates_pair_tuples(self):
        r = extract_challenge_solution({
            "type": "match",
            "pairs": [
                {"learningWord": "cat", "translation": "kočka"},
                {"learningWord": "dog", "translation": "pes"},
            ],
        })
        self.assertEqual(r["pair_tuples"], [("cat", "kočka"), ("dog", "pes")])


class TestExtractBuildSentence(unittest.TestCase):
    def test_tap_complete_populates_word_bank(self):
        r = extract_challenge_solution({
            "type": "tapComplete",
            "tokens": [{"value": "el"}, {"value": "gato"}, {"value": "bebe"}],
            "correctSolutions": ["el gato bebe"],
        })
        self.assertEqual(r["word_bank"], ["el", "gato", "bebe"])
        self.assertEqual(r["answer"], "el gato bebe")


class TestExtractCloze(unittest.TestCase):
    def test_tap_cloze_builds_blank_prompt(self):
        r = extract_challenge_solution({
            "type": "tapCloze",
            "displayTokens": [
                {"text": "The "},
                {"text": "cat", "isBlank": True},
                {"text": " runs"},
            ],
            "choices": ["dog", "cat"],
            "correctSolutions": ["cat"],
        })
        self.assertIn("____", r["prompt"])
        self.assertEqual(r["choices"], ["dog", "cat"])
        self.assertEqual(r["answer"], "cat")


class TestExtractTypeComplete(unittest.TestCase):
    def test_type_complete_builds_blanked_word(self):
        r = extract_challenge_solution({
            "type": "typeComplete",
            "displayTokens": [
                {"text": "w"},
                {"isBlank": True},
                {"text": "te"},
            ],
            "correctSolutions": ["write"],
        })
        self.assertIn("____", r["prompt"])
        self.assertEqual(r["answer"], "write")


class TestExtractUnknown(unittest.TestCase):
    def test_unknown_type_returns_prompt_with_type_name(self):
        r = extract_challenge_solution({
            "type": "someFutureType",
            "correctSolutions": ["ok"],
        })
        self.assertIn("someFutureType", r["prompt"])


class FakeClient:
    """Stand-in for DuoClient that only provides get_learning_language."""
    def __init__(self, lang):
        self._lang = lang

    def get_learning_language(self):
        return self._lang


class TestLanguageResolution(unittest.TestCase):
    @mock.patch("duo.practice.get_preset_language", return_value=None)
    def test_practice_respects_server_language_when_not_given(self, _mock_preset):
        from duo.practice import PracticeSession

        # No -l flag -> should use the active course from the server, not "es".
        s = PracticeSession(FakeClient("fr"), None)
        self.assertEqual(s.lang_code, "fr")

    @mock.patch("duo.practice.get_preset_language", return_value=None)
    def test_practice_explicit_flag_wins(self, _mock_preset):
        from duo.practice import PracticeSession

        s = PracticeSession(FakeClient("fr"), "de")
        self.assertEqual(s.lang_code, "de")

    @mock.patch("duo.practice.get_preset_language", return_value=None)
    def test_practice_falls_back_to_es_without_server_lang(self, _mock_preset):
        from duo.practice import PracticeSession

        s = PracticeSession(FakeClient(None), None)
        self.assertEqual(s.lang_code, "es")

    @mock.patch("duo.practice.get_preset_language", return_value="ja")
    def test_practice_uses_local_preset_over_server(self, _mock_preset):
        from duo.practice import PracticeSession

        # Local preset wins over the server's reported language.
        s = PracticeSession(FakeClient("fr"), None)
        self.assertEqual(s.lang_code, "ja")


if __name__ == "__main__":
    unittest.main()
