"""Unit tests for Social Media Video Caption Generator."""

import unittest
from scenecraft.caption_generator import CaptionGenerator, SocialCaption, copy_to_clipboard


class TestCaptionGenerator(unittest.TestCase):

    def setUp(self):
        self.gen = CaptionGenerator()

    def test_standalone_story_caption(self):
        story = {
            "title": "Your Phone Knows When You'll Die",
            "genre": "Psychological Horror",
            "summary": "A phone counts down 60 seconds offline warning not to look behind.",
            "scenes": [
                {"narration": "At 11:59, your phone buzzes with an unclosable alert: Sixty seconds left to live."},
                {"narration": "Zero signal bars, completely offline."}
            ],
            "opening_hook": "At 11:59, your phone buzzes.",
            "engagement_question": "Would you answer that call?",
        }
        caption = self.gen.generate_caption(story, platform="youtube_shorts")
        text = caption.format_text("youtube_shorts")

        # 1. Standalone header: No invented episode
        self.assertEqual(caption.header, "YOUR PHONE KNOWS WHEN YOU'LL DIE")
        self.assertNotIn("EPISODE", text)
        self.assertNotIn("PART", text)

        # 2. Suspenseful description present
        self.assertTrue(len(caption.description) > 20)
        self.assertNotIn("ending", caption.description.lower())

        # 3. No invented episode info
        self.assertIsNone(caption.episode_info)

        # 4. Engagement question
        self.assertIn("Would you answer that call?", text)

        # 5. Hashtags
        self.assertTrue(4 <= len(caption.hashtags) <= 6)
        self.assertTrue(any("horror" in tag for tag in caption.hashtags))
        self.assertIn("#shorts", text)

    def test_series_story_caption(self):
        story = {
            "title": "The Lockdown",
            "genre": "Zombie Survival",
            "summary": "Three survivors barricade inside an apartment as infected gather outside.",
            "engagement_question": "Would you wake them?",
            "series_info": {
                "series_name": "Zombie Outbreak",
                "episode_num": 5,
                "part_num": 3,
                "total_parts": 4,
                "total_episodes": 4,
            }
        }
        caption = self.gen.generate_caption(story, platform="youtube_shorts")
        text = caption.format_text("youtube_shorts")

        # 1. Episode header
        self.assertEqual(caption.header, "ZOMBIE OUTBREAK - EPISODE 5 (PART 3/4)")
        self.assertIn("ZOMBIE OUTBREAK - EPISODE 5 (PART 3/4)", text)

        # 2. Episode info
        self.assertEqual(caption.episode_info, "Part 3 - Episode 5 (3/4). Part 4 coming soon.")
        self.assertIn("Part 3 - Episode 5 (3/4). Part 4 coming soon.", text)

        # 3. Question & hashtags
        self.assertIn("Would you wake them?", text)
        self.assertTrue(any("survival" in tag or "zombie" in tag for tag in caption.hashtags))

    def test_instagram_reels_formatting(self):
        story = {
            "title": "The 30th Floor",
            "genre": "Psychological Suspense",
            "summary": "Knocks at 3:17 AM on the 30th floor.",
            "scenes": [{"narration": "Whatever you do, do not check the hallway peephole at 3:17 AM."}],
        }
        caption = self.gen.generate_caption(story, platform="instagram_reels")
        ig_text = caption.format_text("instagram_reels")

        self.assertIn("#reels", ig_text)
        self.assertNotIn("#shorts", ig_text)


if __name__ == "__main__":
    unittest.main()
