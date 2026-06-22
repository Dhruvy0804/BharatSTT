from config import LANG_CONFIDENCE_THRESHOLD, WHISPER_TO_INDIC

_INDIAN_LANGS = set(WHISPER_TO_INDIC.keys())


def classify(lang_code, confidence):
    """
    Classify a detected language into a routing category.

    Returns (route_type, effective_lang_code) where route_type is one of:
      'english'     — high-confidence English  → Whisper
      'indian'      — high-confidence Indian   → IndicConformer
      'mixed'       — low confidence           → word-level mixer
      'unsupported' — unknown language         → Whisper fallback
    """
    if confidence >= LANG_CONFIDENCE_THRESHOLD:
        if lang_code == "en":
            return "english", "en"
        if lang_code in _INDIAN_LANGS:
            return "indian", lang_code
        return "unsupported", lang_code

    # Low confidence = likely code-switched
    if lang_code in _INDIAN_LANGS:
        return "mixed", lang_code
    if lang_code == "en":
        return "mixed", "hi"   # default Indian side to Hindi
    return "unsupported", lang_code
