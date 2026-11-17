"""Tests for subtitle timing, word-level chunking, and non-overlapping ASS generation."""

import unittest
from pathlib import Path
from scenecraft.narration import (
    _format_ass_time,
    _parse_ass_time,
    _sanitize_word_timestamps,
    _smart_chunk_words,
    _chunk_to_word_level_ass_dialogues,
    _sanitize_ass_dialogue_events,
    _write_styled_ass,
)


class TestSubtitleTimingAndDeOverlap(unittest.TestCase):
    def test_format_and_parse_ass_time(self):
        self.assertEqual(_format_ass_time(0.0), "0:00:00.00")
        self.assertEqual(_format_ass_time(1.25), "0:00:01.25")
        self.assertEqual(_format_ass_time(59.996), "0:01:00.00")
        self.assertEqual(_format_ass_time(3661.05), "1:01:01.05")

        self.assertAlmostEqual(_parse_ass_time("0:00:01.25"), 1.25, places=2)
        self.assertAlmostEqual(_parse_ass_time("1:01:01.05"), 3661.05, places=2)

    def test_sanitize_word_timestamps_removes_inversion_and_overlap(self):
        raw_words = [
            {"word": "a", "start": 1.36, "end": 1.42},
            {"word": "colossal", "start": 1.40, "end": 2.00},  # Overlaps previous end
            {"word": "wall", "start": 2.05, "end": 2.02},      # Negative duration
            {"word": "of", "start": 2.01, "end": 2.30},        # Starts before previous
        ]
        clean = _sanitize_word_timestamps(raw_words)
        self.assertEqual(len(clean), 4)

        for i in range(len(clean)):
            self.assertGreater(clean[i]["end"], clean[i]["start"])
            if i < len(clean) - 1:
                self.assertLessEqual(clean[i]["end"], clean[i + 1]["start"])

    def test_chunk_to_word_level_ass_dialogues_never_overlaps(self):
        chunk = [
            {"word": "a", "start": 1.36, "end": 1.42},
            {"word": "colossal", "start": 1.42, "end": 2.00},
            {"word": "wall", "start": 2.00, "end": 2.22},
            {"word": "of", "start": 2.22, "end": 2.48},
        ]
        dialogues = _chunk_to_word_level_ass_dialogues(chunk, time_offset=15.83, next_chunk_start=18.50)
        self.assertEqual(len(dialogues), 4)

        # Check consecutive cues
        for i in range(len(dialogues) - 1):
            p1 = dialogues[i].split(",", 9)
            p2 = dialogues[i + 1].split(",", 9)
            end1 = _parse_ass_time(p1[2])
            start2 = _parse_ass_time(p2[1])
            self.assertLessEqual(end1, start2, f"Cue {i} end ({end1}) exceeds Cue {i+1} start ({start2})")

    def test_sanitize_ass_dialogue_events_enforces_clean_transitions(self):
        bad_dialogues = [
            "Dialogue: 0,0:00:17.19,0:00:17.34,Default,,0,0,0,,a colossal wall of",
            "Dialogue: 0,0:00:17.25,0:00:17.83,Default,,0,0,0,,a colossal wall of",  # Overlaps!
            "Dialogue: 0,0:00:17.83,0:00:18.05,Default,,0,0,0,,a colossal wall of",
        ]
        sanitized = _sanitize_ass_dialogue_events(bad_dialogues)
        self.assertEqual(len(sanitized), 3)

        for i in range(len(sanitized) - 1):
            p1 = sanitized[i].split(",", 9)
            p2 = sanitized[i + 1].split(",", 9)
            end1 = _parse_ass_time(p1[2])
            start2 = _parse_ass_time(p2[1])
            self.assertLessEqual(end1, start2)


if __name__ == "__main__":
    unittest.main()
