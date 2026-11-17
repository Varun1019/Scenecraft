"""Tests for Upgrade 2: Visual Intelligence, Multi-Angle References, and Word-Level Subtitles."""

import unittest
from pathlib import Path
from storyforge.visual_intelligence import (
    get_character_reference_for_shot,
    CinematicPromptEngine,
    CharacterSpec,
    ImageQualityController,
    OFFICIAL_CLOSE_UP_REF,
    OFFICIAL_BACK_VIEW_REF,
    OFFICIAL_THREE_QUARTER_REF,
    OFFICIAL_FULL_BODY_REF,
)
from storyforge.flow_client import compute_image_content_hash
from storyforge.narration import (
    _chunk_to_word_level_ass_dialogues,
    _format_ass_time,
)


class TestUpgrade2Visual(unittest.TestCase):

    def test_multi_angle_reference_resolution(self):
        """Verify that shot types resolve to appropriate reference angle images."""
        close_ref = get_character_reference_for_shot("CLOSE_UP_INTENSE")
        self.assertEqual(close_ref, OFFICIAL_CLOSE_UP_REF)

        back_ref = get_character_reference_for_shot("OVER_THE_SHOULDER")
        self.assertEqual(back_ref, OFFICIAL_BACK_VIEW_REF)

        three_ref = get_character_reference_for_shot("MEDIUM_ACTION")
        self.assertEqual(three_ref, OFFICIAL_THREE_QUARTER_REF)

        wide_ref = get_character_reference_for_shot("WIDE_ESTABLISHING")
        self.assertEqual(wide_ref, OFFICIAL_FULL_BODY_REF)

    def test_cinematic_prompt_engine_depth_and_pose(self):
        """Verify prompt builder enriches prompts with pose, composition depth, and narrative purpose."""
        engine = CinematicPromptEngine()
        char = CharacterSpec()
        prompt, shot_type = engine.build_scene_prompt(
            scene_idx=1,
            total_scenes=5,
            title="The Knock",
            narration="You reach for the door handle as the lock rattles.",
            visual_action="Reaching cautiously for the vibrating metal deadbolt.",
            character=char,
            emotion="SUSPENSE",
            aspect_ratio="9:16",
        )
        self.assertIn("The Wanderer", prompt)
        self.assertIn("Character Pose & Expression", prompt)
        self.assertIn("Composition & Depth", prompt)
        self.assertIn("Visual Story Purpose", prompt)
        self.assertIn("Absolutely NO white borders", prompt)

    def test_content_hash_consistency(self):
        """Verify deterministic hashing for content-based caching."""
        h1 = compute_image_content_hash("Prompt A", aspect_ratio="9:16")
        h2 = compute_image_content_hash("Prompt A", aspect_ratio="9:16")
        h3 = compute_image_content_hash("Prompt B", aspect_ratio="9:16")
        self.assertEqual(h1, h2)
        self.assertNotEqual(h1, h3)

    def test_word_by_word_highlighting_subtitles(self):
        """Verify word-level ASS subtitle formatting with dynamic sizing and word illumination."""
        chunk = [
            {"word": "The", "start": 0.0, "end": 0.3},
            {"word": "lock", "start": 0.3, "end": 0.7},
            {"word": "snapped", "start": 0.7, "end": 1.2},
        ]
        dialogues = _chunk_to_word_level_ass_dialogues(chunk, time_offset=1.5)
        self.assertEqual(len(dialogues), 3)

        # Word 1 active
        self.assertIn("{\\c&H0000FFFF&\\b1}The{\\c&H00FFFFFF&\\b0}", dialogues[0])
        # Word 2 active
        self.assertIn("{\\c&H0000FFFF&\\b1}lock{\\c&H00FFFFFF&\\b0}", dialogues[1])
        # Word 3 active (dramatic keyword)
        self.assertIn("{\\c&H0000FFFF&\\b1}snapped{\\c&H00FFFFFF&\\b0}", dialogues[2])


if __name__ == "__main__":
    unittest.main()
