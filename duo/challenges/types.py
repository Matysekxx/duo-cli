"""
Challenge taxonomy, supported types and language flags.
"""

from typing import List, Optional, Set

# All text-based challenge types the terminal can handle
TEXT_CHALLENGE_TYPES: List[str] = [
    "assist", "characterIntro", "characterMatch", "characterPuzzle", "characterSelect",
    "characterTrace", "characterWrite", "completeReverseTranslation", "definition", "dialogue",
    "extendedMatch", "form", "freeResponse", "gapFill", "judge",
    "match", "name", "orderTapComplete", "partialReverseTranslate",
    "patternTapComplete", "radioBinary", "radioImageSelect",
    "radioSelect", "readComprehension", "reverseAssist", "sameDifferent",
    "select", "svgPuzzle", "syllableTap",
    "tapCloze", "tapClozeTable", "tapComplete", "tapCompleteTable",
    "tapDescribe", "translate", "transliterate", "transliterationAssist", "typeCloze",
    "typeClozeTable", "typeComplete", "typeCompleteTable", "writeComprehension"
]

# Audio / speaking challenge types are intentionally excluded: the terminal
# client cannot present or capture them, so we only request text-based types.
AUDIO_CHALLENGE_TYPES: Set[str] = {
    "listen", "listenComplete", "listenMatch", "listenComprehension", "listenIsolation",
    "listenSpeak", "listenTap", "partialListen", "radioListenMatch",
    "radioListenRecognize", "syllableListenTap", "speak",
    "selectPronunciation", "selectTranscription",
}

CHALLENGE_TYPES: List[str] = [t for t in TEXT_CHALLENGE_TYPES if t not in AUDIO_CHALLENGE_TYPES]

# Visual/character challenges that cannot be rendered in pure terminal UI and get auto-completed
VISUAL_CHALLENGE_TYPES: Set[str] = {
    "characterMatch",
    "characterPuzzle",
    "characterSelect",
    "characterTrace",
    "characterWrite",
    "svgPuzzle",
}

# Challenges where the learner arranges a word bank into the correct sentence.
BUILD_SENTENCE_TYPES: Set[str] = {
    "orderTapComplete", "patternTapComplete", "syllableTap",
    "tapComplete", "tapCompleteTable",
}

# Cloze-style challenges with one or more blanks filled from a word bank.
CLOZE_TYPES: Set[str] = {
    "gapFill", "tapCloze", "tapClozeTable", "typeCloze", "typeClozeTable",
}

# Challenges where the learner types the missing letters of a word.
TYPE_COMPLETE_TYPES: Set[str] = {
    "typeComplete", "typeCompleteTable",
}

# Types whose "choices"/"options" are the source sentence tokens (not answer options).
# They must be solved as free text, never as multiple choice.
FREE_TEXT_FAMILY: Set[str] = {
    "translate",
}

LANGUAGE_FLAGS = {
    "en": "🇬🇧",
    "es": "🇪🇸",
    "fr": "🇫🇷",
    "de": "🇩🇪",
    "it": "🇮🇹",
    "ja": "🇯🇵",
    "zh": "🇨🇳",
    "ru": "🇷🇺",
    "pt": "🇧🇷",
    "cs": "🇨🇿",
    "pl": "🇵🇱",
    "ko": "🇰🇷",
    "nl": "🇳🇱",
    "sv": "🇸🇪",
    "el": "🇬🇷",
    "tr": "🇹🇷",
    "uk": "🇺🇦",
    "vi": "🇻🇳",
    "ar": "🇸🇦",
    "hi": "🇮🇳",
    "la": "🏛️",
    "eo": "🟢",
    "kl": "🖖",
}


def get_flag(lang_code: Optional[str]) -> str:
    """Return flag emoji for a language code."""
    if not lang_code:
        return "🌐"
    return LANGUAGE_FLAGS.get(lang_code.lower(), "🌐")
