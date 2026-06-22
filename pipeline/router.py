from config import WHISPER_TO_INDIC
from pipeline.lang_detect import classify
from pipeline import mixer


class Router:
    """
    Routes each audio chunk to the right model based on language detection.

    Routes:
      'english'     → Whisper only (1 Whisper pass via detect_and_transcribe)
      'indian >90%' → IndicConformer only (1 Whisper pass for detection, reused)
      'indian 85-90%' / 'mixed' → Both models + mixer (2 Whisper passes)
      'unsupported' → Whisper auto fallback
    """

    def __init__(self, whisper_model, indic_model):
        self.whisper = whisper_model
        self.indic = indic_model

    def process(self, audio_path, forced_lang=None):
        """
        Transcribe one audio chunk.

        Parameters
        ----------
        audio_path  : path to WAV chunk
        forced_lang : None (auto-detect) | 'en' | 'hi' | 'bn' | ... etc.

        Returns
        -------
        (transcript_str, info_dict)
        info_dict keys: route, lang, confidence
        """
        # ── Forced language mode ─────────────────────────────────────────────
        if forced_lang == "en":
            text = self.whisper.transcribe(audio_path, language="en")
            return text, {"route": "whisper", "lang": "en", "confidence": 1.0}

        if forced_lang and forced_lang in WHISPER_TO_INDIC:
            indic_id = WHISPER_TO_INDIC[forced_lang]
            text = self.indic.transcribe(audio_path, language_id=indic_id)
            return text, {"route": "indic", "lang": forced_lang, "confidence": 1.0}

        # ── Auto-detect mode — ONE Whisper pass for detect + transcribe ──────
        # detect_and_transcribe() runs Whisper once with language=None and returns
        # (lang, confidence, text, words). For English and pure-Indian routes this
        # means we never need a second Whisper pass.
        detected, confidence, whisper_text, whisper_words = \
            self.whisper.detect_and_transcribe(audio_path)

        route_type, lang_code = classify(detected, confidence)

        if route_type == "english":
            # Text already computed above — no second Whisper pass
            return whisper_text, {"route": "whisper", "lang": "en", "confidence": confidence}

        if route_type == "indian":
            if confidence >= 0.90:
                # Very high confidence = genuinely Indian speech.
                # Whisper would translate (not romanise) at this level — use IndicConformer.
                indic_id = WHISPER_TO_INDIC[lang_code]
                text = self.indic.transcribe(audio_path, language_id=indic_id)
                return text, {"route": "indic", "lang": lang_code, "confidence": confidence}
            # 85–90% — may have English loanwords → mixer
            text = self._mix(audio_path, lang_code)
            return text, {"route": "mixed", "lang": lang_code, "confidence": confidence}

        if route_type == "mixed":
            text = self._mix(audio_path, lang_code)
            return text, {"route": "mixed", "lang": lang_code, "confidence": confidence}

        # Unsupported language → Whisper auto fallback (text already computed)
        return whisper_text, {"route": "whisper-fallback", "lang": detected, "confidence": confidence}

    def _mix(self, audio_path, indian_lang):
        """Word-level mixing for code-switched audio."""
        indic_id = WHISPER_TO_INDIC.get(indian_lang, "hi")

        # Force language="en" so Whisper outputs ASCII words with timestamps.
        # detect_and_transcribe used language=None so its words may be Devanagari;
        # we need a fresh en-forced pass for the mixer to work correctly.
        whisper_words = self.whisper.transcribe_words(audio_path, language="en")

        indic_text = self.indic.transcribe(audio_path, language_id=indic_id)

        return mixer.merge(whisper_words, indic_text)
