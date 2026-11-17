from __future__ import annotations

"""Narration and synchronized short-chunk subtitle generation for Scenecraft."""

import asyncio
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional


DEFAULT_VOICE = "en-US-AndrewMultilingualNeural"
DEFAULT_RATE = "+0%"
DEFAULT_PITCH = "-2Hz"

# Dramatic and suspense keywords for selective yellow highlighting
DRAMATIC_KEYWORDS = {
    # Numbers and time
    "30th", "30", "9:40", "nine-forty", "tonight", "midnight", "seconds", "minutes", "zero",
    # Physical/Suspense nouns
    "floor", "phone", "phones", "water", "shadow", "shadows", "blood", "stairwell", "stairs",
    "lock", "locks", "door", "doors", "knife", "blade", "window", "smoke", "fire", "alarm",
    "dead", "death", "body", "hallway", "corridor", "flat", "building", "elevator", "trap",
    "sound", "noise", "breath", "breathing", "footsteps", "silence", "darkness", "dark",
    # Action verbs
    "screams", "screaming", "locked", "scream", "running", "run", "chase", "chasing", "fell",
    "fall", "falling", "stops", "stopped", "knock", "knocking", "banging", "breaks", "broken",
    "drowning", "drown", "freeze", "freezing", "frozen", "kills", "killed", "escaped", "escape",
    # Intense adjectives
    "worst", "terrified", "silent", "cold", "alone", "trapped", "hollow", "unseen", "empty"
}


def get_audio_duration(file_path: Path) -> float:
    """Return duration of audio file in seconds using ffprobe."""
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(file_path),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return float(res.stdout.strip())


def synthesize_scene_narration(
    text: str,
    out_audio: Path,
    out_vtt: Path,
    voice: str = "default",
    rate: str = DEFAULT_RATE,
    pitch: str = DEFAULT_PITCH,
    emotion: Optional[str] = None,
    tension_level: Optional[int] = None,
    base_speed: Optional[float] = None,
    delivery_style: Optional[str] = None,
) -> float:
    """Generate audio and subtitle file for scene, returning duration in seconds."""
    out_audio.parent.mkdir(parents=True, exist_ok=True)
    out_vtt.parent.mkdir(parents=True, exist_ok=True)

    if out_audio.is_file() and out_audio.stat().st_size > 0 and out_vtt.is_file() and out_vtt.stat().st_size > 0:
        return get_audio_duration(out_audio)

    # 1. Primary check: VoiceStudio Permanent Narrator integration
    from scenecraft.voicestudio_client import VoiceStudioClient, get_scene_delivery_params
    vs_client = VoiceStudioClient()
    v_lower = voice.lower()
    hex_id = bool(re.match(r"^[0-9a-f]{8}$", v_lower))

    is_voicestudio_target = (
        voice in ["default", "permanent", DEFAULT_VOICE, "voicestudio", "candidate", "rooftop"]
        or v_lower.startswith("voicestudio")
        or v_lower.startswith("vs:")
        or hex_id
    )

    if is_voicestudio_target:
        if not vs_client.is_available():
            raise RuntimeError(
                f"VoiceStudio is required for profile '{voice}' but the VoiceStudio service is not available on port 3900. "
                "Per user policy: Scenecraft will not silently switch to another TTS provider. Start VoiceStudio to proceed."
            )

        if ":" in voice:
            vs_voice = voice.split(":", 1)[1].strip()
        elif hex_id:
            vs_voice = v_lower
        elif v_lower in ["permanent", "default", "candidate", "rooftop", "rooftop_survivor"]:
            vs_voice = "6f7af622"
        elif v_lower in ["documentarian"]:
            vs_voice = "b77c1cca"
        else:
            vs_voice = "6f7af622"
        if not vs_voice:
            vs_voice = "6f7af622"

        delivery = get_scene_delivery_params(
            emotion=emotion,
            tension_level=tension_level,
            base_speed=base_speed,
            delivery_style=delivery_style,
        )
        try:
            dur = vs_client.generate_speech(
                text=text,
                output_path=out_audio,
                voice=vs_voice,
                speed=delivery["speed"],
                instructions=delivery["instructions"],
                response_format="wav",
            )
        except Exception as err:
            raise RuntimeError(
                f"VoiceStudio synthesis failed for profile '{vs_voice}': {err}. "
                "Per user policy: Scenecraft will not silently switch to another TTS provider."
            ) from err

        def _fmt_vtt_ts(secs: float) -> str:
            h = int(secs // 3600)
            m = int((secs % 3600) // 60)
            s = secs % 60
            return f"{h:02d}:{m:02d}:{s:06.3f}"

        words_list = text.split()
        total_words = len(words_list)
        chunk_size = 4
        chunks = [words_list[i:i + chunk_size] for i in range(0, total_words, chunk_size)]
        n_chunks = max(1, len(chunks))
        with open(out_vtt, "w", encoding="utf-8") as f:
            f.write("WEBVTT\n\n")
            for ci, chunk in enumerate(chunks):
                t_start = ci * dur / n_chunks
                t_end = (ci + 1) * dur / n_chunks
                f.write(f"{_fmt_vtt_ts(t_start)} --> {_fmt_vtt_ts(t_end)}\n")
                f.write(" ".join(chunk) + "\n\n")
        return dur

    # Check for Kokoro voice integration
    v_clean = voice.lower().replace("kokoro_", "").strip()
    from scenecraft.kokoro_engine import ALL_TEST_VOICES
    if v_clean in ALL_TEST_VOICES or voice.lower().startswith("kokoro_"):
        from scenecraft.kokoro_engine import KokoroEngine
        engine = KokoroEngine()
        voice_id = v_clean if v_clean in ALL_TEST_VOICES else "am_onyx"
        dur = engine.synthesize(text=text, output_wav=out_audio, voice=voice_id)

        def _fmt_vtt_ts(secs: float) -> str:
            h = int(secs // 3600)
            m = int((secs % 3600) // 60)
            s = secs % 60
            return f"{h:02d}:{m:02d}:{s:06.3f}"

        words_list = text.split()
        total_words = len(words_list)
        chunk_size = 4
        chunks = [words_list[i:i + chunk_size] for i in range(0, total_words, chunk_size)]
        n_chunks = max(1, len(chunks))
        with open(out_vtt, "w", encoding="utf-8") as f:
            f.write("WEBVTT\n\n")
            for ci, chunk in enumerate(chunks):
                t_start = ci * dur / n_chunks
                t_end = (ci + 1) * dur / n_chunks
                f.write(f"{_fmt_vtt_ts(t_start)} --> {_fmt_vtt_ts(t_end)}\n")
                f.write(" ".join(chunk) + "\n\n")
        return dur

    # Check for ElevenLabs voice integration
    v_clean = voice.lower().replace("eleven_", "").strip()
    from scenecraft.elevenlabs_client import ElevenLabsClient, CURATED_NARRATIVE_VOICES
    el_client = ElevenLabsClient()

    if el_client.is_configured() and (v_clean in CURATED_NARRATIVE_VOICES or len(voice) >= 20):
        voice_id = CURATED_NARRATIVE_VOICES[v_clean]["voice_id"] if v_clean in CURATED_NARRATIVE_VOICES else voice
        el_client.generate_narration(text=text, output_path=out_audio, voice_id=voice_id)
        dur = get_audio_duration(out_audio)
        # Write a proper word-distributed VTT as fallback (Whisper will override this in generate_scene_ass_dialogues)
        # Use correct H:MM:SS.mmm timestamp format to avoid malformed VTT when dur > 60s
        def _fmt_vtt_ts(secs: float) -> str:
            h = int(secs // 3600)
            m = int((secs % 3600) // 60)
            s = secs % 60
            return f"{h:02d}:{m:02d}:{s:06.3f}"

        # Distribute text into ~4-word sentence chunks evenly across duration
        words_list = text.split()
        total_words = len(words_list)
        chunk_size = 4
        chunks = [words_list[i:i + chunk_size] for i in range(0, total_words, chunk_size)]
        n_chunks = len(chunks)
        with open(out_vtt, "w", encoding="utf-8") as f:
            f.write("WEBVTT\n\n")
            for ci, chunk in enumerate(chunks):
                t_start = ci * dur / n_chunks
                t_end = (ci + 1) * dur / n_chunks
                f.write(f"{_fmt_vtt_ts(t_start)} --> {_fmt_vtt_ts(t_end)}\n")
                f.write(" ".join(chunk) + "\n\n")
        return dur

    edge_bin = shutil.which("edge-tts") or "/home/varun/.local/bin/edge-tts"
    cmd = [
        edge_bin,
        "--voice", voice,
        "--rate", rate,
        "--pitch", pitch,
        "--text", text,
        "--write-media", str(out_audio),
        "--write-subtitles", str(out_vtt),
    ]

    import time
    last_err = ""
    for attempt in range(4):
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0 and out_audio.is_file() and out_audio.stat().st_size > 0:
            return get_audio_duration(out_audio)
        last_err = res.stderr or res.stdout
        time.sleep(1.2 * (attempt + 1))

    raise RuntimeError(f"edge-tts failed after 4 retries:\n{last_err}")


def _get_whisper_python() -> Optional[str]:
    """Find python interpreter capable of running faster-whisper."""
    try:
        import faster_whisper  # type: ignore
        return sys.executable
    except ImportError:
        pass

    candidates = [
        "/home/varun/.config/VoiceStudio/runtime/project/.venv/bin/python",
        "/home/varun/Desktop/ClipForge/.venv/bin/python3",
        "/home/varun/.local/share/pipx/venvs/faster-whisper/bin/python",
    ]
    for c in candidates:
        if os.path.isfile(c) and os.access(c, os.X_OK):
            return c
    return None


def extract_word_timestamps(audio_path: Path) -> List[Dict[str, Any]]:
    """Extract word-level timestamps using faster-whisper with disk caching."""
    words_file = Path(audio_path).with_suffix(".words.json")
    if words_file.is_file():
        try:
            with open(words_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if data:
                    return data
        except Exception:
            pass

    whisper_py = _get_whisper_python()
    if whisper_py:
        script = (
            "import sys, json\n"
            "from faster_whisper import WhisperModel\n"
            "model = WhisperModel('base', device='cpu', compute_type='int8')\n"
            "segments, _ = model.transcribe(sys.argv[1], word_timestamps=True)\n"
            "words = []\n"
            "for segment in segments:\n"
            "    for word in segment.words:\n"
            "        words.append({'word': word.word.strip(), 'start': float(round(word.start, 2)), 'end': float(round(word.end, 2))})\n"
            "print(json.dumps(words))\n"
        )
        try:
            res = subprocess.run(
                [whisper_py, "-c", script, str(audio_path)],
                capture_output=True,
                text=True,
                check=True,
                timeout=45,
            )
            data = json.loads(res.stdout)
            if data:
                try:
                    with open(words_file, "w", encoding="utf-8") as f:
                        json.dump(data, f)
                except Exception:
                    pass
                return data
        except Exception as e:
            print(f"[Subtitles] Whisper extraction failed ({e}), falling back to proportional timing")

    return []


def _format_ass_time(seconds: float) -> str:
    """Format seconds into ASS timestamp: H:MM:SS.cs with exact centisecond precision."""
    total_cs = max(0, int(round(seconds * 100)))
    cs = total_cs % 100
    total_s = total_cs // 100
    s = total_s % 60
    total_m = total_s // 60
    m = total_m % 60
    h = total_m // 60
    return f"{h:d}:{m:02d}:{s:02d}.{cs:02d}"


def _parse_ass_time(ts: str) -> float:
    """Parse ASS timestamp H:MM:SS.cs into seconds."""
    parts = ts.strip().split(":")
    if len(parts) != 3:
        return 0.0
    h = int(parts[0])
    m = int(parts[1])
    s = float(parts[2])
    return h * 3600.0 + m * 60.0 + s


def _sanitize_word_timestamps(words: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Clean word stream to enforce strictly non-overlapping, positive duration words."""
    clean_words = []
    for w in words:
        txt = w.get("word", "").strip()
        if not txt:
            continue
        try:
            st = float(w["start"])
            en = float(w["end"])
        except (KeyError, ValueError, TypeError):
            continue
        clean_words.append({"word": txt, "start": max(0.0, st), "end": max(0.0, en)})

    if not clean_words:
        return []

    # Sort by start timestamp
    clean_words.sort(key=lambda x: (x["start"], x["end"]))

    # Enforce strictly monotonic, non-overlapping timestamps
    for i in range(len(clean_words)):
        w = clean_words[i]
        if i > 0:
            prev_end = clean_words[i - 1]["end"]
            if w["start"] < prev_end:
                w["start"] = prev_end
        if w["end"] <= w["start"]:
            w["end"] = w["start"] + 0.08
        if i < len(clean_words) - 1:
            next_start = clean_words[i + 1]["start"]
            if w["end"] > next_start:
                if next_start > w["start"] + 0.04:
                    w["end"] = next_start
                else:
                    clean_words[i + 1]["start"] = w["end"]
                    if clean_words[i + 1]["end"] <= clean_words[i + 1]["start"]:
                        clean_words[i + 1]["end"] = clean_words[i + 1]["start"] + 0.08

    return clean_words


def _smart_chunk_words(words: List[Dict[str, Any]], max_words: int = 4) -> List[List[Dict[str, Any]]]:
    """Group word stream into natural 2-4 (max 5) word subtitle events broken at pauses."""
    words = _sanitize_word_timestamps(words)
    if not words:
        return []

    # 1. Partition by sentence boundaries
    sentences = []
    curr_sent = []
    for w in words:
        curr_sent.append(w)
        if re.search(r"[.!?]$", w["word"]):
            sentences.append(curr_sent)
            curr_sent = []
    if curr_sent:
        sentences.append(curr_sent)

    all_chunks = []
    for sent in sentences:
        # 2. Sub-divide sentence by commas, colons, or dashes
        clauses = []
        curr_clause = []
        for w in sent:
            curr_clause.append(w)
            if re.search(r"[,;—:–]$", w["word"]):
                clauses.append(curr_clause)
                curr_clause = []
        if curr_clause:
            clauses.append(curr_clause)

        # 3. Partition clause evenly into chunks of <= max_words
        for clause in clauses:
            n = len(clause)
            if n <= max_words:
                all_chunks.append(clause)
            else:
                num_parts = (n + max_words - 1) // max_words
                k, m = divmod(n, num_parts)
                idx = 0
                for i in range(num_parts):
                    part_len = k + (1 if i < m else 0)
                    all_chunks.append(clause[idx:idx + part_len])
                    idx += part_len

    return all_chunks


def _chunk_to_word_level_ass_dialogues(
    chunk: List[Dict[str, Any]],
    time_offset: float = 0.0,
    next_chunk_start: Optional[float] = None,
) -> List[str]:
    """Generate word-by-word highlighted ASS dialogue events for a 2-4 word chunk."""
    if not chunk:
        return []

    # Dynamic font sizing based on chunk length
    total_chars = sum(len(w.get("word", "")) for w in chunk)
    if total_chars <= 14:
        size_tag = "{\\fs52}"
    elif total_chars > 28:
        size_tag = "{\\fs44}"
    else:
        size_tag = "{\\fs48}"

    chunk_start = chunk[0]["start"] + time_offset
    chunk_end = chunk[-1]["end"] + time_offset
    if chunk_end - chunk_start < 0.35:
        proposed_end = chunk_start + 0.35
        if next_chunk_start is None or proposed_end <= next_chunk_start:
            chunk_end = proposed_end
        elif next_chunk_start > chunk_start:
            chunk_end = next_chunk_start

    dialogues = []
    n = len(chunk)

    for active_idx in range(n):
        w_start = chunk[active_idx]["start"] + time_offset
        if active_idx < n - 1:
            w_end = chunk[active_idx + 1]["start"] + time_offset
            if w_end <= w_start:
                w_end = w_start + 0.05
        else:
            w_end = chunk_end
            if next_chunk_start is not None and w_end > next_chunk_start:
                w_end = next_chunk_start
            if w_end <= w_start:
                w_end = w_start + 0.05

        # Build words with active word highlighted in bold yellow (&H0000FFFF&)
        formatted_words = []
        for idx, w in enumerate(chunk):
            word_text = w["word"]
            clean = re.sub(r"[^a-zA-Z0-9]", "", word_text).lower()
            is_dramatic = clean in DRAMATIC_KEYWORDS or clean.isdigit()

            m = re.match(r"^([^a-zA-Z0-9]*)(.*?)([^a-zA-Z0-9]*)$", word_text)
            lead, core, trail = m.groups() if m else ("", word_text, "")

            if idx == active_idx:
                # Active word: bright warm yellow with bold pop
                formatted_words.append(f"{lead}{{\\c&H0000FFFF&\\b1}}{core}{{\\c&H00FFFFFF&\\b0}}{trail}")
            elif is_dramatic:
                # Selective keyword emphasis in light gold/italic
                formatted_words.append(f"{lead}{{\\c&H0028A0DF&}}{core}{{\\c&H00FFFFFF&}}{trail}")
            else:
                formatted_words.append(f"{lead}{core}{trail}")

        # Wrap to two lines only if text is genuinely long (> 28 chars or >= 5 words)
        if len(formatted_words) >= 5 or total_chars > 28:
            mid = len(formatted_words) // 2
            line1 = " ".join(formatted_words[:mid])
            line2 = " ".join(formatted_words[mid:])
            line_text = f"{size_tag}{line1}\\N{line2}"
        else:
            line_text = f"{size_tag}{' '.join(formatted_words)}"

        start_str = _format_ass_time(w_start)
        end_str = _format_ass_time(w_end)
        dialogues.append(f"Dialogue: 0,{start_str},{end_str},Default,,0,0,0,,{line_text}")

    return dialogues


def _chunk_to_ass_dialogue(chunk: List[Dict[str, Any]], time_offset: float = 0.0) -> str:
    """Format a 3-5 word chunk into an ASS dialogue line with yellow keyword styling."""
    dialogues = _chunk_to_word_level_ass_dialogues(chunk, time_offset=time_offset)
    return dialogues[0] if dialogues else ""


def generate_scene_ass_dialogues(audio_path: Path, vtt_path: Path, time_offset: float) -> List[str]:
    """Generate high-precision short-chunk subtitle dialogues for an audio file."""
    words = extract_word_timestamps(audio_path)
    if words:
        chunks = _smart_chunk_words(words, max_words=4)
        dialogues = []
        for idx, c in enumerate(chunks):
            if c:
                next_c_start = (chunks[idx + 1][0]["start"] + time_offset) if idx < len(chunks) - 1 and chunks[idx + 1] else None
                dialogues.extend(_chunk_to_word_level_ass_dialogues(c, time_offset=time_offset, next_chunk_start=next_c_start))
        return dialogues

    # Fallback to VTT parsing if whisper was unavailable
    return _vtt_to_ass_dialogues(vtt_path, time_offset=time_offset)


def generate_full_narration(
    scenes: List[Dict[str, Any]],
    output_dir: Path,
    voice: str = DEFAULT_VOICE,
    rate: str = DEFAULT_RATE,
    pitch: str = DEFAULT_PITCH,
    aspect_ratio: str = "16:9",
    base_speed: Optional[float] = None,
    delivery_style: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], Path, Path]:
    """Generate narration for all scenes, concatenate audio, and produce aligned subtitles.

    Returns:
        (updated_scenes_with_timings, merged_audio_path, merged_ass_path)
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    merged_audio = output_dir / "full_narration.wav"
    merged_ass = output_dir / "subtitles.ass"

    # Fast path: If all scene audios, merged audio, and subtitles already exist, reuse them
    all_scenes_cached = True
    for idx in range(1, len(scenes) + 1):
        sa = output_dir / f"scene_{idx:02d}.mp3"
        if not (sa.is_file() and sa.stat().st_size > 5000):
            all_scenes_cached = False
            break

    if all_scenes_cached and merged_audio.is_file() and merged_audio.stat().st_size > 50000 and merged_ass.is_file():
        updated_scenes = []
        current_time = 0.0
        for idx, scene in enumerate(scenes, start=1):
            sa = output_dir / f"scene_{idx:02d}.mp3"
            dur = get_audio_duration(sa)
            scene_dur = dur + 0.4
            updated_scenes.append({
                **scene,
                "audio_path": sa,
                "start_time": current_time,
                "end_time": current_time + scene_dur,
                "duration": scene_dur,
            })
            current_time += scene_dur
        return updated_scenes, merged_audio, merged_ass

    scene_audios = []
    updated_scenes = []

    current_time = 0.0
    ass_dialogues = []

    for idx, scene in enumerate(scenes, start=1):
        narration_text = scene.get("narration", "").strip()
        if not narration_text:
            continue

        scene_audio = output_dir / f"scene_{idx:02d}.mp3"
        scene_vtt = output_dir / f"scene_{idx:02d}.vtt"

        if scene_audio.is_file() and scene_audio.stat().st_size > 5000 and scene_vtt.is_file():
            duration = get_audio_duration(scene_audio)
        else:
            duration = synthesize_scene_narration(
                narration_text,
                scene_audio,
                scene_vtt,
                voice=voice,
                rate=rate,
                pitch=pitch,
                emotion=scene.get("emotion"),
                tension_level=scene.get("tension_level"),
                base_speed=base_speed,
                delivery_style=delivery_style,
            )
        start_time = current_time
        # Add 0.4s breathing room buffer at end of each scene
        scene_duration = duration + 0.4
        end_time = start_time + scene_duration

        updated_scenes.append({
            **scene,
            "audio_path": scene_audio,
            "start_time": start_time,
            "end_time": end_time,
            "duration": scene_duration,
        })
        scene_audios.append((scene_audio, duration, 0.4))

        # Generate synchronized short-chunk subtitles shifted by scene start_time
        scene_subs = generate_scene_ass_dialogues(scene_audio, scene_vtt, time_offset=start_time)
        ass_dialogues.extend(scene_subs)

        current_time = end_time

    # Merge audio files with silence buffers using ffmpeg
    merged_audio = output_dir / "full_narration.wav"
    _merge_scene_audios(scene_audios, merged_audio)

    # Build stylized ASS subtitle file tailored to aspect ratio
    merged_ass = output_dir / "subtitles.ass"
    _write_styled_ass(ass_dialogues, merged_ass, aspect_ratio=aspect_ratio)

    return updated_scenes, merged_audio, merged_ass


def _merge_scene_audios(scene_audios: List[Tuple[Path, float, float]], out_path: Path):
    """Concatenate scene audios with padded silence buffers."""
    filter_parts = []
    inputs = []
    for idx, (path, dur, pad) in enumerate(scene_audios):
        inputs.extend(["-i", str(path)])
        # Pad each audio stream with pad seconds of silence
        filter_parts.append(f"[{idx}:a]apad=pad_dur={pad:.2f}[a{idx}]")

    concat_inputs = "".join(f"[a{i}]" for i in range(len(scene_audios)))
    filter_complex = f"{';'.join(filter_parts)};{concat_inputs}concat=n={len(scene_audios)}:v=0:a=1[outa]"

    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", filter_complex,
        "-map", "[outa]",
        "-c:a", "pcm_s16le",
        str(out_path)
    ]
    subprocess.run(cmd, check=True, capture_output=True)


def _vtt_to_ass_dialogues(vtt_path: Path, time_offset: float) -> List[str]:
    """Fallback: Parse VTT file and convert cues to short-chunk non-overlapping ASS dialogues."""
    dialogues = []
    if not vtt_path.is_file():
        return dialogues

    content = vtt_path.read_text(encoding="utf-8")
    blocks = re.split(r"\n\s*\n", content.strip())

    time_pat = re.compile(r"(\d{2}):(\d{2}):(\d{2})[,.](\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2})[,.](\d{3})")

    for block in blocks:
        lines = [l.strip() for l in block.splitlines() if l.strip()]
        if not lines:
            continue

        match = None
        text_lines = []
        for line in lines:
            m = time_pat.search(line)
            if m:
                match = m
            elif match and not line.isdigit() and line != "WEBVTT":
                text_lines.append(line)

        if match and text_lines:
            sh, sm, ss, sms = map(int, match.group(1, 2, 3, 4))
            eh, em, es, ems = map(int, match.group(5, 6, 7, 8))
            start_s = sh * 3600 + sm * 60 + ss + sms / 1000.0 + time_offset
            end_s = eh * 3600 + em * 60 + es + ems / 1000.0 + time_offset

            sub_text = " ".join(text_lines).replace("\n", " ").strip()
            if not sub_text:
                continue

            words = sub_text.split()
            if not words:
                continue

            chunk_size = 4
            word_chunks = [words[i:i + chunk_size] for i in range(0, len(words), chunk_size)]
            total_words = len(words)
            cue_dur = max(0.4, end_s - start_s)

            c_curr = start_s
            for c_idx, c_words in enumerate(word_chunks):
                c_ratio = len(c_words) / total_words
                c_dur = cue_dur * c_ratio
                c_start = c_curr
                c_end = min(end_s, c_start + c_dur)
                if c_idx == len(word_chunks) - 1:
                    c_end = end_s
                if c_end <= c_start:
                    c_end = c_start + 0.10

                phrase_str = " ".join(c_words)
                start_str = _format_ass_time(c_start)
                end_str = _format_ass_time(c_end)
                dialogues.append(f"Dialogue: 0,{start_str},{end_str},Default,,0,0,0,,{{\\fs48}}{phrase_str}")
                c_curr = c_end

    return dialogues


def _sanitize_ass_dialogue_events(dialogues: List[str]) -> List[str]:
    """Parse, sort, de-overlap, and clean ASS Dialogue lines.

    Guarantees:
    1. Strictly non-overlapping events: previous subtitle ends before/at next starts.
    2. Start < End always (no zero-duration or negative events).
    3. Chronological sorting by start timestamp.
    4. Eliminates duplicate simultaneous events.
    """
    if not dialogues:
        return []

    parsed = []
    for line in dialogues:
        line_clean = line.strip()
        if not line_clean.startswith("Dialogue:"):
            continue
        parts = line_clean.split(",", 9)
        if len(parts) < 10:
            continue
        try:
            start_sec = _parse_ass_time(parts[1])
            end_sec = _parse_ass_time(parts[2])
        except (ValueError, IndexError):
            continue

        text = parts[9]
        if not text.strip():
            continue

        parsed.append({
            "start": start_sec,
            "end": end_sec,
            "layer": parts[0],
            "style": parts[3],
            "name": parts[4],
            "margin_l": parts[5],
            "margin_r": parts[6],
            "margin_v": parts[7],
            "effect": parts[8],
            "text": text,
        })

    if not parsed:
        return []

    # Sort strictly by start time
    parsed.sort(key=lambda x: (x["start"], x["end"]))

    # Enforce non-overlapping invariant
    for i in range(len(parsed)):
        s = parsed[i]["start"]
        e = parsed[i]["end"]
        if e <= s:
            e = s + 0.05

        if i < len(parsed) - 1:
            next_s = parsed[i + 1]["start"]
            # If current cue overlaps next cue start, clamp current end to next start
            if e > next_s:
                e = next_s
            # If next start is <= current start
            if next_s <= s:
                parsed[i + 1]["start"] = s + 0.05
                next_s = parsed[i + 1]["start"]
                e = next_s

        if e <= s:
            e = s + 0.05

        parsed[i]["start"] = s
        parsed[i]["end"] = e

    # Format into valid ASS Dialogue lines with precise centiseconds
    result = []
    for ev in parsed:
        s_str = _format_ass_time(ev["start"])
        e_str = _format_ass_time(ev["end"])
        if s_str == e_str:
            e_str = _format_ass_time(ev["start"] + 0.02)
        dlg = (
            f"{ev['layer']},{s_str},{e_str},{ev['style']},{ev['name']},"
            f"{ev['margin_l']},{ev['margin_r']},{ev['margin_v']},{ev['effect']},{ev['text']}"
        )
        result.append(dlg)

    return result


def _write_styled_ass(dialogue_lines: List[str], out_path: Path, aspect_ratio: str = "16:9"):
    """Write stylized ASS subtitle file optimized for either 16:9 horizontal or 9:16 vertical shorts.

    Safe areas:
    - 16:9: PlayResX=1920, PlayResY=1080, MarginV=90, Fontsize=44
    - 9:16: PlayResX=1080, PlayResY=1920, MarginV=340, Fontsize=48
    """
    clean_lines = _sanitize_ass_dialogue_events(dialogue_lines)
    if aspect_ratio == "16:9":
        header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,44,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,1.2,0,1,4,2.0,2,80,80,90,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    else:
        # 9:16 Shorts/Reels portrait safe-zone: Fontsize 48, strong outline 4.5, MarginV 340 (tested safe zone above platform UI overlay)
        header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Montserrat,48,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,1.2,0,1,4.5,1.5,2,70,70,340,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    content = header + "\n".join(clean_lines) + "\n"
    out_path.write_text(content, encoding="utf-8")
