"""
Answer text normalization for flexible and forgiving comparison.
"""


def normalize_answer(text: str) -> str:
    """Normalize answer string by removing punctuation, extra whitespace and lowercasing.
    
    Preserves international accents and Unicode characters.
    """
    clean = text.lower().strip()
    for char in [".", ",", "!", "?", "'", '"', "¿", "¡", ":", ";", "-", "–"]:
        clean = clean.replace(char, " ")
    return " ".join(clean.split())
