import sys, os, tempfile, time
sys.path.insert(0, os.path.dirname(__file__))

# Force UTF-8 output so Devanagari prints correctly on Windows
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

import soundfile as sf
from config import INDIC_MODEL_PATH, WHISPER_MODEL_SIZE
from models.indic_model import IndicModel
from models.whisper_model import WhisperModel
from pipeline.vad import VADSplitter
from pipeline.router import Router
from pipeline.assembler import Assembler

AUDIO = r"C:\Users\Dhruv Garg\Downloads\test5.wav"

# ── Model load times ─────────────────────────────────────────────────────────
t0 = time.perf_counter()
print("Loading models...")
indic   = IndicModel(INDIC_MODEL_PATH);   print(f"  IndicConformer loaded  : {time.perf_counter()-t0:.2f}s")
t1 = time.perf_counter()
whisper = WhisperModel(WHISPER_MODEL_SIZE); print(f"  Whisper loaded         : {time.perf_counter()-t1:.2f}s")
t2 = time.perf_counter()
vad     = VADSplitter();                   print(f"  Silero VAD loaded      : {time.perf_counter()-t2:.2f}s")
router  = Router(whisper, indic)
asm     = Assembler()
print(f"  Total model load time  : {time.perf_counter()-t0:.2f}s")

# ── Audio info ───────────────────────────────────────────────────────────────
audio, sr = sf.read(AUDIO)
if audio.ndim == 2:
    audio = audio.mean(axis=1)
audio_duration = len(audio) / sr
print(f"\nAudio duration: {audio_duration:.2f}s")

tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
sf.write(tmp.name, audio, sr)
tmp.close()

# ── VAD latency ──────────────────────────────────────────────────────────────
t_vad = time.perf_counter()
print("\nRunning VAD split...")
chunks = vad.split(tmp.name)
vad_ms = (time.perf_counter() - t_vad) * 1000
print(f"  {len(chunks)} chunk(s)  |  VAD latency: {vad_ms:.0f}ms")

# ── Per-chunk transcription latency ──────────────────────────────────────────
results = []
t_pipeline_start = time.perf_counter()

for i, (start, end, cpath) in enumerate(chunks):
    chunk_dur = end - start
    t_chunk = time.perf_counter()
    print(f"\n  chunk {i+1}: {start:.2f}s - {end:.2f}s  (duration: {chunk_dur:.2f}s)")
    text, info = router.process(cpath)
    chunk_ms = (time.perf_counter() - t_chunk) * 1000
    route = info["route"]
    lang  = info["lang"]
    conf  = info["confidence"]
    rtf   = (chunk_ms / 1000) / chunk_dur   # Real-Time Factor
    print(f"    route={route}  lang={lang}  conf={conf:.0%}")
    print(f"    latency: {chunk_ms:.0f}ms  |  RTF: {rtf:.2f}x  {'✅ real-time' if rtf < 1.0 else '⚠️  slower than real-time'}")
    print(f"    text : {text}")
    results.append((start, end, text, info))

total_inference_ms = (time.perf_counter() - t_pipeline_start) * 1000

transcript, summary = asm.assemble(results)

# ── Summary ──────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("FINAL TRANSCRIPT:")
print(transcript)
print()
print("ROUTE SUMMARY:", summary)
print()
print("── LATENCY SUMMARY ─────────────────────────────────────")
print(f"  Audio duration      : {audio_duration:.2f}s")
print(f"  VAD split           : {vad_ms:.0f}ms")
print(f"  Transcription total : {total_inference_ms:.0f}ms")
print(f"  Full pipeline       : {vad_ms + total_inference_ms:.0f}ms")
print(f"  Overall RTF         : {(vad_ms + total_inference_ms) / 1000 / audio_duration:.2f}x")
print(f"  (RTF < 1.0 = faster than real-time, RTF > 1.0 = slower)")
print("="*60)

os.unlink(tmp.name)
for _, _, cp in chunks:
    if cp != tmp.name:
        try:
            os.unlink(cp)
        except OSError:
            pass
