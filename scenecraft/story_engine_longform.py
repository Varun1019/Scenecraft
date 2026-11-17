"""Long-form Storytelling Engine for Scenecraft.

Generates cinematic multi-act stories for 10-20 minute YouTube videos
with actual AI-generated video clip breakdowns, opening hooks (15-30s),
dialogue, escalating tension, and sequel-worthy cliffhangers.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import List, Dict, Any, Optional

from scenecraft.story_enhancer import StoryQualityChecker


SUPPORTED_LONGFORM_GENRES = [
    "zombie_apocalypse",
    "survival_horror",
    "post_apocalyptic_survival",
    "psychological_thriller",
    "mystery",
    "sci_fi_horror",
]


@dataclass
class LongformSceneBeat:
    scene_index: int
    act: str  # Act I, Act II, Act III, Act IV
    title: str
    narration: str
    video_prompt: str  # Cinematic 16:9 prompt for omni-flash / veo
    target_duration: float = 6.0  # Seconds per clip
    camera_movement: str = "slow_dolly_forward"
    camera_angle: str = "eye_level"
    lighting: str = "emergency_amber_and_deep_shadows"
    sfx_cue: Optional[str] = None
    emotion: str = "suspense"
    tension_level: int = 5  # 1 to 10
    is_short_candidate: bool = False
    short_hook: Optional[str] = None


@dataclass
class LongformStoryPlan:
    project_name: str
    title: str
    premise: str
    genre: str
    target_minutes: int
    opening_hook_narration: str  # 15-30 second viral opening hook
    characters: List[Dict[str, str]]
    scenes: List[LongformSceneBeat]
    ending: str
    cliffhanger: str
    description: str
    hashtags: List[str]

    @property
    def total_estimated_duration(self) -> float:
        return sum(s.target_duration for s in self.scenes)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self, path: Optional[Path] = None, indent: int = 2) -> str:
        data_str = json.dumps(self.to_dict(), indent=indent)
        if path:
            Path(path).write_text(data_str, encoding="utf-8")
        return data_str

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> LongformStoryPlan:
        raw_scenes = data.get("scenes", [])
        scenes = [
            LongformSceneBeat(**s) if isinstance(s, dict) else s
            for s in raw_scenes
        ]
        clean_data = {k: v for k, v in data.items() if k in cls.__dataclass_fields__ and k != "scenes"}
        clean_data["scenes"] = scenes
        return cls(**clean_data)


class LongformStoryEngine:
    """Generates and manages multi-act scripts and 16:9 video prompt beats."""

    def __init__(self, workspace_dir: Optional[Path] = None):
        self.workspace_dir = Path(workspace_dir or Path.cwd()).resolve()
        self.quality_checker = StoryQualityChecker()

    def generate_plan(
        self,
        theme: str = "You are trapped inside a supermarket during a zombie apocalypse",
        genre: str = "zombie_apocalypse",
        target_minutes: int = 15,
        project_name: Optional[str] = None,
        max_scenes: Optional[int] = None,
    ) -> LongformStoryPlan:
        """Construct a multi-act, highly engaging long-form narrative."""
        clean_genre = genre.lower().replace(" ", "_")
        if clean_genre not in SUPPORTED_LONGFORM_GENRES:
            clean_genre = "survival_horror"

        safe_slug = re.sub(r"[^\w\s-]", "", theme.lower()).strip()
        safe_name = project_name or re.sub(r"[\s_-]+", "_", safe_slug)[:32].strip("_") or "supermarket_apocalypse"
        
        # Calculate scene count: for long-form master videos, target 15-40 cinematic clips
        clip_duration = 6.0
        if max_scenes is not None:
            num_scenes = max_scenes
        else:
            num_scenes = max(16, min(40, int((target_minutes * 60) / 25)))

        scenes = self._build_scenes_for_genre(clean_genre, theme, num_scenes, clip_duration)
        
        opening_hook = (
            "The emergency shutters of FoodMart slammed shut at midnight. "
            "Outside, twenty thousand infected tore through the parking lot. "
            "Inside, three survivors realized the security doors can only be unlocked from the outside... "
            "and one of them is already bitten."
        )

        characters = [
            {
                "name": "Marcus Kane",
                "role": "Nightshift Manager / Reluctant Leader",
                "visual_anchor": "Dark graphic novel style, rugged man in a faded navy supermarket vest, flashlight strapped to shoulder, exhausted determined expression.",
            },
            {
                "name": "Dr. Elena Vance",
                "role": "Biologist Survivor",
                "visual_anchor": "Dark graphic novel style, woman with wire-rimmed glasses, practical hooded parka, carrying a reinforced medical case.",
            },
            {
                "name": "The Shadowed Figure",
                "role": "Unknown Stalker / Patient Zero",
                "visual_anchor": "Tall menacing silhouette moving between aisle shelves, distorted posture, eyes reflecting flickering fluorescent tube light.",
            }
        ]

        title = f"{theme.title()} — Nightfall Containment"
        description = (
            f"A full-length cinematic AI survival thriller: {theme}.\n\n"
            f"Follow the survivors as they navigate pitch-black supermarket aisles, "
            f"failing backup generators, and the horrifying truth lurking in the cold storage warehouse.\n\n"
            f"Produced with Scenecraft Cinematic AI Video Engine."
        )

        hashtags = [
            "#ZombieApocalypse",
            "#SurvivalHorror",
            "#AIVideo",
            "#Scenecraft",
            "#HorrorFilm",
            "#CinematicAI",
            "#SciFiHorror",
        ]

        cliffhanger = (
            "Elena points the ultraviolet scanner at Marcus's sleeve. The scanner blinks crimson. "
            "Down the main aisle, the hydraulic lock of the cold storage vault disengages with a deafening hiss."
        )

        return LongformStoryPlan(
            project_name=safe_name,
            title=title,
            premise=theme,
            genre=clean_genre,
            target_minutes=target_minutes,
            opening_hook_narration=opening_hook,
            characters=characters,
            scenes=scenes,
            ending="The emergency lights die completely as hundreds of eyes glow in the meat locker.",
            cliffhanger=cliffhanger,
            description=description,
            hashtags=hashtags,
        )

    def _build_scenes_for_genre(
        self,
        genre: str,
        theme: str,
        count: int,
        clip_duration: float
    ) -> List[LongformSceneBeat]:
        """Construct multi-act scene progression with dedicated 16:9 visual prompts."""
        scenes: List[LongformSceneBeat] = []

        act_splits = {
            "Act I: Containment & The Viral Hook": int(count * 0.25),
            "Act II: Resource Scramble & Darkness": int(count * 0.50),
            "Act III: Breach & The Betrayal Twist": int(count * 0.80),
            "Act IV: Final Stand & Sequel Cliffhanger": count,
        }

        # Narrative templates based on genre
        beat_definitions = [
            # Act I
            ("Act I: Containment", "Midnight Lockdown", "The heavy metal security grille crashes onto the concrete floor. The automated sirens scream in the empty parking lot.", "Cinematic 16:9 wide shot, dark graphic novel illustration, industrial steel supermarket security shutters slamming down, amber emergency beacons, silhouettes pounding on the shatterproof glass outside", "sfx_door_slam", "terror", 8, True, "You are locked inside. And the glass is cracking."),
            ("Act I: Containment", "Flickering Aisles", "Fluorescent tubes hum overhead, flickering violently as the electrical grid wavers. Canned goods line endless, silent aisles.", "Cinematic 16:9 medium dolly shot, dark graphic novel comic style, long perspective down narrow supermarket aisle 4, flickering overhead strip lights, deep eerie shadows", "sfx_tension_riser", "suspense", 6, False, None),
            ("Act I: Containment", "The Survivor Count", "Marcus wipes sweat from his forehead, clutching an iron crowbar. Elena checks the pulse of the wounded security guard.", "Cinematic 16:9 over-the-shoulder shot, rugged man in navy supermarket vest holding crowbar looking down at injured guard on linoleum floor, gritty graphic novel artwork", "sfx_footsteps_creepy", "fear", 7, False, None),
            ("Act I: Containment", "The Scratching In The Ceiling", "Above aisle twelve, the fiberglass ceiling tiles begin to sag. Dust rains down into the breakfast cereal displays.", "Cinematic 16:9 low angle looking up at sagging acoustic ceiling tiles in supermarket, dust motes floating under pale flashlight beam, dark claw marks scraping from above", "sfx_sub_rumble", "mystery", 7, True, "Look up at the ceiling tiles. They are moving."),
            
            # Act II
            ("Act II: The Descent", "Generator Failure", "The main power breaker violently trips. Total darkness swallows the store, leaving only the amber glow of battery backup lights.", "Cinematic 16:9 wide establishing shot, sudden blackout in sprawling hypermarket, lone amber emergency exit signs casting long eerie orange shadows across abandoned shopping carts", "sfx_emergency_alert", "dread", 8, False, None),
            ("Act II: The Descent", "Rations and Bandages", "Elena gathers antiseptic and bandages in the pharmacy aisle. Her flashlight beam catches a trail of black liquid leading into the staff lounge.", "Cinematic 16:9 close up, woman with glasses directing flashlight beam at spilled viscous dark fluid across polished white pharmacy floor, comic graphic novel aesthetic", "sfx_whoosh_cinematic", "mystery", 7, False, None),
            ("Act II: The Descent", "The Whispering PA System", "Static crackles through the store speakers. A broken automated voice repeats: Code Black. Do not open warehouse sector three.", "Cinematic 16:9 medium shot, public address horn speaker mounted high on industrial ceiling support beam, red warning strobe pulsing rhythmically, dark cinematic lighting", "sfx_alarm", "paranoia", 8, False, None),
            ("Act II: The Descent", "Footsteps Behind The Display", "Marcus freezes behind an endcap of soda crates. Two aisles away, heavy uneven dragging footsteps echo through the silence.", "Cinematic 16:9 low angle tracking shot, survivor crouched behind cardboard displays holding breath, shadowy distorted silhouette pacing past the aisle entrance in the background", "sfx_footsteps_creepy", "suspense", 9, True, "Never make a sound when aisle six goes quiet."),
            
            # Act III
            ("Act III: The Breach", "The Glass Fractures", "A deafening thud shakes the front entrance. The reinforced plate glass is spiderwebbing under immense pressure from outside hordes.", "Cinematic 16:9 wide shot, massive plate glass store windows buckling inwards, spiderweb cracks spreading, dozens of infected silhouettes pressing against the glass under night rain", "sfx_whoosh_fast", "panic", 9, True, "The glass won't hold until morning."),
            ("Act III: The Breach", "The Secret In The Freezer", "They retreat to the commercial walk-in freezer. Marcus pulls the heavy lever, but the lock mechanism is jammed with zip-ties.", "Cinematic 16:9 medium close up, heavy stainless steel industrial freezer door, thick frost rimming the porthole window, human handprint from the inside", "sfx_door_lock", "terror", 9, False, None),
            ("Act III: The Breach", "The Bite Mark", "Elena notices blood soaking Marcus's left sleeve. The torn fabric reveals a deep jagged bite that has already turned necrotic grey.", "Cinematic 16:9 dramatic close-up, torn sleeve pulled back showing fresh infected bite mark, characters face stricken with horrifying realization, harsh directional flashlight lighting", "sfx_tension_riser", "betrayal", 10, True, "He promised he wasn't bitten. He lied."),
            ("Act III: The Breach", "Containment Compromise", "The ceiling tiles finally give way. A skeletal infected drops onto the customer service counter, screeching into the dark.", "Cinematic 16:9 high dynamic action shot, creature crashing down through broken ceiling panels onto checkout counter, scattered papers, graphic novel dramatic comic linework", "sfx_whoosh_cinematic", "horror", 10, False, None),

            # Act IV
            ("Act IV: The Climax", "The Flare in Aisle Nine", "Elena strikes a road flare. Blood-red smoke fills the central corridor, illuminating three dozen infected surrounding their barricade.", "Cinematic 16:9 panoramic shot, brilliant crimson magnesium flare smoke illuminating endless supermarket aisle filled with snarling silhouettes, high contrast graphic novel art", "sfx_emergency_alert", "despair", 10, False, None),
            ("Act IV: The Climax", "Marcus's Sacrifice", "Marcus cocks the manual pump-action shotgun. He turns his back to Elena and points towards the loading dock fire escape.", "Cinematic 16:9 medium heroic silhouette shot, survivor standing in front of red flare smoke holding shotgun facing incoming darkness, grim heroic resolve", "sfx_door_slam", "resolve", 9, False, None),
            ("Act IV: The Climax", "The Loading Bay Door", "The motorized bay door grinds open six inches. Outside isn't safety—it's a military quarantine blockade on fire.", "Cinematic 16:9 wide shot, industrial roll-up door lifting slightly off concrete apron, revealing burning military Humvees and smoke-choked city skyline outside in distance", "sfx_sub_rumble", "shock", 8, True, "Escape was never an option."),
            ("Act IV: The Climax", "The Final Transmission", "Her handheld radio squeals with military encryption: Any remaining personnel inside Sector 4... strike inbound in T-minus sixty seconds.", "Cinematic 16:9 slow zoom into military tactical radio blinking amber on concrete floor, smoke drifting across lens, dramatic cliffhanger conclusion", "sfx_alarm", "cliffhanger", 10, True, "The radio just confirmed our strike order."),
        ]

        # Stretch or adapt to requested count
        while len(scenes) < count:
            idx = len(scenes)
            template_beat = beat_definitions[idx % len(beat_definitions)]
            
            act_name = "Act I: Containment"
            if idx >= act_splits["Act III: Breach & The Betrayal Twist"]:
                act_name = "Act IV: The Climax & Sequel Cliffhanger"
            elif idx >= act_splits["Act II: Resource Scramble & Darkness"]:
                act_name = "Act III: The Breach & Plot Twist"
            elif idx >= act_splits["Act I: Containment & The Viral Hook"]:
                act_name = "Act II: Resource Scramble & Darkness"

            beat = LongformSceneBeat(
                scene_index=idx + 1,
                act=act_name,
                title=f"{template_beat[1]} - Part {idx // len(beat_definitions) + 1}",
                narration=f"Scene {idx + 1}: {template_beat[2]}",
                video_prompt=f"{template_beat[3]}, scene {idx + 1}, ultra-detailed graphic novel aesthetic, cinematic lighting, 16:9 landscape aspect ratio",
                target_duration=clip_duration,
                camera_movement="slow_dolly_forward" if idx % 2 == 0 else "pan_right",
                camera_angle="eye_level" if idx % 3 == 0 else "low_angle",
                lighting="dark_cinematic_contrast",
                sfx_cue=template_beat[4],
                emotion=template_beat[5],
                tension_level=template_beat[6],
                is_short_candidate=template_beat[7] if idx < len(beat_definitions) else False,
                short_hook=template_beat[8] if idx < len(beat_definitions) else None,
            )
            scenes.append(beat)

        return scenes[:count]
