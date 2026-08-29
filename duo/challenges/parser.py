"""
Duolingo Challenge Parser and extractor.
Converts raw challenge dictionaries from the Duolingo API into structured Challenge objects.
"""

from typing import Any, Dict, List, Optional, Tuple
from ..models import Challenge
from .types import (
    BUILD_SENTENCE_TYPES,
    CLOZE_TYPES,
    FREE_TEXT_FAMILY,
    TYPE_COMPLETE_TYPES,
)


class ChallengeParser:
    """Parses raw Duolingo challenge payloads into structured Challenge dataclass instances."""

    def parse(self, ch: Dict[str, Any]) -> Challenge:
        """Parse any raw challenge object into a Challenge model."""
        ctype = ch.get("type", "unknown")
        raw_prompt = ch.get("prompt") or ch.get("promptText") or ch.get("sentence") or ""
        translation = (
            ch.get("solutionTranslation")
            or (ch.get("metadata", {}) if isinstance(ch.get("metadata"), dict) else {}).get("translation")
            or (ch.get("metadata", {}) if isinstance(ch.get("metadata"), dict) else {}).get("word")
            or ""
        )

        solutions: List[str] = []
        if "correctSolutions" in ch and ch["correctSolutions"]:
            solutions.extend([str(s) for s in ch["correctSolutions"]])
        elif "solution" in ch and ch["solution"]:
            solutions.append(str(ch["solution"]))

        best_sol = ch.get("challengeResponseTrackingProperties", {}).get("best_solution")
        if best_sol and best_sol not in solutions:
            solutions.append(str(best_sol))

        meta = ch.get("metadata", {}) if isinstance(ch.get("metadata"), dict) else {}
        meta_word = meta.get("word") or meta.get("translation")

        raw_choices = ch.get("choices") or []
        options = ch.get("options") or []
        pairs = ch.get("pairs") or []
        display_tokens = ch.get("displayTokens") or []
        tokens = ch.get("tokens") or []
        correct_idx = ch.get("correctIndex")

        formatted_choices: List[str] = []
        pair_strings: List[str] = []
        pair_tuples: List[Tuple[str, str]] = []
        word_bank: List[str] = []
        answer_str = ""
        prompt = ""

        # Dispatch by challenge family
        if ctype in ["assist", "select", "characterSelect", "gapFill", "tapCloze", "tapClozeTable", "typeCloze", "typeClozeTable"]:
            formatted_choices = self._extract_choices(raw_choices, options)
            answer_str = self._resolve_answer(formatted_choices, correct_idx, solutions, meta_word)
            prompt = self._build_choice_prompt(ctype, raw_prompt, display_tokens, translation, solutions)

        elif ctype == "translate":
            if solutions:
                answer_str = solutions[0]
            elif meta_word:
                answer_str = str(meta_word)

            if raw_prompt:
                prompt = f"✍️ Translate: \"{raw_prompt}\""
            elif display_tokens:
                prompt = f"✍️ Translate: \"{''.join(t.get('text', '') for t in display_tokens)}\""

        elif ctype in TYPE_COMPLETE_TYPES:
            prompt = self._build_type_complete_prompt(display_tokens, translation, raw_prompt, solutions)
            if solutions:
                answer_str = solutions[0]

        elif ctype == "match":
            for p in pairs:
                lw = p.get("learningWord") or p.get("learning_word") or p.get("learningToken") or ""
                tr = p.get("translation") or p.get("fromToken") or ""
                if lw and tr:
                    pair_tuples.append((lw, tr))
                    pair_strings.append(f"{lw} ⇄ {tr}")
            answer_str = ", ".join(pair_strings)
            prompt = "Match the following pairs"

        elif ctype in BUILD_SENTENCE_TYPES:
            word_bank = self._extract_word_bank(tokens, display_tokens, raw_choices, options)
            answer_str = solutions[0] if solutions else (str(meta_word) if meta_word else "")
            prompt = "Arrange the words to build the correct sentence"

        else:
            if solutions:
                answer_str = solutions[0]
            elif meta_word:
                answer_str = str(meta_word)
            if raw_prompt:
                prompt = raw_prompt

        # Fallback for MC-like types with choices
        if not formatted_choices and ctype not in BUILD_SENTENCE_TYPES and ctype not in FREE_TEXT_FAMILY:
            formatted_choices = self._extract_choices(raw_choices, options)
            if formatted_choices and not answer_str:
                if correct_idx is not None and 0 <= correct_idx < len(formatted_choices):
                    answer_str = formatted_choices[correct_idx]
                elif solutions:
                    answer_str = solutions[0]

        if not prompt:
            if raw_prompt:
                prompt = raw_prompt
            elif translation:
                prompt = f"Translate/Solve: (Meaning: {translation})"
            else:
                prompt = f"Solve this {ctype} challenge"

        if not answer_str and solutions:
            answer_str = solutions[0]

        return Challenge(
            type=ctype,
            prompt=prompt,
            choices=formatted_choices,
            pairs=pair_strings,
            pair_tuples=pair_tuples,
            word_bank=word_bank,
            answer=answer_str or "OK",
            solutions=solutions,
            correct_index=correct_idx,
            raw=ch,
        )

    def _extract_choices(self, raw_choices: List[Any], options: List[Any]) -> List[str]:
        formatted: List[str] = []
        if raw_choices:
            for c in raw_choices:
                if isinstance(c, str):
                    formatted.append(c)
                elif isinstance(c, dict):
                    formatted.append(c.get("text", ""))
        elif options:
            for opt in options:
                if isinstance(opt, dict):
                    formatted.append(opt.get("text", ""))
                else:
                    formatted.append(str(opt))
        return formatted

    def _resolve_answer(
        self,
        formatted_choices: List[str],
        correct_idx: Optional[int],
        solutions: List[str],
        meta_word: Any,
    ) -> str:
        if correct_idx is not None and 0 <= correct_idx < len(formatted_choices):
            return formatted_choices[correct_idx]
        elif solutions:
            return solutions[0]
        elif meta_word:
            return str(meta_word)
        return ""

    def _build_choice_prompt(
        self,
        ctype: str,
        raw_prompt: str,
        display_tokens: List[Dict[str, Any]],
        translation: str,
        solutions: List[str],
    ) -> str:
        if ctype == "gapFill":
            if display_tokens:
                sentence = self._tokens_to_sentence(display_tokens)
                prompt = f"Fill in the blank:\n  \"{sentence}\""
                if translation:
                    prompt += f"\n  [dim](Meaning: {translation})[/dim]"
                return prompt
            elif raw_prompt:
                return f"Fill in the blank: \"{raw_prompt}\""
        elif ctype == "assist":
            if raw_prompt:
                return f"Translate: '{raw_prompt}'"
        elif ctype in ["select", "characterSelect"]:
            if raw_prompt:
                return f"Select the correct option for: '{raw_prompt}'"
        elif ctype in ["tapCloze", "tapClozeTable", "typeCloze", "typeClozeTable"]:
            if display_tokens:
                sentence = self._tokens_to_sentence(display_tokens)
                if "____" in sentence:
                    prompt = f"Fill in the blank:\n  \"{sentence}\""
                    if translation:
                        prompt += f"\n  [dim](Meaning: {translation})[/dim]"
                    return prompt
            if raw_prompt:
                return f"Fill in the blank: \"{raw_prompt}\""
            elif solutions:
                return f"Fill in the blank (answer: {solutions[0]})"
        return raw_prompt or ""

    def _build_type_complete_prompt(
        self,
        display_tokens: List[Dict[str, Any]],
        translation: str,
        raw_prompt: str,
        solutions: List[str],
    ) -> str:
        if display_tokens:
            sentence = self._tokens_to_sentence(display_tokens)
            if "____" in sentence:
                prompt = f"🔤 Type the missing letters:\n  [bold bright_white]{sentence}[/]"
                if translation:
                    prompt += f"\n  [dim](Meaning: {translation})[/dim]"
                return prompt
        if raw_prompt:
            return f"🔤 Type the word: \"{raw_prompt}\""
        elif solutions:
            return f"🔤 Type the word (answer: {solutions[0]})"
        return ""

    def _tokens_to_sentence(self, display_tokens: List[Dict[str, Any]]) -> str:
        sentence_parts: List[str] = []
        in_blank = False
        for t in display_tokens:
            is_b = t.get("isBlank") or t.get("is_blank", False)
            if is_b:
                if not in_blank:
                    sentence_parts.append("____")
                    in_blank = True
            else:
                in_blank = False
                sentence_parts.append(t.get("text", ""))
        return "".join(sentence_parts)

    def _extract_word_bank(
        self,
        tokens: List[Any],
        display_tokens: List[Any],
        raw_choices: List[Any],
        options: List[Any],
    ) -> List[str]:
        word_bank: List[str] = []
        for t in (tokens or display_tokens):
            if isinstance(t, dict):
                word_bank.append(t.get("value") or t.get("text") or t.get("token") or "")
            elif isinstance(t, str):
                word_bank.append(t)
        word_bank = [w for w in word_bank if w]
        if not word_bank and raw_choices:
            for c in raw_choices:
                word_bank.append(c if isinstance(c, str) else c.get("text", ""))
        if not word_bank and options:
            for opt in options:
                word_bank.append(opt if isinstance(opt, str) else opt.get("text", ""))
        return word_bank


def extract_challenge_solution(ch: Dict[str, Any]) -> Dict[str, Any]:
    """Compatibility function: parse raw challenge and return legacy dictionary."""
    parser = ChallengeParser()
    challenge = parser.parse(ch)
    return challenge.to_dict()
