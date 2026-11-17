"""Unit tests for the upgraded Scenecraft Storytelling Intelligence Engine."""

import unittest
from pathlib import Path

from scenecraft.story_enhancer import (
    ViralHookEngine,
    StoryPacingEngine,
    CliffhangerEngine,
    PlotTwistEngine,
    EmotionalIntelligence,
    StoryQualityChecker,
)
from scenecraft.story_engine import StoryEngine, StoryPlan, SceneBeat


class TestStoryEnhancer(unittest.TestCase):
    def setUp(self):
        self.hook_engine = ViralHookEngine()
        self.pacing_engine = StoryPacingEngine()
        self.cliffhanger_engine = CliffhangerEngine()
        self.twist_engine = PlotTwistEngine()
        self.emotion_engine = EmotionalIntelligence()
        self.quality_checker = StoryQualityChecker()

    # 1. VIRAL HOOK ENGINE
    def test_viral_hook_detects_generic_openers(self):
        generic = "Once upon a time, there was a man living on the 30th floor."
        res = self.hook_engine.analyze_hook(generic)
        self.assertTrue(res["is_generic"])
        self.assertLess(res["score"], 12)

        strong = "Never unlock your deadbolt when the sirens turn red."
        res_strong = self.hook_engine.analyze_hook(strong)
        self.assertFalse(res_strong["is_generic"])
        self.assertGreaterEqual(res_strong["score"], 15)

    def test_viral_hook_sharpening(self):
        weak_hook = "It was a dark and stormy night when the radio turned on."
        sharpened = self.hook_engine.sharpen_hook(weak_hook, genre="Suspense", premise="crane operator trapped")
        self.assertFalse(sharpened.lower().startswith("it was a"))
        self.assertIn("vibrate", sharpened)

    # 2. STORY PACING ENGINE
    def test_pacing_prunes_filler(self):
        bloated_text = "Suddenly and without warning he slowly began to realize that the door was locked."
        pruned = self.pacing_engine.prune_filler(bloated_text)
        self.assertNotIn("suddenly and without warning", pruned.lower())
        self.assertNotIn("slowly began to realize that", pruned.lower())
        self.assertEqual(pruned, "the door was locked.")

    def test_pacing_analysis_budget(self):
        # 5 scenes with realistic word distribution for Shorts (target ~45-60s)
        good_scenes = [
            {"narration": "You live on the top floor of an abandoned hospital where no power has run for twenty years. Down below, the dark city streets are completely silent."},
            {"narration": "At midnight, the emergency intercom clicks awake with piercing static and a woman's calm voice. She announces that all stairwell exits are sealed."},
            {"narration": "The voice instructs every patient to remain in their beds and ignore the sounds in the corridor. You know for a fact there are no other patients."},
            {"narration": "You check the glass elevator shaft through the darkness with a dim flashlight beam. Heavy scraping sounds vibrate through the steel frame."},
            {"narration": "All three elevator cables had been severed from the inside just seconds ago. And the counterweight is slowly rising toward your floor."},
        ]
        res = self.pacing_engine.analyze_pacing(good_scenes)
        self.assertGreaterEqual(res["pacing_score"], 15)
        self.assertTrue(45.0 <= res["estimated_duration_sec"] <= 65.0)

    # 3. CLIFFHANGER ENGINE
    def test_cliffhanger_rejects_passive_resolution(self):
        passive = "Then he woke up and realized everything was fine."
        eval_passive = self.cliffhanger_engine.analyze_ending(passive)
        self.assertTrue(eval_passive["is_passive"])
        self.assertLess(eval_passive["score"], 10)

        tense = "That's when the glass ceiling began to spiderweb under heavy weight."
        eval_tense = self.cliffhanger_engine.analyze_ending(tense)
        self.assertTrue(eval_tense["has_cliffhanger"])
        self.assertGreaterEqual(eval_tense["score"], 16)

    def test_cliffhanger_crafting(self):
        ending = "He stood by the closet."
        crafted = self.cliffhanger_engine.craft_cliffhanger(ending, context="closet door open")
        self.assertIn("knocking wasn't coming from outside", crafted)

    # 4. PLOT TWIST ENGINE
    def test_plot_twist_two_point_anchor(self):
        scenes = [
            {"scene_index": 1, "narration": "Scene 1 setup."},
            {"scene_index": 2, "narration": "Scene 2 escalation."},
            {"scene_index": 3, "narration": "Scene 3 conflict."},
            {"scene_index": 4, "narration": "Scene 4 discovery."},
            {"scene_index": 5, "narration": "Scene 5 climax."},
        ]
        modified, twist_pair = self.twist_engine.plant_and_reveal_twist(scenes)
        self.assertIsNotNone(twist_pair)
        self.assertIn("foreshadowing_clue", modified[1])
        self.assertEqual(twist_pair.clue_scene_index, 2)
        self.assertEqual(twist_pair.reveal_scene_index, 5)

    # 5. EMOTIONAL INTELLIGENCE
    def test_emotion_classification_and_tension_curve(self):
        scenes = [
            {"narration": "You wait quietly listening to the strange sound."},
            {"narration": "The phone screams with an urgent alarm message."},
            {"narration": "In the cold darkness a shadow moves across the wall."},
            {"narration": "You noticed the safe lock was unlocked from the inside."},
            {"narration": "The glass suddenly began cracking under immense pressure."},
        ]
        enriched = self.emotion_engine.enrich_scenes(scenes)
        tension_levels = [s["tension_level"] for s in enriched]
        # Tension must strictly ascend toward climax
        self.assertLess(tension_levels[0], tension_levels[-1])
        self.assertGreaterEqual(tension_levels[-1], 8)
        self.assertEqual(enriched[1]["emotion"], "PANIC")
        self.assertIn("alert", enriched[1]["sfx_cue"])

    # 6. STORY QUALITY CHECKER
    def test_quality_audit_and_auto_refine(self):
        raw_scenes = [
            {"scene_index": 1, "narration": "Once upon a time you lived on floor thirty above a quiet city street."},
            {"scene_index": 2, "narration": "Suddenly you noticed that an alarm was sounding through the entire building."},
            {"scene_index": 3, "narration": "He slowly began to realize that the door was shut tight from the outside."},
            {"scene_index": 4, "narration": "You fill the water in the sink before the municipal pumps lose all electrical power."},
            {"scene_index": 5, "narration": "Then he woke up and it was all fine."},
        ]
        opt_data, audit = self.quality_checker.optimize_story_plan(
            title="The Test Story",
            premise="Testing story engine audit",
            hook=raw_scenes[0]["narration"],
            scenes=raw_scenes,
            ending=raw_scenes[-1]["narration"],
        )
        self.assertGreaterEqual(audit.total_score, 80)
        self.assertFalse(opt_data["opening_hook"].lower().startswith("once upon a time"))
        self.assertNotIn("woke up", opt_data["ending"].lower())
        self.assertIsNotNone(opt_data.get("twist_pair"))

    # 7. END-TO-END STORY ENGINE INTEGRATION
    def test_story_engine_generates_enhanced_plan(self):
        engine = StoryEngine()
        plan = engine.plan_standalone_story(concept="The Arctic Bunker", genre="Sci-Fi Thriller")
        self.assertIsInstance(plan, StoryPlan)
        self.assertIsNotNone(plan.quality_audit)
        self.assertGreaterEqual(plan.quality_audit["total_score"], 80)
        self.assertIsNotNone(plan.twist_pair)
        for s in plan.scenes:
            self.assertIsNotNone(s.emotion)
            self.assertIsNotNone(s.tension_level)

    def test_story_engine_adapts_user_script(self):
        engine = StoryEngine()
        user_script = """
        I was working the night shift at the radio tower.
        At 2 AM, the receiver started picking up an emergency signal.
        The coordinates were coming from the bottom of the lake.
        I radioed the rescue team, but their radio was already dead.
        That is when I heard wet footsteps on the staircase behind me.
        """
        # Test faithful mode
        plan_faithful = engine.adapt_script(user_script, mode="faithful", title="The Radio Tower")
        self.assertIsInstance(plan_faithful, StoryPlan)
        self.assertIsNotNone(plan_faithful.quality_audit)
        self.assertEqual(len(plan_faithful.scenes), 5)

        # Test creative mode
        plan_creative = engine.adapt_script(user_script, mode="creative", title="The Radio Tower")
        self.assertIsInstance(plan_creative, StoryPlan)
        self.assertIsNotNone(plan_creative.twist_pair)
        self.assertGreaterEqual(plan_creative.quality_audit["total_score"], 80)

    # 8. HOOK SYSTEM (3 ALTERNATIVES WITH 2S ON-SCREEN TEXT)
    def test_hook_system_generates_three_distinct_options_with_on_screen_text(self):
        opts = self.hook_engine.generate_hook_options(
            premise="A high-rise resident receives an automated warning as knocking begins on Floor 30.",
            title="The Knock at 3:17 AM",
            genre="Psychological Suspense",
            base_hook="Someone knocks on your door at night.",
        )
        self.assertEqual(len(opts), 3)
        archetypes = {o.archetype for o in opts}
        self.assertTrue(len(archetypes) >= 2)
        # Check that one is recommended
        recommended = [o for o in opts if o.is_recommended]
        self.assertEqual(len(recommended), 1)
        # Check on-screen text for opening 2s
        for o in opts:
            self.assertTrue(len(o.on_screen_text) > 0)
            self.assertTrue(o.on_screen_text.isupper())
            self.assertTrue(len(o.curiosity_gap) > 10)
            self.assertGreaterEqual(o.score, 12)

    # 9. SEPARATE STORY CRITIC / REVIEWER PASS
    def test_story_critic_nine_dimension_evaluation_and_improvement(self):
        from scenecraft.story_enhancer import StoryCritic
        critic = StoryCritic()
        raw_scenes = [
            {"scene_index": 1, "narration": "Once upon a time you were in a normal room and it was quiet."},
            {"scene_index": 2, "narration": "A siren sounded in the street outside."},
            {"scene_index": 3, "narration": "You looked out the window and saw fog."},
            {"scene_index": 4, "narration": "Then you heard something on the roof."},
            {"scene_index": 5, "narration": "It was dark and then you went to sleep."},
        ]
        # Initial review should flag weak hook and flat ending
        initial_review = critic.evaluate_story(
            title="Weak Story",
            premise="A resident hears a sound.",
            hook=raw_scenes[0]["narration"],
            scenes=raw_scenes,
            ending=raw_scenes[-1]["narration"],
        )
        self.assertFalse(initial_review.passed)
        self.assertGreater(len(initial_review.weaknesses), 0)

        # Automatic improvement pass
        improved_data, post_review = critic.improve_script_if_needed(
            title="Weak Story",
            premise="A resident hears a sound.",
            hook=raw_scenes[0]["narration"],
            scenes=raw_scenes,
            ending=raw_scenes[-1]["narration"],
        )
        self.assertTrue(post_review.passed)
        self.assertGreaterEqual(post_review.total_score, 80)
        self.assertGreater(post_review.hook_strength, initial_review.hook_strength)

    # 10. GATE 1 OUTLINE PRESENTATION
    def test_gate_1_approval_outline_contains_required_fields(self):
        engine = StoryEngine()
        plan = engine.plan_standalone_story(concept="The Midnight Protocol", genre="Survival Suspense")
        outline = plan.format_approval_outline()
        self.assertIn("GATE 1 — STORY APPROVAL", outline)
        self.assertIn("Story Premise:", outline)
        self.assertIn("HOOK SYSTEM (3 ALTERNATIVES GENERATED FOR GATE 1):", outline)
        self.assertIn("RECOMMENDED", outline)
        self.assertIn("Short Summary:", outline)
        self.assertIn("Estimated Duration:", outline)
        self.assertIn("ON-SCREEN TEXT", outline)
        self.assertIn("The Wanderer", outline)


if __name__ == "__main__":
    unittest.main()
