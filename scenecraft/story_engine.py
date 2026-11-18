from __future__ import annotations

"""Story Engine for Scenecraft: Standalone planning, Script adaptation, and Episodic series with persistent bibles."""

import json
import os
import re
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

from scenecraft.story_enhancer import (
    StoryQualityChecker,
    QualityAuditResult,
    StoryCritic,
    ViralHookEngine,
    CriticReviewResult,
)


def slugify(text: str) -> str:
    """Convert string to safe filename slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    return re.sub(r"[\s_-]+", "_", text)


@dataclass
class SceneBeat:
    scene_index: int
    title: str
    narration: str
    visual_description: str
    camera_movement: str = "zoom_in"
    sfx_cue: Optional[str] = None
    visual_focus: str = ""
    foreshadowing_clue: Optional[str] = None
    duration: Optional[float] = None
    emotion: Optional[str] = None
    tension_level: Optional[int] = None


@dataclass
class StoryPlan:
    title: str
    premise: str
    genre: str
    intended_audience: str
    opening_hook: str  # 1-3 second hook
    characters: List[Dict[str, str]]  # name, role, visual_anchor, motivation
    scenes: List[SceneBeat]
    ending: str
    engagement_question: str
    clues_and_reveals: List[str] = field(default_factory=list)
    adaptation_mode: Optional[str] = None  # None, "faithful", "creative"
    series_info: Optional[Dict[str, Any]] = None  # series_name, episode_num, total_episodes, arc_turn
    aspect_ratio: str = "9:16"
    voice_settings: Optional[Dict[str, Any]] = None
    quality_audit: Optional[Dict[str, Any]] = None
    twist_pair: Optional[Dict[str, Any]] = None
    hook_options: List[Dict[str, Any]] = field(default_factory=list)
    recommended_hook_id: int = 1
    on_screen_hook_text: str = ""
    critic_review: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        return data

    def to_json(self, path: Optional[Path] = None, indent: int = 2) -> str:
        s = json.dumps(self.to_dict(), indent=indent)
        if path:
            Path(path).write_text(s, encoding="utf-8")
        return s

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> StoryPlan:
        scenes_raw = data.get("scenes", [])
        scenes = [
            SceneBeat(**{k: v for k, v in s.items() if k in SceneBeat.__dataclass_fields__})
            if isinstance(s, dict) else s
            for s in scenes_raw
        ]
        valid_fields = cls.__dataclass_fields__.keys()
        clean_data = {k: v for k, v in data.items() if k in valid_fields}
        clean_data["scenes"] = scenes
        clean_data.setdefault("title", data.get("story_title", "Untitled Story"))
        clean_data.setdefault("premise", data.get("summary", data.get("description", "")))
        clean_data.setdefault("genre", data.get("genre", "survival_suspense"))
        clean_data.setdefault("intended_audience", data.get("audience", "general"))
        clean_data.setdefault(
            "opening_hook",
            data.get("opening_hook", (getattr(scenes[0], "narration", "") if scenes else ""))
        )
        clean_data.setdefault("characters", data.get("characters", []))
        clean_data.setdefault("ending", data.get("ending", ""))
        clean_data.setdefault("engagement_question", data.get("engagement_question", ""))
        return cls(**clean_data)

    def to_storyboard_dict(self) -> Dict[str, Any]:
        """Convert to existing pipeline storyboard format."""
        d = {
            "story_title": self.title,
            "genre": self.genre,
            "summary": self.premise,
            "opening_hook": self.opening_hook,
            "hook_options": self.hook_options,
            "recommended_hook_id": self.recommended_hook_id,
            "on_screen_hook_text": self.on_screen_hook_text,
            "ending": self.ending,
            "engagement_question": self.engagement_question,
            "scenes": [asdict(s) for s in self.scenes],
            "series_info": self.series_info,
            "aspect_ratio": self.aspect_ratio,
        }
        if self.voice_settings:
            d["voice_settings"] = self.voice_settings
        if self.critic_review:
            d["critic_review"] = self.critic_review
        return d

    def format_approval_outline(self) -> str:
        """Render Gate 1 high-retention human readable plan for user approval before image generation."""
        ep_header = ""
        if self.series_info:
            ep_header = f" | Episode {self.series_info.get('episode_num', 1)} of {self.series_info.get('total_episodes', 3)}"
            if self.series_info.get("arc_turn"):
                ep_header += f" [MAJOR TURNING POINT]"

        est_dur = 0.0
        word_count = 0
        if self.quality_audit:
            est_dur = self.quality_audit.get("estimated_duration_sec", 0.0)
            word_count = self.quality_audit.get("total_word_count", 0)
        elif self.scenes:
            word_count = sum(len(s.narration.split()) for s in self.scenes)
            est_dur = round(word_count / 2.25, 1)

        lines = [
            f"==================================================================",
            f"GATE 1 — STORY APPROVAL: {self.title.upper()}{ep_header}",
            f"==================================================================",
            f"Genre:              {self.genre}",
            f"Intended Audience:  {self.intended_audience}",
            f"Story Premise:      {self.premise}",
            f"Short Summary:      {self.premise[:140]}...",
            f"Estimated Duration: ~{est_dur:.1f}s ({word_count} words, preview estimate only)",
        ]

        if self.critic_review:
            cr = self.critic_review
            status_str = "PASSED" if cr.get("passed", True) else "NEEDS REVIEW"
            lines.extend([
                f"Critic Review:      {cr.get('total_score', 0)}/100 [{status_str}]",
                f"  - Vector Breakdown: Hook: {cr.get('hook_strength', 0)}/20 | Curiosity: {cr.get('curiosity_gap', 0)}/15 | Orig: {cr.get('originality', 0)}/15 | Pacing: {cr.get('pacing', 0)}/15 | Emotion: {cr.get('emotional_engagement', 0)}/10 | Escalation: {cr.get('escalation', 0)}/10 | Ending: {cr.get('ending_quality', 0)}/10 | Words: {cr.get('word_count_compliance', 0)}/5 | Continuity: {cr.get('scene_continuity', 0)}/5",
            ])
            if cr.get("weaknesses"):
                lines.append(f"  - Critic Notes: {'; '.join(cr.get('weaknesses', [])[:2])}")
        elif self.quality_audit:
            qa = self.quality_audit
            lines.append(f"Quality Score:      {qa.get('total_score', 0)}/100")

        # 3 Hook Options Presentation
        lines.extend([
            f"",
            f"------------------------------------------------------------------",
            f"HOOK SYSTEM (3 ALTERNATIVES GENERATED FOR GATE 1):",
            f"------------------------------------------------------------------",
        ])
        if self.hook_options:
            for opt in self.hook_options:
                rec_badge = " [★ RECOMMENDED]" if opt.get("is_recommended") or opt.get("id") == self.recommended_hook_id else ""
                lines.append(f"  Option {opt.get('id', 1)} [{opt.get('archetype', 'HOOK')}]{rec_badge}:")
                lines.append(f"    Spoken Narration:    \"{opt.get('spoken_hook', '')}\"")
                lines.append(f"    Opening 2s Text:     [{opt.get('on_screen_text', '')}]")
                lines.append(f"    Curiosity Gap:       {opt.get('curiosity_gap', '')}")
                lines.append("")
        else:
            lines.append(f"  Recommended Hook: \"{self.opening_hook}\"")
            if self.on_screen_hook_text:
                lines.append(f"  Opening 2s Text:  [{self.on_screen_hook_text}]")
            lines.append("")

        lines.extend([
            f"SELECTED HOOK: \"{self.opening_hook}\"",
            f"ON-SCREEN TEXT (0-2s): [{self.on_screen_hook_text or 'WATCH TILL END'}]",
            f"",
            f"PERMANENT NARRATOR IDENTITY:",
            f"  Scenecraft Permanent Cinematic Narrator (The Documentarian - VoiceStudio b77c1cca)",
            f"",
            f"CHARACTERS:",
        ])
        for c in self.characters:
            lines.append(f"  - {c.get('name', 'Protagonist')} ({c.get('role', 'Main')}): {c.get('motivation', '')}")
            lines.append(f"    Visual Anchor: {c.get('visual_anchor', '')}")

        lines.extend([
            f"",
            f"SCENE-BY-SCENE NARRATIVE ({len(self.scenes)} Scenes):",
        ])
        for s in self.scenes:
            emo_str = f" [Emotion: {s.emotion} | Tension: {s.tension_level}/10]" if s.emotion else ""
            clue_str = f" [Clue: {s.foreshadowing_clue}]" if s.foreshadowing_clue else ""
            lines.append(f"  Scene {s.scene_index}: {s.title}{emo_str}{clue_str}")
            lines.append(f"    Camera: {s.camera_movement} | SFX: {s.sfx_cue or 'None'}")
            lines.append(f"    Narration: \"{s.narration}\"")
            lines.append(f"    Visual:    {s.visual_description}")
            lines.append("")

        if self.twist_pair:
            lines.extend([
                f"FAIR-PLAY TWIST [{self.twist_pair.get('twist_type', 'TWIST')}]:",
                f"  - Clue (Scene {self.twist_pair.get('clue_scene_index', 1)}): {self.twist_pair.get('clue_text', '')}",
                f"  - Reveal (Scene {self.twist_pair.get('reveal_scene_index', len(self.scenes))}): {self.twist_pair.get('reveal_text', '')}",
                f"",
            ])

        if self.clues_and_reveals:
            lines.append("KEY CLUES & REVEALS:")
            for cl in self.clues_and_reveals:
                lines.append(f"  * {cl}")
            lines.append("")

        lines.extend([
            f"ENDING / RESOLUTION:",
            f"  {self.ending}",
            f"",
            f"AUDIENCE ENGAGEMENT QUESTION:",
            f"  \"{self.engagement_question}\"",
            f"==================================================================",
        ])
        return "\n".join(lines)


class SeriesBible:
    """Persistent Story Bible for an episodic multi-episode series."""

    def __init__(self, series_name: str, base_dir: Optional[Path] = None):
        self.series_name = series_name
        self.slug = slugify(series_name)
        self.base_dir = Path(base_dir or (Path(__file__).resolve().parent.parent / "series"))
        self.series_dir = self.base_dir / self.slug
        self.bible_path = self.series_dir / "bible.json"
        self.data: Dict[str, Any] = {}
        self.load()

    def load(self):
        """Load bible from disk or initialize fresh structure."""
        if self.bible_path.is_file():
            with open(self.bible_path, "r", encoding="utf-8") as f:
                self.data = json.load(f)
        else:
            self.data = {
                "series_name": self.series_name,
                "slug": self.slug,
                "created_at": str(Path.ctime(self.bible_path)) if self.bible_path.exists() else "",
                "logline": "",
                "genre": "Psychological Suspense",
                "core_characters": [],
                "timeline": [],
                "established_facts": [],
                "unresolved_mysteries": [],
                "episodes": [],
                "future_plot_developments": [],
            }

    def save(self):
        """Save bible to disk."""
        self.series_dir.mkdir(parents=True, exist_ok=True)
        with open(self.bible_path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2)

    def add_episode_record(self, plan: StoryPlan):
        """Record completed episode plan into persistent bible."""
        ep_num = len(self.data["episodes"]) + 1
        record = {
            "episode_number": ep_num,
            "title": plan.title,
            "summary": plan.premise,
            "hook": plan.opening_hook,
            "ending": plan.ending,
            "engagement_question": plan.engagement_question,
            "clues_revealed": plan.clues_and_reveals,
        }
        self.data["episodes"].append(record)
        # Update timeline
        self.data["timeline"].append(f"Episode {ep_num}: {plan.title}")
        self.save()


class StoryEngine:
    """Unified Story Engine supporting Standalone, Script Adaptation, and Episodic Series."""

    def __init__(self, workspace_dir: Optional[Path] = None):
        self.workspace_dir = Path(workspace_dir or Path.cwd()).resolve()
        self.series_dir = self.workspace_dir / "series"
        self.series_dir.mkdir(parents=True, exist_ok=True)
        self.quality_checker = StoryQualityChecker()
        self.hook_engine = ViralHookEngine()
        self.critic = StoryCritic()

    def _enhance_plan(self, plan: StoryPlan, preserve_plot: bool = False) -> StoryPlan:
        """Run multi-engine enhancement: hook sharpening, 3 hook options, critic pass, pacing, twist, emotion & audit."""
        # 1. Generate 3 distinct hook alternatives
        hook_options = self.hook_engine.generate_hook_options(
            premise=plan.premise,
            title=plan.title,
            genre=plan.genre,
            base_hook=plan.opening_hook,
        )
        rec_opt = next((o for o in hook_options if o.is_recommended), hook_options[0])
        plan.hook_options = [h.to_dict() for h in hook_options]
        plan.recommended_hook_id = rec_opt.id
        plan.on_screen_hook_text = rec_opt.on_screen_text
        if not plan.opening_hook or plan.opening_hook.strip() == "":
            plan.opening_hook = rec_opt.spoken_hook

        # 2. Run standard optimization pass
        opt_data, audit = self.quality_checker.optimize_story_plan(
            title=plan.title,
            premise=plan.premise,
            hook=plan.opening_hook,
            scenes=[asdict(s) for s in plan.scenes],
            ending=plan.ending,
            genre=plan.genre,
        )
        plan.opening_hook = opt_data["opening_hook"]
        if not preserve_plot:
            plan.ending = opt_data["ending"]
            plan.twist_pair = opt_data.get("twist_pair")
        plan.quality_audit = opt_data["quality_audit"]

        # 3. Separate Critic / Reviewer pass to evaluate and improve weak scripts
        crit_data, crit_review = self.critic.improve_script_if_needed(
            title=plan.title,
            premise=plan.premise,
            hook=plan.opening_hook,
            scenes=opt_data["scenes"],
            ending=plan.ending,
            genre=plan.genre,
        )
        plan.opening_hook = crit_data["opening_hook"]
        plan.ending = crit_data["ending"]
        plan.critic_review = crit_review.to_dict()

        # Ensure characters reflect The Wanderer
        wanderer_anchor = (
            "The Wanderer: 2D dark comic stickman with oversized smooth warm ivory oval head, "
            "two vertical black pill eyes, neutral slit mouth, thin black stick limbs and torso, "
            "wearing a brick-red ribbed knit beanie, striped mustard-gold and rust-maroon scarf with fringe, "
            "and dark charcoal short-sleeved t-shirt."
        )
        if not plan.characters:
            plan.characters = [{
                "name": "The Wanderer",
                "role": "Protagonist",
                "visual_anchor": wanderer_anchor,
                "motivation": "Survive the unknown and uncover the anomaly.",
            }]
        else:
            for c in plan.characters:
                if "stickman" in c.get("visual_anchor", "").lower() or c.get("name") in ["The Wanderer", "Main Character", "Protagonist"]:
                    c["visual_anchor"] = wanderer_anchor
                    c["name"] = "The Wanderer"

        plan.scenes = [
            SceneBeat(
                scene_index=s["scene_index"],
                title=s["title"],
                narration=s["narration"],
                visual_description=s["visual_description"],
                camera_movement=s.get("camera_movement", "zoom_in"),
                sfx_cue=s.get("sfx_cue"),
                visual_focus=s.get("visual_focus", ""),
                foreshadowing_clue=s.get("foreshadowing_clue"),
                duration=s.get("duration"),
                emotion=s.get("emotion"),
                tension_level=s.get("tension_level"),
            )
            for s in crit_data["scenes"]
        ]
        return plan

    def audit_story_plan(self, plan: StoryPlan) -> QualityAuditResult:
        """Audit an existing StoryPlan across all 6 quality vectors."""
        return self.quality_checker.audit_story(
            title=plan.title,
            premise=plan.premise,
            hook=plan.opening_hook,
            scenes=[asdict(s) for s in plan.scenes],
            ending=plan.ending,
        )

    # -------------------------------------------------------------
    # FEATURE 1A: Original Story Mode (Standalone & Series)
    # -------------------------------------------------------------
    def plan_standalone_story(
        self,
        concept: Optional[str] = None,
        genre: Optional[str] = None,
        fallback_mode: str = "local",
    ) -> StoryPlan:
        """Create a retention-focused standalone story plan."""
        title = concept or "The 30th Floor Lockdown"
        selected_genre = genre or "Psychological Suspense"

        # Only invoke LLM if explicitly requested via fallback_mode == 'gemini'
        if fallback_mode == "gemini":
            key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
            if key:
                plan = self._llm_plan_story(title, selected_genre, is_series=False)
                if plan:
                    return self._enhance_plan(plan)

        # High-retention procedural plan (default, zero API quota)
        plan = self._procedural_standalone_plan(title, selected_genre)
        return self._enhance_plan(plan)

    # -------------------------------------------------------------
    # FEATURE 1B: Script Adaptation Mode
    # -------------------------------------------------------------
    def adapt_script(
        self,
        script_input: str,
        mode: str = "faithful",  # "faithful" or "creative"
        title: Optional[str] = None,
        genre: Optional[str] = None,
        fallback_mode: str = "local",
    ) -> StoryPlan:
        """Adapt pasted text or script file into a cinematic StoryPlan.
        
        mode='faithful': Preserves original plot, characters, key dialogue, and ending.
        mode='creative': Tightens pacing, sharpens hook, adds subtle twist and engagement question.
        """
        # Check if input is a filepath
        content = None
        if "\n" not in script_input:
            try:
                p = Path(script_input)
                if p.is_file():
                    content = p.read_text(encoding="utf-8")
                    auto_title = title or p.stem.replace("_", " ").title()
            except (OSError, ValueError):
                pass

        if content is None:
            content = script_input.strip()
            first_line = content.splitlines()[0] if content else "Untitled Script"
            auto_title = title or first_line[:40].strip()

        selected_genre = genre or "Suspense / Mystery"
        preserve = (mode == "faithful")

        # Only invoke LLM if explicitly requested via fallback_mode == 'gemini'
        if fallback_mode == "gemini":
            key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
            if key:
                plan = self._llm_adapt_script(content, mode, auto_title, selected_genre)
                if plan:
                    return self._enhance_plan(plan, preserve_plot=preserve)

        # Procedural adaptation (default, zero API quota)
        plan = self._procedural_adapt_script(content, mode, auto_title, selected_genre)
        return self._enhance_plan(plan, preserve_plot=preserve)

    # -------------------------------------------------------------
    # FEATURE 3: Episodic Series & Story Bible
    # -------------------------------------------------------------
    def create_series(
        self,
        series_name: str,
        premise: str,
        genre: str = "Psychological Suspense",
        characters: Optional[List[Dict[str, str]]] = None,
    ) -> SeriesBible:
        """Initialize a new episodic series with persistent story bible."""
        bible = SeriesBible(series_name, base_dir=self.series_dir)
        bible.data["logline"] = premise
        bible.data["genre"] = genre
        if characters:
            bible.data["core_characters"] = characters
        else:
            bible.data["core_characters"] = [
                {
                    "name": "The Tenant",
                    "role": "Protagonist",
                    "visual_anchor": "Stickman with round white head, dot eyes, mustard-yellow beanie, and grey scarf.",
                    "motivation": "Survive the building quarantine and uncover what happened to the upper floors.",
                }
            ]
        bible.data["established_facts"] = [
            "The building has 30 residential floors and an inaccessible basement level.",
            "All exterior exits were locked from the outside at 9:40 PM.",
            "Tenants were instructed over emergency broadcasts not to open their doors to anyone.",
        ]
        bible.data["unresolved_mysteries"] = [
            "Who initiated the emergency broadcast?",
            "Why do the hallway knocking sounds move faster than human footsteps?",
            "What is hiding behind the mirrored panels in the stairwell?",
        ]
        bible.data["future_plot_developments"] = [
            "Episode 1 establishes the immediate threat and strange auditory anomalies.",
            "Episode 2 reveals contradictory evidence about the other tenants.",
            "Episode 3 delivers the major turning point where the nature of the quarantine is inverted.",
        ]
        bible.save()
        return bible

    def plan_series_arc(
        self,
        series_name: str,
        num_episodes: int = 3,
    ) -> List[StoryPlan]:
        """Plan a cohesive multi-episode arc with a fairly foreshadowed turning point around Episode 3."""
        bible = SeriesBible(series_name, base_dir=self.series_dir)
        if not bible.data.get("logline"):
            # Initialize with default if not existing
            bible = self.create_series(
                series_name=series_name,
                premise="A high-rise resident is locked inside Floor 30 as an automated anomaly sweeps through the tower.",
                genre=bible.data.get("genre", "Psychological Suspense"),
            )

        plans = []
        for ep_idx in range(1, num_episodes + 1):
            is_turning_point = (ep_idx == 3)
            plan = self._procedural_series_episode(bible, ep_idx, num_episodes, is_turning_point)
            plan = self._enhance_plan(plan)
            plans.append(plan)
            bible.add_episode_record(plan)

        return plans

    # -------------------------------------------------------------
    # Internal Planning Implementations
    # -------------------------------------------------------------
    def _procedural_standalone_plan(self, title: str, genre: str) -> StoryPlan:
        """High-retention standalone procedural plan."""
        scenes = [
            SceneBeat(
                scene_index=1,
                title="The Boundary",
                narration="You live on the 30th floor. Until tonight, that was the worst thing about your flat.",
                visual_description="Stickman with solid white head, black dot eyes, mustard-yellow beanie, and grey scarf looking out dark apartment window over city.",
                camera_movement="zoom_in",
                sfx_cue="sfx_whoosh_cinematic",
                visual_focus="Apartment window and silhouette of stickman.",
            ),
            SceneBeat(
                scene_index=2,
                title="The Broadcast",
                narration="At 9:40, every phone in the building screams at once: Stay inside. Lock your doors. Do not help the injured.",
                visual_description="Stickman sitting tensely on green couch as smartphone blinks violently with a glowing red emergency alert triangle.",
                camera_movement="zoom_in",
                sfx_cue="sfx_emergency_alert",
                visual_focus="Glowing red phone alert.",
            ),
            SceneBeat(
                scene_index=3,
                title="The Deadbolts",
                narration="Outside, heavy knuckles rattle against the corridor deadbolts. A muffled voice pleads for shelter.",
                visual_description="Stickman standing frozen in apartment hallway, hand hesitating over the heavy deadbolt lock.",
                camera_movement="pan_left",
                sfx_cue="sfx_knock_heavy",
                visual_focus="Deadbolts vibrating from outside impact.",
            ),
            SceneBeat(
                scene_index=4,
                title="First Problem: Water",
                narration="Rule one of high-rise survival: fill every container before the municipal pumps cut power.",
                visual_description="Stickman kneeling beside white bathroom tub, turning chrome faucet as fresh water pours under dim mirror light.",
                camera_movement="zoom_in",
                sfx_cue="sfx_water_faucet",
                visual_focus="Water level rising rapidly.",
            ),
            SceneBeat(
                scene_index=5,
                title="The Closet Reveal",
                narration="You creep back to the front door and peer through the peephole into the dark, empty corridor. The knocking wasn't coming from outside. It was coming from your bedroom closet.",
                visual_description="Close up of stickman's wide dot eyes peering through peephole, then turning back toward an ajar dark closet door.",
                camera_movement="zoom_in",
                sfx_cue="sfx_knock_door",
                visual_focus="Ajar closet door in background.",
                foreshadowing_clue="The peephole reveals zero footprints in the hallway dust.",
            ),
        ]

        return StoryPlan(
            title=title,
            premise=f"A 30th-floor resident prepares for an urban lockdown only to realize the threat is already inside.",
            genre=genre,
            intended_audience="Fans of fast-paced psychological suspense, analog horror, and survival mystery YouTube Shorts.",
            opening_hook="You live on the 30th floor. Until tonight, that was the worst thing about your flat.",
            characters=[
                {
                    "name": "The Resident",
                    "role": "Protagonist",
                    "visual_anchor": "Stickman with round white head, dot eyes, mustard-yellow beanie, grey scarf.",
                    "motivation": "Maintain security and survive until emergency services respond.",
                }
            ],
            scenes=scenes,
            clues_and_reveals=[
                "Emergency broadcast specifically orders residents not to open doors under any circumstances.",
                "Hallway dust is undisturbed despite the heavy knocking sound.",
                "Knocking origin was misidentified as the corridor door due to acoustic wall echo.",
            ],
            ending="The resident turns to face the open closet door as a shadow moves within.",
            engagement_question="If you were on the 30th floor, would you inspect the closet or flee down the fire escape?",
        )

    def _procedural_adapt_script(
        self,
        content: str,
        mode: str,
        title: str,
        genre: str,
    ) -> StoryPlan:
        """Convert arbitrary text/script into 5-scene vertical storyboard beats."""
        lines = [l.strip() for l in content.splitlines() if l.strip()]
        if not lines:
            lines = ["You hear a sound in the dark.", "The lights go out.", "Footsteps approach your door."]

        # Segment script into 5 chronological narrative segments
        num_scenes = 5
        k, m = divmod(len(lines), num_scenes)
        chunks = []
        idx = 0
        for i in range(num_scenes):
            part_len = k + (1 if i < m else 0)
            chunk = lines[idx:idx + part_len]
            if chunk:
                chunks.append(" ".join(chunk))
            idx += part_len

        while len(chunks) < 5:
            chunks.append(chunks[-1] if chunks else "Silence fills the corridor.")

        sfx_mapping = [
            "sfx_whoosh_cinematic",
            "sfx_emergency_alert",
            "sfx_door_lock",
            "sfx_water_faucet",
            "sfx_knock_heavy",
        ]

        scenes = []
        for i, text in enumerate(chunks, start=1):
            if mode == "faithful":
                narration = text
            else:
                # Creative: ensure second-person punchy hook
                if i == 1 and not text.lower().startswith("you"):
                    narration = f"You listen closely: {text}"
                else:
                    narration = text

            scenes.append(
                SceneBeat(
                    scene_index=i,
                    title=f"Beat {i}",
                    narration=narration,
                    visual_description=(
                        f"Stickman in mustard-yellow beanie and grey scarf in atmospheric setting matching beat: {narration[:60]}... "
                        f"Moody dramatic lighting, vertical 9:16 framing."
                    ),
                    camera_movement="zoom_in" if i % 2 == 1 else "pan_left",
                    sfx_cue=sfx_mapping[i - 1],
                    visual_focus=f"Key visual moment from beat {i}.",
                )
            )

        hook = scenes[0].narration
        return StoryPlan(
            title=title,
            premise=f"Adapted script ({mode} mode): {lines[0][:100]}...",
            genre=genre,
            intended_audience="Short-form narrative video viewers.",
            opening_hook=hook,
            characters=[
                {
                    "name": "Main Character",
                    "role": "Protagonist",
                    "visual_anchor": "Stickman in mustard-yellow knit beanie and grey scarf.",
                    "motivation": "Preserved from source script text.",
                }
            ],
            scenes=scenes,
            clues_and_reveals=[f"Faithful beat preserved from source text: '{lines[-1][:60]}'"],
            ending=scenes[-1].narration,
            engagement_question="What would you have done differently in this situation?",
            adaptation_mode=mode,
        )

    def _procedural_series_episode(
        self,
        bible: SeriesBible,
        ep_num: int,
        total_episodes: int,
        is_turning_point: bool,
    ) -> StoryPlan:
        """Generate cohesive episode adhering to the persistent series bible with fair twist at Ep 3."""
        series_name = bible.series_name

        if ep_num == 1:
            title = f"{series_name} — Ep. 1: The Lockdown"
            hook = "Whatever you do, do not check the hallway peephole at 3:17 AM."
            premise = "The first night of the building quarantine. An automated warning sounds as knocking begins on Floor 30."
            scenes = [
                SceneBeat(1, "The Midnight Warning", hook, "Stickman standing alone in dark apartment looking out rainy panoramic window.", "zoom_in", "sfx_whoosh_cinematic", foreshadowing_clue="The corridor lock clicks before the key touches it."),
                SceneBeat(2, "The Red Alert", "Your phone flashes red across the table: Emergency protocol active. Do not open for human voices.", "Stickman on couch looking down at smartphone blinking crimson.", "zoom_in", "sfx_emergency_alert"),
                SceneBeat(3, "Hallway Knocks", "Three distinct, deliberate knuckles slam against your front door. A voice whispers your name.", "Stickman freezing in hallway, staring at deadbolted entrance.", "pan_left", "sfx_knock_heavy", foreshadowing_clue="Hallway mirror reflects half a second late."),
                SceneBeat(4, "Water Reserve", "You back away toward the bathroom, opening the tap to store water before the pumps fail.", "Stickman kneeling by white tub filling water under dim vanity light.", "zoom_in", "sfx_water_faucet"),
                SceneBeat(5, "Empty Hallway", "You peer through the peephole. The hallway is completely empty. The knocking is coming from inside your closet.", "Stickman close-up at peephole, glancing back at dark ajar closet door.", "zoom_in", "sfx_knock_door"),
            ]
            ending = "The closet door creaks open three inches in the pitch dark."
            question = "Would you open the closet door or run for the emergency stairs?"

        elif ep_num == 2:
            title = f"{series_name} — Ep. 2: The Fire Escape"
            hook = "You didn't open the closet door. But at 3:45 AM, the closet opened itself."
            premise = "Fleeing the apartment, the resident discovers wet footprints leading toward the stairwell and an impossible duplicate."
            scenes = [
                SceneBeat(1, "The Open Door", hook, "Stickman backing away from the wide-open closet as shadows stretch across the floor.", "zoom_in", "sfx_door_creak", foreshadowing_clue="Wet footprints lead OUT of the closet toward the hallway."),
                SceneBeat(2, "The Tenant Directory", "In the stairwell, you find the building directory. Apartment 30B isn't registered to your name.", "Stickman holding flashlight illuminating brass wall directory with unfamiliar name.", "zoom_in", "sfx_whoosh_fast"),
                SceneBeat(3, "Radio Broadcast", "The emergency radio hums to life: Warning to all tenants. The duplicate does not know it is a duplicate.", "Stickman holding portable radio with red indicator light flickering.", "zoom_in", "sfx_emergency_alert", foreshadowing_clue="The broadcast repeats the exact words you whispered in Episode 1."),
                SceneBeat(4, "Footsteps Below", "Heavy boots clatter on the metal fire escape below your feet. Someone is fleeing downward in blind panic.", "Stickman looking over spiral metal stairwell railing into deep darkness.", "pan_left", "sfx_footsteps_creepy"),
                SceneBeat(5, "The Sighting", "You shine the light down. A figure in your exact yellow beanie and grey scarf looks up, screaming: Don't let it follow me!", "Stickman staring down into the beam of flashlight at an identical twin looking back with terrified eyes.", "zoom_in", "sfx_sub_rumble"),
            ]
            ending = "Two identical survivors stare at each other across the iron railings."
            question = "Who is the original: the one on floor 30, or the one running on floor 29?"

        else:  # Episode 3: The Fair Turning Point
            title = f"{series_name} — Ep. 3: The Quarantine Canvas"
            hook = "At 4:00 AM, the emergency sirens finally shut off. And you realize why the lock clicked first."
            premise = "The major turning point: the resident uncovers the true nature of the duplicate, reversing every event from Episode 1 and 2."
            scenes = [
                SceneBeat(1, "The Siren Silence", hook, "Stickman standing on the fire escape landing as all city lights snap back to full brilliance.", "zoom_in", "sfx_whoosh_cinematic", foreshadowing_clue="Reflecting on Episode 1 lock click and Episode 2 footprints."),
                SceneBeat(2, "The Realization", "The figure running down the stairs wasn't your copy. He was the real human who lived in 30B.", "Stickman stepping onto the 29th floor landing, looking at dropped keys with human initials.", "zoom_in", "sfx_sub_rumble"),
                SceneBeat(3, "The Closet Origin", "The knocking in Episode 1 wasn't someone trying to get in. It was you breaking out of the closet.", "Flashback framing of the dark closet interior looking outward into the living room.", "pan_left", "sfx_door_lock"),
                SceneBeat(4, "The Reflection", "You step into the hallway mirror. For the first time, you look down at your hands. No skin. Just clean black ink lines on a white canvas.", "Stickman holding up stick hands in front of mirror, ink lines glowing softly under neon lamp.", "zoom_in", "sfx_tension_riser"),
                SceneBeat(5, "The New Command", "Your phone chimes one final time: Entity successfully extracted from Apartment 30B. Proceed to street level.", "Stickman with yellow beanie turning toward the open elevator doors glowing bright white.", "zoom_in", "sfx_door_slam"),
            ]
            ending = "The elevator doors close as the stickman descends toward the real world."
            question = "Did you catch the reversed lock click in Episode 1, or did the twist surprise you?"

        return StoryPlan(
            title=title,
            premise=premise,
            genre=bible.data.get("genre", "Psychological Suspense"),
            intended_audience="Series viewers invested in mystery and psychological twists.",
            opening_hook=hook,
            characters=bible.data.get("core_characters", []),
            scenes=scenes,
            clues_and_reveals=[s.foreshadowing_clue for s in scenes if s.foreshadowing_clue],
            ending=ending,
            engagement_question=question,
            series_info={
                "series_name": series_name,
                "episode_num": ep_num,
                "total_episodes": total_episodes,
                "arc_turn": is_turning_point,
            },
        )

    # -------------------------------------------------------------
    # Optional LLM integration (if API key present)
    # -------------------------------------------------------------
    def _llm_plan_story(self, title: str, genre: str, is_series: bool) -> Optional[StoryPlan]:
        try:
            from google import genai
            from google.genai import types

            client = genai.Client()
            prompt = (
                f"Create a high-retention vertical YouTube Shorts story plan.\n"
                f"Title: {title}\nGenre: {genre}\n"
                f"Format: Second-person ('You...'), 1-3s hook, exactly 5 scenes (~60s narration), "
                f"stickman visual anchors (round white head, dot eyes, yellow beanie, grey scarf), "
                f"foreshadowing clues, twist ending, audience engagement question.\n"
                f"Provide valid JSON matching the StoryPlan structure."
            )
            resp = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0.75),
            )
            data = json.loads(resp.text)
            return StoryPlan.from_dict(data)
        except Exception:
            return None

    def _llm_adapt_script(self, content: str, mode: str, title: str, genre: str) -> Optional[StoryPlan]:
        try:
            from google import genai
            from google.genai import types

            client = genai.Client()
            instruction = (
                "You are an expert director adapting a user script for a 9:16 vertical short. "
                f"Mode is {mode.upper()}: "
                + ("Preserve original characters, plot, and dialogue strictly." if mode == "faithful" else "Tighten hook, escalate tension, add suspense twist.")
            )
            prompt = f"Title: {title}\nGenre: {genre}\nScript:\n{content}"
            resp = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=instruction,
                    response_mime_type="application/json",
                    temperature=0.6,
                ),
            )
            data = json.loads(resp.text)
            data["adaptation_mode"] = mode
            return StoryPlan.from_dict(data)
        except Exception:
            return None
