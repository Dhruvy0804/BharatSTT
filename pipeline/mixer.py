"""
Word-level mixer for code-switched audio.

Two strategies depending on audio content:

1. BOUNDARY strategy — for audio where language switches once (English → Hindi):
   - IndicConformer output has a clear Hindi section starting mid-way
   - Take Whisper-EN words up to the estimated switch point
   - Append IndicConformer's authentic Hindi tail

2. WORD-LEVEL strategy — for true Hinglish (mixed word-by-word):
   - Whisper-EN gives ASCII words with timestamps
   - Keep English words; replace romanised Indian words with IndicConformer
   - Advances indic_idx for both English and Indian positions (1-to-1 alignment)
"""

# ── English vocabulary (genuine English words in code-switched speech) ───────
_ENGLISH_VOCAB = {
    "i","you","he","she","we","they","it","me","him","her","us","them",
    "my","your","his","our","their","its","this","that","these","those",
    "a","an","the","is","are","was","were","be","been","being",
    "have","has","had","do","does","did","will","would","could","should",
    "may","can","need","must","shall","might","let",
    "and","or","but","so","if","then","when","where","why","how",
    "what","who","which","because","since","though","although","as",
    "at","in","on","of","to","for","with","by","from","about","after",
    "before","during","through","over","under","between",
    "not","no","yes","ok","okay","please","thank","thanks","sorry",
    "hello","hi","bye","also","just","very","too","already","still",
    "now","then","today","tomorrow","yesterday","again","here","there",
    "some","any","all","more","less","most","other","same","such","like",
    "time","day","week","month","year","morning","evening","night",
    "office","work","meeting","call","report","email","phone","message",
    "team","project","data","system","server","file","code","app",
    "money","bank","card","bill","payment","order","status","update",
    "home","house","road","car","train","bus","flight","ticket",
    "food","water","tea","coffee","lunch","dinner","break",
    "go","come","take","give","make","get","put","set","run","start",
    "stop","send","check","open","close","finish","complete","cancel",
    "ready","done","good","bad","right","wrong","new","old","big","small",
    "one","two","three","four","five","six","seven","eight","nine","ten",
}

# ── Known Hindi romanisations (ASCII but NOT English) ─────────────────────────
_HINDI_ROMANIZATIONS = {
    "mujhe","maine","tumhe","tumhara","mera","tera","humara","unka",
    "yeh","woh","kya","hai","hain","tha","thi","nahi","nahin",
    "karo","karna","kar","ho","hoga","hogi","honge","ko","se","ke","ka",
    "jana","aana","dena","lena","rehna","raho","jao","aao",
    "baat","kaam","log","din","kal","aaj","abhi","phir","bas","haan",
    "ek","do","teen","char","paanch","bhi","sirf","toh","yaar","bhai",
    "baar","saath","upar","neeche","andar","bahar","pehle","baad",
    "chahiye","chahti","chahta","achha","sahi","theek","bilkul",
    "zaroor","pakka","thoda","bahut","zyada","kam","accha",
    "kuch","matlab","samajh","lagta","lagti","rehta",
}

# ── Authentic Hindi grammar markers (NOT phonetic English) ────────────────────
# These words ONLY appear in real Hindi sentences, never in phonetic English
_HINDI_GRAMMAR = {
    "मैं","में","को","से","का","के","की","ने","पर","तक","साथ","कि",
    "है","हैं","था","थे","थी","हो","हूँ","हुए","हुई",
    "रहा","रही","रहे","जाना","आना","करना","होना","देना","लेना",
    "और","यह","वह","यहाँ","वहाँ","नहीं","लेकिन","तो","भी","जो",
    "कोई","कुछ","बहुत","अभी","अब","फिर","जब","क्योंकि",
    "पढ़","कर","जा","आ","दे","ले","हो",
}


# ── Helper: classify a Whisper-EN word ───────────────────────────────────────

def _is_english(word):
    clean = word.strip(" .,!?;:\"'").lower()
    if not clean:
        return True
    if not clean.isascii():
        return False
    if not clean.isalpha():
        return True
    if clean in _ENGLISH_VOCAB:
        return True
    if clean in _HINDI_ROMANIZATIONS:
        return False
    if len(clean) > 2 and any(
        p in clean for p in ("aa","ii","uu","kh","gh","ch","jh","sh","dh","bh","ng","ai","au")
    ):
        return False
    return True


# ── Helper: detect language boundary inside IndicConformer output ─────────────

def _find_boundary(indic_words):
    """
    Returns the index where authentic Hindi starts, or -1 if no clear boundary.

    Cases:
    1. Chunk starts with a Hindi grammar word → pure Hindi → return 0.
    2. >40% of words are grammar markers → Hindi-dominant → return 0.
    3. First grammar marker past 40% AND ≥2 tail markers → English→Hindi boundary.
    4. Otherwise → word-level Hinglish → return -1.
    """
    n = len(indic_words)
    if n < 2:
        return -1

    # Case 1: chunk opens with authentic Hindi
    if indic_words[0] in _HINDI_GRAMMAR:
        return 0

    # Case 2: Hindi-dominant chunk (>40% grammar words)
    grammar_count = sum(1 for w in indic_words if w in _HINDI_GRAMMAR)
    if grammar_count / n > 0.40:
        return 0

    # Case 3: clear English→Hindi boundary in second half
    if n < 4:
        return -1
    cutoff = int(n * 0.4)
    for i, word in enumerate(indic_words):
        if word in _HINDI_GRAMMAR and i >= cutoff:
            tail_grammar = sum(1 for w in indic_words[i:] if w in _HINDI_GRAMMAR)
            if tail_grammar >= 2:
                return i
    return -1


# ── Public merge function ─────────────────────────────────────────────────────

def merge(whisper_words, indic_text):
    """
    Merge Whisper-EN word list with IndicConformer transcript.

    Parameters
    ----------
    whisper_words : list[dict]  — each has {"word": str, "start": float, "end": float}
    indic_text    : str         — IndicConformer full transcript

    Returns
    -------
    str — best-effort merged transcript
    """
    if not whisper_words:
        return indic_text

    indic_words = indic_text.split()

    # ── Strategy 1: BOUNDARY (English chunk → Hindi chunk) ───────────────────
    boundary_idx = _find_boundary(indic_words)
    if boundary_idx != -1:
        return _boundary_merge(whisper_words, indic_words, boundary_idx)

    # ── Quick exit: zero Hindi romanisations ─────────────────────────────────
    hindi_count = sum(
        1 for w in whisper_words
        if w.get("word", "").strip().lower() in _HINDI_ROMANIZATIONS
    )
    if hindi_count == 0:
        # Whisper (forced en) found zero Hindi romanizations — could be:
        # (a) Genuinely English chunk → return Whisper text
        # (b) Pure Hindi chunk where Whisper TRANSLATED instead of romanising →
        #     return IndicConformer text
        #
        # Discriminator: genuine Hindi always contains grammar markers (है, में, मेरा…).
        # Phonetic English in Devanagari ("आई एम फ़्रोम") never does.
        if indic_words and any(w in _HINDI_GRAMMAR for w in indic_words):
            return indic_text
        # Genuinely English chunk
        return " ".join(
            w.get("word", "").strip() for w in whisper_words
            if w.get("word", "").strip()
        )

    # ── Strategy 2: WORD-LEVEL (Hinglish — mixed word-by-word) ───────────────
    return _wordlevel_merge(whisper_words, indic_words)


def _boundary_merge(whisper_words, indic_words, boundary_idx):
    """
    Audio switches language once: take Whisper-EN up to the transition,
    then IndicConformer's authentic Hindi tail.

    If boundary_idx == 0, the entire chunk is Hindi — skip Whisper entirely.
    """
    # Whole chunk is Hindi → IndicConformer is authoritative
    if boundary_idx == 0:
        return " ".join(indic_words)

    n_indic = len(indic_words)

    # Estimate timestamp of the language switch using word-count proportion
    boundary_ratio = boundary_idx / n_indic
    t_start = whisper_words[0].get("start", 0.0)
    t_end   = whisper_words[-1].get("end", 0.0)
    switch_time = t_start + boundary_ratio * (t_end - t_start)

    # Whisper EN words spoken before the switch → English part
    en_words = [
        w.get("word", "").strip()
        for w in whisper_words
        if w.get("end", 0.0) <= switch_time + 0.3 and w.get("word", "").strip()
    ]
    if not en_words:
        # No Whisper words before switch — fall back to full IndicConformer
        return " ".join(indic_words)

    hindi_tail = " ".join(indic_words[boundary_idx:])
    return (" ".join(en_words) + " " + hindi_tail).strip()


def _wordlevel_merge(whisper_words, indic_words):
    """
    True Hinglish: for each Whisper-EN word, keep if English, replace if
    romanised Indian. Always advances indic_idx to maintain 1-to-1 alignment
    (skipping IndicConformer's phonetic version of English words).
    """
    result = []
    indic_idx = 0

    for w in whisper_words:
        raw   = w.get("word", "")
        clean = raw.strip()

        if not clean.isascii():
            # Whisper already gave native script — keep and stay in sync
            result.append(clean)
            indic_idx += 1
            continue

        if _is_english(clean):
            result.append(clean)
            if indic_idx < len(indic_words):
                indic_idx += 1          # skip phonetic English in IndicConformer
        else:
            if indic_idx < len(indic_words):
                result.append(indic_words[indic_idx])
                indic_idx += 1
            else:
                result.append(clean)    # fallback

    # Append genuine extra Hindi words (IndicConformer found more than Whisper)
    result.extend(indic_words[indic_idx:])
    return " ".join(w for w in result if w)
