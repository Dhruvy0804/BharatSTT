import os

# ── Model Paths ──────────────────────────────────────────────────────────────
INDIC_MODEL_PATH = "C:/nemo_venv/hindi_asr.nemo"
# To upgrade to 22-language model, change to:
# INDIC_MODEL_PATH = "ai4bharat/indic-conformer-600m-multilingual"

WHISPER_MODEL_SIZE = "small"   # options: "tiny", "small", "medium", "large-v3"

# ── Routing Thresholds ───────────────────────────────────────────────────────
LANG_CONFIDENCE_THRESHOLD = 0.85   # above = pure language, below = mixed

# ── VAD Settings ─────────────────────────────────────────────────────────────
VAD_THRESHOLD    = 0.5
MIN_SILENCE_MS   = 200   # split at pauses >= 200ms
MIN_SPEECH_MS    = 100   # ignore chunks shorter than 100ms

# ── Language Maps ────────────────────────────────────────────────────────────
WHISPER_TO_INDIC = {
    "hi": "hi", "bn": "bn", "ta": "ta", "te": "te", "mr": "mr",
    "gu": "gu", "kn": "kn", "ml": "ml", "pa": "pa", "ur": "ur",
    "as": "as", "or": "or", "sa": "sa", "ne": "ne",
}

SUPPORTED_LANGUAGES = {
    "Auto-detect":      "auto",
    "English (en)":     "en",
    "Hindi (hi)":       "hi",
    "Bengali (bn)":     "bn",
    "Tamil (ta)":       "ta",
    "Telugu (te)":      "te",
    "Marathi (mr)":     "mr",
    "Gujarati (gu)":    "gu",
    "Kannada (kn)":     "kn",
    "Malayalam (ml)":   "ml",
    "Punjabi (pa)":     "pa",
    "Urdu (ur)":        "ur",
    "Assamese (as)":    "as",
    "Odia (or)":        "or",
    "Sanskrit (sa)":    "sa",
    "Nepali (ne)":      "ne",
    "Maithili (mai)":   "mai",
    "Sindhi (sd)":      "sd",
    "Dogri (doi)":      "doi",
    "Konkani (kok)":    "kok",
    "Kashmiri (ks)":    "ks",
    "Santali (sat)":    "sat",
    "Bodo (brx)":       "brx",
    "Manipuri (mni)":   "mni",
}
