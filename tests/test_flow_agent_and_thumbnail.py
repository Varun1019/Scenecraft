"""Comprehensive test suite for Flow Agent Video Generation and Flow AI Thumbnail Generator.

Zero credit expenditure: all generation tests execute with dry_run=True.
"""

import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from storyforge.flow_client import FlowClient
from storyforge.flow_agent import FlowAgentDirector
from storyforge.thumbnail_generator import ThumbnailGenerator
from storyforge.metadata_generator import MetadataGenerator


class TestFlowAgentAndThumbnail(unittest.TestCase):

    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp(prefix="storyforge_test_"))
        self.workspace_dir = Path(__file__).resolve().parent.parent

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    # -------------------------------------------------------------------------
    # 1. Flow Native Agent Capability & Honest Fallback Audit
    # -------------------------------------------------------------------------
    def test_flow_agent_probe_honesty(self):
        """Verify Flow Agent capability probe identifies DOM state and reports fallback honestly."""
        client = FlowClient()
        probe = client.probe_agent_capabilities()

        self.assertIn("native_agent_supported", probe)
        self.assertIn("mode_name", probe)
        self.assertIn("reason", probe)
        self.assertIn("closest_alternative", probe)

        # In current live Flow web interface, native Agent is NOT present
        # Verify honest reporting: native_agent_supported must be False or strictly reflect DOM
        if not probe["native_agent_supported"]:
            self.assertEqual(probe["native_agent_supported"], False)
            self.assertIn("sequential", probe["closest_alternative"].lower())
            self.assertTrue(
                "agentfound: false" in probe["reason"].lower() or "unsupported" in probe["reason"].lower()
            )

    # -------------------------------------------------------------------------
    # 2. Wanderer Character Identity & Reference Resolution
    # -------------------------------------------------------------------------
    def test_establish_character_wanderer(self):
        """Verify Wanderer universe establishes red-beanie reference identity."""
        director = FlowAgentDirector(workspace_dir=self.workspace_dir)
        char_info = director.establish_character(character_name="The Wanderer")

        self.assertEqual(char_info["name"], "The Wanderer")
        self.assertIn("beanie", char_info["description"].lower())
        self.assertIn("scarf", char_info["description"].lower())
        self.assertIsNotNone(char_info["reference_image"])
        self.assertTrue(char_info["reference_image"].is_file())
        self.assertEqual(char_info["reference_image"].name, "ref_character_full_body.jpg")

    # -------------------------------------------------------------------------
    # 3. Scene Plan Formatting & Credit Approval Gate
    # -------------------------------------------------------------------------
    def test_scene_plan_and_credit_approval(self):
        """Verify scene plan estimates credits accurately and respects user approval gates."""
        director = FlowAgentDirector(workspace_dir=self.workspace_dir)
        scenes = [
            {"scene_index": 1, "visual_description": "Ethan standing on rooftop", "duration": 15.0},
            {"scene_index": 2, "visual_description": "Ethan walking down empty stairwell", "duration": 15.0},
        ]
        char_info = director.establish_character("The Wanderer")

        plan_text = director.format_scene_plan(
            scenes=scenes,
            character_info=char_info,
            story_title="Test Outbreak",
            aspect_ratio="16:9",
            model="omni-flash",
        )

        self.assertIn("Flow Credits Needed: 2 video generations", plan_text)
        self.assertIn("Test Outbreak", plan_text)
        self.assertIn("16:9", plan_text)

        # Test approval gate: auto_approve=True returns True
        self.assertTrue(director.request_user_approval(plan_text, auto_approve=True))

        # Test non-interactive shell without auto-approve returns False (protects user credits)
        with patch("sys.stdin.isatty", return_value=False):
            self.assertFalse(director.request_user_approval(plan_text, auto_approve=False))

    # -------------------------------------------------------------------------
    # 4. Sequential Scene Video Generation (Dry-Run / Zero Credit)
    # -------------------------------------------------------------------------
    def test_sequential_scene_video_generation_dry_run(self):
        """Verify sequential scene video generation outputs valid clips and scene manifest."""
        director = FlowAgentDirector(workspace_dir=self.workspace_dir)
        scenes = [
            {"scene_index": 1, "title": "Empty Horizon", "visual_description": "The Wanderer looks at empty city", "duration": 4.0},
            {"scene_index": 2, "title": "Dark Subway", "visual_description": "The Wanderer finds an abandoned subway", "duration": 4.0},
        ]

        out_bundle = self.test_dir / "test_video_bundle"
        out_bundle.mkdir()

        updated_scenes = director.generate_scenes(
            scenes=scenes,
            output_dir=out_bundle,
            story_title="Silent Metropolis",
            character_name="The Wanderer",
            aspect_ratio="16:9",
            model="omni-flash",
            auto_approve=True,
            dry_run=True,
        )

        self.assertEqual(len(updated_scenes), 2)
        for s in updated_scenes:
            self.assertIn("video_path", s)
            self.assertTrue(Path(s["video_path"]).is_file())
            self.assertTrue(s["video_path"].endswith(".mp4"))

        # Verify manifest file
        manifest_file = out_bundle / "videos" / "scene_manifest.json"
        self.assertTrue(manifest_file.is_file())
        with open(manifest_file, "r", encoding="utf-8") as f:
            manifest = json.load(f)
        self.assertEqual(manifest["total_scenes"], 2)
        self.assertEqual(manifest["completed_scenes"], 2)
        self.assertIn("probe_audit", manifest)

    # -------------------------------------------------------------------------
    # 5. Flow AI Dedicated Thumbnail Generator (16:9 and 9:16)
    # -------------------------------------------------------------------------
    def test_flow_ai_thumbnail_analysis_and_prompting(self):
        """Verify thumbnail generator analyzes drama peak and formats rule-of-thirds / vertical prompts."""
        thumb_gen = ThumbnailGenerator(workspace_dir=self.workspace_dir)
        story_data = {
            "story_title": "The Boy Who Sold His Shadow",
            "genre": "Dark Suspense",
            "characters": [{"name": "The Wanderer"}],
            "scenes": [
                {"scene_index": 1, "visual_description": "Boy laughing in sunlight", "tension_level": 2.0},
                {"scene_index": 2, "visual_description": "Old man taking black box", "tension_level": 6.0},
                {"scene_index": 3, "visual_description": "Desperate confrontation at midnight climax", "tension_level": 9.5},
            ]
        }

        analysis = thumb_gen.analyze_story_for_thumbnail(story_data)
        self.assertEqual(analysis["title"], "The Boy Who Sold His Shadow")
        self.assertIn("confrontation", analysis["peak_moment"].lower())
        self.assertEqual(analysis["peak_scene_index"], 3)

        # 16:9 Landscape Prompt
        prompt_16_9 = thumb_gen.build_thumbnail_prompt(analysis, aspect_ratio="16:9", style_preset="earthy_explainer")
        self.assertIn("16:9 cinematic YouTube master thumbnail", prompt_16_9)
        self.assertIn("right third of the frame", prompt_16_9)
        self.assertIn("No text", prompt_16_9)

        # 9:16 Vertical Prompt
        prompt_9_16 = thumb_gen.build_thumbnail_prompt(analysis, aspect_ratio="9:16", style_preset="earthy_explainer")
        self.assertIn("Vertical 9:16 YouTube Shorts cover thumbnail", prompt_9_16)
        self.assertIn("middle safe area", prompt_9_16)
        self.assertIn("No text", prompt_9_16)

    def test_flow_ai_thumbnail_generation_dry_run(self):
        """Verify dedicated thumbnail generation generates independent files without video extraction."""
        thumb_gen = ThumbnailGenerator(workspace_dir=self.workspace_dir)
        story_data = {
            "story_title": "The Last Human On Earth",
            "genre": "Sci-Fi Suspense",
            "characters": [{"name": "Ethan"}],
            "scenes": [
                {"scene_index": 1, "visual_description": "Ethan discovers empty streets", "tension_level": 8.0}
            ]
        }

        out_bundle = self.test_dir / "test_thumb_bundle"
        out_bundle.mkdir()

        res = thumb_gen.generate_flow_ai_thumbnail(
            story_data=story_data,
            output_dir=out_bundle,
            aspect_ratio="16:9",
            style_preset="earthy_explainer",
            dry_run=True,
        )

        self.assertIn("png", res)
        self.assertIn("jpg", res)
        self.assertTrue(res["png"].is_file())
        self.assertTrue(res["jpg"].is_file())
        self.assertEqual(res["png"].name, "thumbnail.png")
        self.assertEqual(res["jpg"].name, "thumbnail_recommended.jpg")

        # Verify prompt log exists
        prompt_log = out_bundle / "thumbnail_prompt.txt"
        self.assertTrue(prompt_log.is_file())

    def test_flow_ai_thumbnail_regeneration(self):
        """Verify user can regenerate thumbnail with a custom revised prompt."""
        thumb_gen = ThumbnailGenerator(workspace_dir=self.workspace_dir)
        out_bundle = self.test_dir / "test_regen_bundle"
        out_bundle.mkdir()

        revised_prompt = "Extreme macro close-up of glowing mechanical keyhole reflecting burning city skyline"
        res = thumb_gen.regenerate_thumbnail(
            output_dir=out_bundle,
            revised_prompt=revised_prompt,
            aspect_ratio="16:9",
            dry_run=True,
        )

        self.assertTrue(res["png"].is_file())
        prompt_log = out_bundle / "thumbnail_prompt.txt"
        self.assertTrue(prompt_log.is_file())
        log_content = prompt_log.read_text(encoding="utf-8")
        self.assertIn(revised_prompt, log_content)

    # -------------------------------------------------------------------------
    # 6. Metadata Generator Integration: NEVER Extract Frames
    # -------------------------------------------------------------------------
    def test_metadata_generator_uses_ai_thumbnail_without_extraction(self):
        """Verify MetadataGenerator attaches the Flow AI thumbnail and does not extract video frames."""
        out_bundle = self.test_dir / "test_meta_bundle"
        out_bundle.mkdir()

        # Place fake Flow AI thumbnail
        ai_thumb = out_bundle / "thumbnail_recommended.jpg"
        ai_thumb.write_bytes(b"FLOW_AI_THUMBNAIL_BYTES")

        meta_gen = MetadataGenerator()
        meta = meta_gen.generate_metadata(
            story_title="Test Survival",
            story_summary="A lone survivor escapes.",
            scenes=[{"narration": "He woke up alone."}],
            output_dir=out_bundle,
            thumbnail_path=ai_thumb,
            extract_frame=False,
        )

        self.assertIsNotNone(meta.recommended_thumbnail_path)
        self.assertEqual(meta.recommended_thumbnail_path.resolve(), ai_thumb.resolve())

    # -------------------------------------------------------------------------
    # 7. Intelligent Script Breakdown into 25-45 Visual Image Beats (1-3 min Reel)
    # -------------------------------------------------------------------------
    def test_decompose_script_to_visual_beats_reel_count(self):
        """Verify script decomposes into 25-45 detailed visual beats with camera variation."""
        director = FlowAgentDirector(workspace_dir=self.workspace_dir)
        story_data = {
            "story_title": "The 30th Floor Lockdown",
            "genre": "Survival Suspense",
            "summary": "A lone tenant survives in a sealed 30th-floor apartment tower after midnight.",
            "scenes": [
                {
                    "scene_index": 1,
                    "title": "The Rooftop Perch",
                    "narration": "The broadcast tower went silent three days ago. Ethan stood on the rusted fire escape of the 30th floor looking out over the dark city. Not a single car moved on the expressway below. Only the low hum of the emergency backup generator kept his small radio alive. Suddenly a harsh static crackle burst from the speaker.",
                    "visual_description": "Protagonist standing on rusted rooftop fire escape looking over dead city.",
                    "emotion": "SUSPENSE",
                },
                {
                    "scene_index": 2,
                    "title": "The Deadbolt",
                    "narration": "He ducked inside the stairwell and threw the heavy iron bolt. The steel door rattled once from the other side. Outside in the dark hallway heavy footsteps dragged across the concrete. He held his breath as shadows pooled beneath the doorframe. The doorknob jiggled with deliberate slow violence.",
                    "visual_description": "Bolting the reinforced iron door in narrow concrete stairwell.",
                    "emotion": "DREAD",
                },
                {
                    "scene_index": 3,
                    "title": "The Flooded Concourse",
                    "narration": "He escaped downward through the maintenance shaft into the flooded subway concourse. Murky black water reflected flickering yellow emergency lights. Rusted turnstiles blocked the main terminal exit. Through the cracked tile archway something massive shifted in the gloom. He raised his flashlight and revealed the terrifying truth.",
                    "visual_description": "Navigating flooded subway concourse with flashlight beam.",
                    "emotion": "REVEAL",
                },
            ]
        }

        beats = director.decompose_script_to_visual_beats(
            script_data=story_data,
            target_beats_range=(25, 45),
            aspect_ratio="9:16",
            universe="wanderer",
        )

        # 1. Verify beat count is within 25 to 45 bounds
        self.assertGreaterEqual(len(beats), 25)
        self.assertLessEqual(len(beats), 45)

        # 2. Verify all 4 required descriptive dimensions exist on every beat
        shot_types_seen = set()
        for idx, b in enumerate(beats, start=1):
            self.assertEqual(b.beat_index, idx)
            shot_types_seen.add(b.shot_type)

            # Character dimension
            self.assertTrue(len(b.character_action) > 5)
            self.assertTrue(len(b.character_pose) > 5)
            self.assertTrue(len(b.character_expression) > 5)
            self.assertTrue(len(b.character_gaze) > 3)
            self.assertTrue(len(b.character_interaction) > 5)

            # Environment dimension
            self.assertTrue(len(b.environment_location) > 5)
            self.assertTrue(len(b.background_details) > 5)
            self.assertTrue(len(b.foreground_details) > 5)
            self.assertTrue(len(b.weather_atmosphere) > 5)
            self.assertTrue(len(b.time_of_day) > 3)

            # Cinematography dimension
            self.assertTrue(len(b.shot_type) > 3)
            self.assertTrue(len(b.camera_movement) > 3)
            self.assertTrue(len(b.subject_position) > 3)
            self.assertTrue(len(b.lighting_direction_intensity) > 5)
            self.assertTrue(len(b.shadows_depth_focus) > 5)

            # Continuity dimension
            self.assertTrue(len(b.continuity_prior_event) > 3)
            self.assertTrue(len(b.continuity_current_action) > 3)
            self.assertTrue(len(b.continuity_next_event) > 3)
            self.assertTrue(len(b.continuity_persistent_elements) > 3)

        # 3. Verify camera anti-repetition: multiple shot types utilized
        self.assertGreaterEqual(len(shot_types_seen), 4)

    # -------------------------------------------------------------------------
    # 8. Flow Agent Master Prompt Format: Strict 9-Section Validation
    # -------------------------------------------------------------------------
    def test_flow_agent_master_prompt_nine_sections(self):
        """Verify Flow Agent master prompt contains all 9 required sections in exact format."""
        director = FlowAgentDirector(workspace_dir=self.workspace_dir)
        story_data = {
            "story_title": "The Silent Signal",
            "genre": "Psychological Horror",
            "summary": "An emergency broadcaster discovers who is tapping on the antenna wire.",
            "scenes": [
                {"scene_index": 1, "title": "Static", "narration": "The radio transmitter hissed with white noise.", "visual_description": "Radio console in dark studio."},
                {"scene_index": 2, "title": "The Knock", "narration": "Three sharp taps echoed from the rooftop antenna.", "visual_description": "Looking up at antenna tower."},
                {"scene_index": 3, "title": "The Wire", "narration": "He climbed the ladder into freezing fog.", "visual_description": "Climbing iron rungs in dense mist."},
            ]
        }

        master_prompt, beats = director.generate_master_agent_prompt(
            story_data=story_data,
            universe="wanderer",
            style_preset="dark_cinematic",
            aspect_ratio="9:16",
            target_beats_range=(25, 45),
        )

        self.assertGreaterEqual(len(beats), 25)

        # Check all 9 required sections
        self.assertIn("SECTION 1: OVERALL VISUAL STYLE & INSTRUCTIONS", master_prompt)
        self.assertIn("SECTION 2: CHARACTER REFERENCE & CONSISTENCY INSTRUCTIONS", master_prompt)
        self.assertIn("SECTION 3: COMPLETE STORY CONTEXT", master_prompt)
        self.assertIn("SECTION 4: NUMBERED IMAGE-GENERATION INSTRUCTIONS", master_prompt)
        self.assertIn("SECTION 5: DETAILED INDIVIDUAL DESCRIPTIONS FOR EVERY IMAGE", master_prompt)
        self.assertIn("SECTION 6: CONTINUITY INSTRUCTIONS BETWEEN CONSECUTIVE IMAGES", master_prompt)
        self.assertIn("SECTION 7: COMPOSITION AND CAMERA INSTRUCTIONS", master_prompt)
        self.assertIn("SECTION 8: NEGATIVE CONSTRAINTS", master_prompt)
        self.assertIn("SECTION 9: FINAL SEQUENCE & IMAGE-COUNT REQUIREMENTS", master_prompt)

        # Check negative constraints content
        self.assertIn("NO white borders", master_prompt)
        self.assertIn("NO letterbox bars", master_prompt)
        self.assertIn("NO speech bubbles", master_prompt)

        # Check Wanderer character consistency in master prompt
        self.assertIn("brick-red", master_prompt.lower())
        self.assertIn("beanie", master_prompt.lower())
        self.assertIn("scarf", master_prompt.lower())
        self.assertIn("ivory", master_prompt.lower())

    # -------------------------------------------------------------------------
    # 9. Creative Universes: Wanderer Universe vs Experimental Stories
    # -------------------------------------------------------------------------
    def test_creative_universes_wanderer_vs_experimental(self):
        """Verify Wanderer universe preserves locked identity and Experimental universe supports custom characters."""
        director = FlowAgentDirector(workspace_dir=self.workspace_dir)

        # A. Wanderer Universe
        wanderer_char = director.establish_character(universe="wanderer")
        self.assertEqual(wanderer_char["name"], "The Wanderer")
        self.assertEqual(wanderer_char["universe"], "wanderer")
        self.assertIn("beanie", wanderer_char["description"].lower())
        self.assertIn("scarf", wanderer_char["description"].lower())
        self.assertIn("ivory", wanderer_char["description"].lower())
        self.assertTrue(wanderer_char["reference_image"].name.endswith("ref_character_full_body.jpg"))

        # B. Experimental Stories
        custom_spec = {
            "name": "Cipher-9",
            "description": "Android explorer with sleek matte black composite armor, glowing teal optical visor, and copper cybernetic limbs.",
        }
        exp_char = director.establish_character(
            character_name="Cipher-9",
            custom_description=custom_spec["description"],
            universe="experimental",
        )
        self.assertEqual(exp_char["name"], "Cipher-9")
        self.assertEqual(exp_char["universe"], "experimental")
        self.assertIn("matte black composite armor", exp_char["description"])
        self.assertIn("teal optical visor", exp_char["description"])

    # -------------------------------------------------------------------------
    # 10. Automatic Thumbnail Settings & Dry-Run Generation
    # -------------------------------------------------------------------------
    def test_auto_thumbnail_settings_and_generation(self):
        """Verify automatic thumbnail generation respects settings and creates independent files."""
        from storyforge.settings import is_auto_thumbnail_enabled, set_auto_thumbnail_enabled

        # Test settings toggle
        set_auto_thumbnail_enabled(True, workspace_dir=self.test_dir)
        self.assertTrue(is_auto_thumbnail_enabled(workspace_dir=self.test_dir))

        thumb_gen = ThumbnailGenerator(workspace_dir=self.workspace_dir)
        story_data = {
            "story_title": "Rooftop Outbreak",
            "genre": "Action Survival",
            "scenes": [
                {"scene_index": 1, "visual_description": "Stickman stands on rooftop surrounded by burning skyline", "tension_level": 9.5}
            ]
        }

        out_bundle = self.test_dir / "test_auto_thumb_bundle"
        out_bundle.mkdir()

        res = thumb_gen.generate_flow_ai_thumbnail(
            story_data=story_data,
            output_dir=out_bundle,
            aspect_ratio="9:16",
            style_preset="dark_cinematic",
            dry_run=True,
        )

        self.assertTrue(res["png"].is_file())
        self.assertTrue(res["jpg"].is_file())
        self.assertEqual(res["png"].name, "thumbnail.png")
        self.assertEqual(res["jpg"].name, "thumbnail_recommended.jpg")

        prompt_txt = out_bundle / "thumbnail_prompt.txt"
        self.assertTrue(prompt_txt.is_file())
        content = prompt_txt.read_text(encoding="utf-8")
        self.assertIn("9:16", content)
        self.assertIn("Rooftop Outbreak", content)

    # -------------------------------------------------------------------------
    # 11. Asset Intake & Organization from Flow Agent
    # -------------------------------------------------------------------------
    def test_asset_intake_and_organization(self):
        """Verify ingesting Flow Agent generated images normalizes filenames and creates asset manifest."""
        director = FlowAgentDirector(workspace_dir=self.workspace_dir)

        # Create mock source images
        source_dir = self.test_dir / "mock_flow_downloads"
        source_dir.mkdir()
        for i in range(1, 6):
            # Create simple blank image files
            from PIL import Image
            img = Image.new("RGB", (1080, 1920), color=(10 * i, 20 * i, 30 * i))
            img.save(source_dir / f"flow_agent_gen_{i:03d}.png")

        target_bundle = self.test_dir / "target_bundle"
        target_bundle.mkdir()

        ingested = director.ingest_agent_assets(
            source_path=source_dir,
            output_dir=target_bundle,
            aspect_ratio="9:16",
        )

        self.assertEqual(len(ingested), 5)
        for idx, p in enumerate(ingested, start=1):
            self.assertEqual(p.name, f"scene_{idx:02d}.jpg")
            self.assertTrue(p.is_file())

        manifest = target_bundle / "images" / "agent_assets_manifest.json"
        self.assertTrue(manifest.is_file())
        with open(manifest, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data["total_ingested"], 5)

    # -------------------------------------------------------------------------
    # 12. Honest Flow Agent Instructions & No False Automation
    # -------------------------------------------------------------------------
    def test_honest_flow_agent_instructions(self):
        """Verify master prompt bundle includes clear user-paste instructions and never claims false submission."""
        director = FlowAgentDirector(workspace_dir=self.workspace_dir)
        story_data = {
            "story_title": "Midnight Protocol",
            "scenes": [{"scene_index": 1, "narration": "He closed the steel door.", "visual_description": "Closed door."}]
        }
        master_prompt, beats = director.generate_master_agent_prompt(story_data, target_beats_range=(25, 45))

        out_bundle = self.test_dir / "honest_bundle"
        out_bundle.mkdir()

        saved = director.save_master_prompt_bundle(
            output_dir=out_bundle,
            story_data=story_data,
            visual_beats=beats,
            master_prompt=master_prompt,
        )

        guide_text = saved["guide_txt"].read_text(encoding="utf-8")
        self.assertIn("PASTE INTO GOOGLE FLOW AGENT", guide_text)
        self.assertIn("StoryForge prepares the prompt; submission is performed by you in Flow", guide_text)
        self.assertNotIn("StoryForge submitted the prompt to Flow Agent", guide_text)


if __name__ == "__main__":
    unittest.main()
