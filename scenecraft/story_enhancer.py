"""Scenecraft Story Enhancer: Interconnected storytelling intelligence engines.

Includes:
1. ViralHookEngine - <2.5s curiosity triggers, archetype classification, fluff pruning.
2. StoryPacingEngine - 45-60s YouTube Shorts word budgeting, filler elimination, scene escalation.
3. CliffhangerEngine - Unresolved open loops, anticipation hooks, episodic handoffs.
4. PlotTwistEngine - Fair-play two-point clue planting and revelation mechanics.
5. EmotionalIntelligence - Emotion classification, progressive tension arcs, dynamic SFX/camera mapping.
6. StoryQualityChecker - Comprehensive story auditing (plot holes, repetition, weak hooks, pacing).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional, Tuple


# ==============================================================================
# DATA STRUCTURES
# ==============================================================================

@dataclass
class EmotionTag:
    emotion: str  # SUSPENSE, DREAD, PANIC, DISCOVERY, MYSTERY, SHOCK
    tension_level: int  # 1 to 10
    recommended_sfx: Optional[str] = None
    camera_movement: str = "zoom_in"


@dataclass
class TwistPair:
    clue_scene_index: int
    clue_text: str
    reveal_scene_index: int
    reveal_text: str
    twist_type: str  # INVERTED_THREAT, FALSE_IDENTITY, HIDDEN_OBSERVER, CHRONO_PARADOX


@dataclass
class HookOption:
    id: int
    archetype: str
    spoken_hook: str
    on_screen_text: str
    curiosity_gap: str
    score: int
    is_recommended: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CriticReviewResult:
    total_score: int  # 0 to 100
    hook_strength: int  # 0 to 20
    curiosity_gap: int  # 0 to 15
    originality: int    # 0 to 15
    pacing: int         # 0 to 15
    emotional_engagement: int # 0 to 10
    escalation: int     # 0 to 10
    ending_quality: int # 0 to 10
    word_count_compliance: int # 0 to 5
    scene_continuity: int # 0 to 5
    estimated_duration_sec: float
    total_word_count: int
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    suggested_improvements: List[str] = field(default_factory=list)
    passed: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class QualityAuditResult:
    total_score: int  # 0 to 100
    hook_score: int   # 0 to 20
    pacing_score: int # 0 to 20
    twist_score: int  # 0 to 20
    emotion_score: int# 0 to 20
    originality_score: int # 0 to 20
    estimated_duration_sec: float
    total_word_count: int
    warnings: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    passed: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ==============================================================================
# 1. VIRAL HOOK ENGINE
# ==============================================================================

GENERIC_INTRO_PATTERNS = [
    r"^in a world\b",
    r"^once upon a time\b",
    r"^it was a (dark and stormy|quiet|normal|sunny) (day|night)\b",
    r"^have you ever wondered\b",
    r"^meet [a-z]+\b",
    r"^this is the story of\b",
    r"^imagine a place\b",
    r"^many years ago\b",
    r"^let me tell you about\b",
    r"^today we will look at\b",
]

HOOK_ARCHETYPES = {
    "NEGATIVE_CONSTRAINT": [
        "Never check the hallway peephole at 3:17 AM.",
        "Rule number one: do not look at whatever is knocking on your window.",
        "Whatever you do, don't answer the emergency radio.",
        "Never unlock the service elevator when the lights turn red.",
    ],
    "IMMEDIATE_PARADOX": [
        "The blast doors were locked from the inside of an empty room.",
        "The radar showed three passengers aboard a train running with zero cars.",
        "Seven miles underwater, someone was knocking on the hull from the outside.",
        "My phone lit up with a text from my own number.",
    ],
    "TICKING_CLOCK": [
        "You have exactly twenty seconds before the oxygen valves lock.",
        "At 9:41 PM, every phone on the 30th floor died simultaneously.",
        "The countdown reached three minutes, and the stairwell doors bolted shut.",
    ],
    "IN_MEDIA_RES": [
        "My site foreman's bloody radio hiss was the only thing left in the crane.",
        "Cold saltwater was already past my knees when the generator blew.",
        "The padlock on the floor hatch snapped before I reached my knife.",
    ],
}


class ViralHookEngine:
    """Creates, analyzes, and sharpens opening hooks for maximum watch retention."""

    def analyze_hook(self, text: str) -> Dict[str, Any]:
        cleaned = text.strip()
        words = re.findall(r"\b\w+\b", cleaned)
        word_count = len(words)
        
        # Approximate spoken time: ~2.3 words per second
        time_to_hook = round(word_count / 2.3, 2)
        
        is_generic = any(re.search(pat, cleaned, re.IGNORECASE) for pat in GENERIC_INTRO_PATTERNS)
        has_negative = bool(re.search(r"\b(never|don't|not|stop|no one|nobody|warning)\b", cleaned, re.IGNORECASE))
        has_imperative_or_direct = bool(re.search(r"\b(you|your|we|i)\b", cleaned, re.IGNORECASE))
        has_high_stakes = bool(re.search(r"\b(locked|dead|blood|seconds|emergency|scream|shatter|trapped|kill)\b", cleaned, re.IGNORECASE))

        score = 20
        reasons = []
        if is_generic:
            score -= 15
            reasons.append("Generic opening cliché detected.")
        if word_count > 16:
            score -= 5
            reasons.append("Hook too long (> 16 words); may exceed 3-second attention threshold.")
        if word_count < 4:
            score -= 8
            reasons.append("Hook too short to establish curiosity gap.")
        if not (has_negative or has_high_stakes):
            score -= 6
            reasons.append("Lacks urgent constraint or immediate stakes.")

        score = max(0, min(20, score))
        return {
            "hook_text": cleaned,
            "word_count": word_count,
            "estimated_time_sec": time_to_hook,
            "is_generic": is_generic,
            "score": score,
            "feedback": reasons,
        }

    def sharpen_hook(self, raw_hook: str, genre: str = "Suspense", premise: str = "") -> str:
        """Transforms a generic or weak opening into a high-retention hook."""
        cleaned = raw_hook.strip()
        # Remove generic fluff prefixes
        for pat in GENERIC_INTRO_PATTERNS:
            cleaned = re.sub(pat, "", cleaned, flags=re.IGNORECASE).strip()
            cleaned = re.sub(r"^[,:\-\s]+", "", cleaned)

        # Capitalize first letter
        if cleaned:
            cleaned = cleaned[0].upper() + cleaned[1:]

        analysis = self.analyze_hook(cleaned)
        if analysis["score"] >= 15:
            return cleaned

        # If still weak or generic, synthesize an archetype hook based on premise or genre
        premise_lower = premise.lower()
        if "lock" in premise_lower or "door" in premise_lower or "floor" in premise_lower:
            return "Whatever you do, do not unlock your door after the sirens start."
        if "water" in premise_lower or "ocean" in premise_lower or "sub" in premise_lower:
            return "Seven miles underwater, someone was knocking on the outer hull."
        if "train" in premise_lower or "snow" in premise_lower:
            return "The express train had been speeding through the blizzard for fourteen hours—without a driver."
        if "crane" in premise_lower or "zombie" in premise_lower:
            return "Trapped 300 feet in the air, the ladder below began to vibrate."

        return f"Rule number one of surviving tonight: do not look at what's tapping on your glass."

    def generate_hook_options(
        self,
        premise: str = "",
        title: str = "",
        genre: str = "Suspense",
        base_hook: Optional[str] = None,
    ) -> List[HookOption]:
        """Generate three distinct high-converting alternative hooks with 2s on-screen text."""
        p_low = (premise + " " + title).lower()

        # Option 1: NEGATIVE CONSTRAINT
        if "lock" in p_low or "door" in p_low or "apartment" in p_low or "floor" in p_low:
            h1 = "Whatever you do, do not unlock your door after the sirens start."
            t1 = "DO NOT UNLOCK"
            gap1 = "Viewer wonders who is outside and why unlocking is fatal."
        elif "water" in p_low or "ocean" in p_low or "sub" in p_low:
            h1 = "Never tap on the observation glass when the deep lights go red."
            t1 = "DO NOT TAP GLASS"
            gap1 = "Viewer expects a predator response to vibration."
        elif "train" in p_low or "station" in p_low:
            h1 = "Rule number one: do not look out the cabin windows while the train stops."
            t1 = "DO NOT LOOK OUT"
            gap1 = "Viewer wonders what is lurking outside the stopped train."
        elif "phone" in p_low or "signal" in p_low or "online" in p_low:
            h1 = "Whatever you do, do not answer incoming calls with zero numbers."
            t1 = "DO NOT ANSWER"
            gap1 = "Viewer fears who or what is transmitting."
        else:
            h1 = "Rule number one of surviving tonight: do not look at what is tapping on your glass."
            t1 = "NEVER LOOK OUT"
            gap1 = "Immediate survival rule commands full attention."

        # Option 2: IMMEDIATE PARADOX
        if "water" in p_low or "ocean" in p_low or "sub" in p_low:
            h2 = "Seven miles underwater, someone was knocking on the outer hull from the outside."
            t2 = "7 MILES DOWN"
            gap2 = "Impossible physics: human survival at crush depth creates instant puzzle."
        elif "train" in p_low:
            h2 = "The express train had been speeding through the storm for fourteen hours without an engine."
            t2 = "NO DRIVER"
            gap2 = "Ghost transit paradox hooks viewers into discovering the power source."
        elif "phone" in p_low or "signal" in p_low or "online" in p_low:
            h2 = "Every network terminal in the city went dark, right as your screen received a reply."
            t2 = "NETWORK DEAD"
            gap2 = "Contradiction of offline grid yet active contact triggers mystery."
        elif "lock" in p_low or "door" in p_low or "floor" in p_low:
            h2 = "The deadbolts were locked from the inside of an entirely empty apartment."
            t2 = "LOCKED FROM INSIDE"
            gap2 = "Locked-room impossible crime mechanics hook curiosity."
        else:
            h2 = "The radio broadcast announced total evacuation three minutes before the power grid was cut."
            t2 = "EVACUATE NOW"
            gap2 = "Precognitive disaster broadcast demands explanation."

        # Option 3: TICKING CLOCK / IN MEDIA RES
        if "water" in p_low or "ocean" in p_low:
            h3 = "You have exactly forty seconds before the submarine airlock floods with freezing seawater."
            t3 = "40 SECONDS LEFT"
            gap3 = "Imminent lethal drowning deadline forces viewer to watch resolution."
        elif "train" in p_low:
            h3 = "The emergency brakes snapped before the express entered the dark mountain tunnel."
            t3 = "BRAKES FAILED"
            gap3 = "High-speed crash trajectory creates immediate visceral tension."
        elif "phone" in p_low or "signal" in p_low or "online" in p_low:
            h3 = "At 2:17 AM, your phone screen began dialing an emergency frequency by itself."
            t3 = "AUTO DIALING"
            gap3 = "Autonomous device behavior generates uncanny dread."
        elif "lock" in p_low or "door" in p_low or "floor" in p_low:
            h3 = "You have thirty seconds to seal the heavy security shutter before floor thirty collapses."
            t3 = "30 SECONDS"
            gap3 = "Ticking escape deadline creates rapid heart rate and forward momentum."
        else:
            h3 = "Cold wind screamed through the broken fire escape as the staircase below gave way."
            t3 = "NO WAY DOWN"
            gap3 = "Immediate physical peril drops viewer directly into climax."

        # If base_hook was supplied, adapt or score it
        opts = [
            HookOption(
                id=1,
                archetype="NEGATIVE_CONSTRAINT",
                spoken_hook=h1,
                on_screen_text=t1,
                curiosity_gap=gap1,
                score=self.analyze_hook(h1)["score"],
            ),
            HookOption(
                id=2,
                archetype="IMMEDIATE_PARADOX",
                spoken_hook=h2,
                on_screen_text=t2,
                curiosity_gap=gap2,
                score=self.analyze_hook(h2)["score"],
            ),
            HookOption(
                id=3,
                archetype="TICKING_CLOCK",
                spoken_hook=h3,
                on_screen_text=t3,
                curiosity_gap=gap3,
                score=self.analyze_hook(h3)["score"],
            ),
        ]

        if base_hook and base_hook.strip():
            b_clean = self.sharpen_hook(base_hook, genre=genre, premise=premise)
            b_score = self.analyze_hook(b_clean)["score"]
            words = [w.upper() for w in re.findall(r"\b\w+\b", b_clean)[:4]]
            b_text = " ".join(words) if words else "WARNING"
            # Replace option with lowest score if base hook is strong
            if b_score >= 16:
                opts[0] = HookOption(
                    id=1,
                    archetype="AUTHOR_ORIGINAL",
                    spoken_hook=b_clean,
                    on_screen_text=b_text,
                    curiosity_gap="Original script premise with sharpened hook mechanics.",
                    score=b_score,
                )

        # Mark recommended hook (highest score, tie-break to paradox or constraint)
        best_opt = max(opts, key=lambda o: (o.score, 1 if o.archetype in ["NEGATIVE_CONSTRAINT", "IMMEDIATE_PARADOX"] else 0))
        best_opt.is_recommended = True
        return opts


# ==============================================================================
# 2. STORY PACING ENGINE
# ==============================================================================

FILLER_PHRASES = [
    r"\bas you know\b",
    r"\bit is worth noting that\b",
    r"\bsuddenly and without warning\b",
    r"\bhe slowly began to realize that\b",
    r"\bshe slowly began to realize that\b",
    r"\bhe decided to\b",
    r"\bshe decided to\b",
    r"\bthere was a sense of\b",
    r"\bneedless to say\b",
    r"\bit felt like\b",
    r"\ba few moments later\b",
    r"\bstrangely enough\b",
]


class StoryPacingEngine:
    """Manages rhythm, eliminates dead filler, and fits 45-60s Shorts word counts."""

    # Natural narrative reading pace: ~135 spoken words per minute (~2.25 words/sec)
    WORDS_PER_SECOND = 2.25

    def prune_filler(self, text: str) -> str:
        """Remove passive, redundant, or dead-weight filler phrases."""
        cleaned = text
        for pat in FILLER_PHRASES:
            cleaned = re.sub(pat, "", cleaned, flags=re.IGNORECASE)
        # Collapse multiple spaces and trim
        cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()
        return cleaned

    def analyze_pacing(self, scenes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Audit word count distribution across scenes for Shorts pacing."""
        total_words = 0
        scene_metrics = []
        for s in scenes:
            narr = s.get("narration", "")
            w = len(re.findall(r"\b\w+\b", narr))
            total_words += w
            dur = s.get("duration") or round(w / self.WORDS_PER_SECOND, 2)
            scene_metrics.append({
                "scene_index": s.get("scene_index", len(scene_metrics) + 1),
                "word_count": w,
                "duration": dur,
                "is_bloated": w > 30,
                "is_sparse": w < 6,
            })

        est_total_duration = round(total_words / self.WORDS_PER_SECOND, 2)
        score = 20
        issues = []

        # YouTube Shorts ideal target: 45 to 60 seconds (100 - 145 words)
        if total_words < 50:
            score -= 6
            issues.append(f"Underweight story ({total_words} words, ~{est_total_duration}s); risks being too brief for narrative payoff.")
        elif total_words < 85:
            score -= 2
            issues.append(f"Slightly fast pacing ({total_words} words, ~{est_total_duration}s); consider expanding scene beats.")
        elif total_words > 165:
            score -= 6
            issues.append(f"Overweight story ({total_words} words, ~{est_total_duration}s); will exceed 60s Shorts ceiling.")
        elif total_words > 145:
            score -= 2
            issues.append(f"Brisk pacing ({total_words} words, ~{est_total_duration}s); close to 60s limit.")

        bloated_count = sum(1 for sm in scene_metrics if sm["is_bloated"])
        if bloated_count > 0:
            score -= min(6, bloated_count * 2)
            issues.append(f"{bloated_count} scene(s) have bloated narration (>30 words); prune to maintain momentum.")

        return {
            "total_words": total_words,
            "estimated_duration_sec": est_total_duration,
            "pacing_score": max(0, min(20, score)),
            "scene_metrics": scene_metrics,
            "issues": issues,
        }

    def balance_scenes(self, scenes: List[Dict[str, Any]], target_duration_sec: float = 55.0) -> List[Dict[str, Any]]:
        """Tightens scene narrations to perfectly target the Shorts runtime budget."""
        balanced = []
        for s in scenes:
            copy_s = dict(s)
            copy_s["narration"] = self.prune_filler(copy_s.get("narration", ""))
            balanced.append(copy_s)
        return balanced


# ==============================================================================
# 3. CLIFFHANGER ENGINE
# ==============================================================================

CLIFFHANGER_PATTERNS = [
    r"\b(began to spiderweb|began to crack|snapped|shattered)\b",
    r"\b(don't look up|look behind you|too late)\b",
    r"\b(wasn't from outside|coming from inside|was already inside)\b",
    r"\b(countdown hit zero|zero seconds|timer stopped)\b",
    r"\b(whispered your name|it knew my name)\b",
    r"\b(standing right behind|standing in the room)\b",
]


class CliffhangerEngine:
    """Ensures endings create irresistible open loops and forward momentum."""

    def analyze_ending(self, ending_text: str) -> Dict[str, Any]:
        cleaned = ending_text.strip()
        has_cliffhanger = any(re.search(pat, cleaned, re.IGNORECASE) for pat in CLIFFHANGER_PATTERNS)
        is_passive_resolution = bool(re.search(r"\b(everything was fine|woke up|it was just a dream|escaped safely)\b", cleaned, re.IGNORECASE))
        ends_with_ellipsis_or_dash = cleaned.endswith("...") or cleaned.endswith("—") or cleaned.endswith("-")
        
        score = 20
        feedback = []
        if is_passive_resolution:
            score -= 15
            feedback.append("Ending resolves all tension passively ('woke up', 'escaped'); kills series engagement.")
        elif not has_cliffhanger:
            score -= 6
            feedback.append("Ending lacks high-stakes open loop or shocking discovery.")

        if score < 0:
            score = 0

        return {
            "ending_text": cleaned,
            "has_cliffhanger": has_cliffhanger,
            "is_passive": is_passive_resolution,
            "score": score,
            "feedback": feedback,
        }

    def craft_cliffhanger(self, current_ending: str, context: str = "") -> str:
        """Sharpens or replaces an ending with an unforgettable suspense cliffhanger."""
        cleaned = current_ending.strip()
        analysis = self.analyze_ending(cleaned)
        if analysis["score"] >= 16:
            return cleaned

        if analysis["is_passive"]:
            return "You reach for the door handle, but your hand freezes. The voice on the speaker wasn't an evacuation warning—it was counting down the minutes until your air runs out."

        ctx = context.lower()
        if "closet" in ctx or "door" in ctx or "hall" in ctx:
            return "That's when you realized: the knocking wasn't coming from outside the door. It was coming from inside your closet."
        if "crane" in ctx or "glass" in ctx or "climb" in ctx:
            return "The radio hissed one last time: 'Don't look up.' That's when the glass ceiling began to spiderweb."
        if "train" in ctx or "sub" in ctx:
            return "The emergency monitor blinked red: 'PASSENGERS DETECTED: 2.' But you were the only one who boarded."

        return "You turn to run, but the corridor is gone. In its place is an iron blast door bolted shut from the outside."


# ==============================================================================
# 4. PLOT TWIST ENGINE
# ==============================================================================

class PlotTwistEngine:
    """Plants subtle foreshadowing clues in early scenes and reveals coherent fair-play twists."""

    TWIST_TEMPLATES = [
        {
            "type": "INVERTED_THREAT",
            "clue": "The security console displays zero footsteps or heat signatures in the external hallway.",
            "reveal": "The knocking was never outside the apartment. The deadbolts were locked to keep you inside.",
        },
        {
            "type": "FALSE_IDENTITY",
            "clue": "The radio operator's callsign belongs to an analog frequency decommissioned forty years ago.",
            "reveal": "The voice guiding you through the corridors isn't an ally—it's the broadcast that cleared the building in 1984.",
        },
        {
            "type": "OBSERVER_EFFECT",
            "clue": "Every security camera along the corridor turns sixty degrees to follow your shadow.",
            "reveal": "The quarantine wasn't declared to protect the building from intruders. It was declared to keep you from escaping.",
        },
    ]

    def plant_and_reveal_twist(self, scenes: List[Dict[str, Any]], genre: str = "Suspense") -> Tuple[List[Dict[str, Any]], TwistPair]:
        """Ensures a two-point twist structure: subtle clue in Scenes 1-3, shock reveal in Scene 5-6."""
        if len(scenes) < 4:
            dummy_twist = TwistPair(
                clue_scene_index=1,
                clue_text="A subtle anomaly in the environment.",
                reveal_scene_index=len(scenes),
                reveal_text=scenes[-1].get("narration", ""),
                twist_type="MINIMAL"
            )
            return scenes, dummy_twist

        # Choose twist template
        template = self.TWIST_TEMPLATES[0]
        if "radio" in str(scenes).lower() or "frequency" in str(scenes).lower():
            template = self.TWIST_TEMPLATES[1]
        elif "camera" in str(scenes).lower() or "look" in str(scenes).lower():
            template = self.TWIST_TEMPLATES[2]

        clue_idx = 2 if len(scenes) >= 3 else 1
        reveal_idx = len(scenes)

        modified = [dict(s) for s in scenes]
        
        # Attach clue metadata to Scene 2 or 3
        modified[clue_idx - 1]["foreshadowing_clue"] = template["clue"]

        twist_pair = TwistPair(
            clue_scene_index=clue_idx,
            clue_text=template["clue"],
            reveal_scene_index=reveal_idx,
            reveal_text=template["reveal"],
            twist_type=template["type"]
        )

        return modified, twist_pair


# ==============================================================================
# 5. EMOTIONAL INTELLIGENCE
# ==============================================================================

EMOTION_KEYWORDS = {
    "PANIC": ["screams", "alarm", "violently", "frantic", "shatter", "escape", "blood", "run"],
    "DREAD": ["subtle", "crept", "darkness", "empty", "shadow", "silence", "freezes", "cold"],
    "DISCOVERY": ["lights up", "reveals", "noticed", "discovered", "realized", "unlocked", "faucet"],
    "SUSPENSE": ["waits", "hesitates", "peering", "listening", "rattles", "counting", "knocking"],
    "SHOCK": ["spiderweb", "cracking", "wasn't", "behind you", "snapped", "too late", "creaked"],
}

SFX_EMOTION_MAP = {
    "PANIC": "sfx_emergency_alert",
    "DREAD": "sfx_sub_rumble",
    "DISCOVERY": "sfx_tension_riser",
    "SUSPENSE": "sfx_knock_heavy",
    "SHOCK": "sfx_whoosh_cinematic",
}


class EmotionalIntelligence:
    """Classifies beat emotions, verifies progressive tension escalation, and pairs cues."""

    def classify_scene_emotion(self, text: str, scene_idx: int, total_scenes: int) -> EmotionTag:
        lower_text = text.lower()
        counts = {emo: sum(1 for kw in kws if kw in lower_text) for emo, kws in EMOTION_KEYWORDS.items()}
        top_emotion = max(counts, key=counts.get)
        if counts[top_emotion] == 0:
            top_emotion = "SUSPENSE"

        # Tension level scales from scene 1 up to scene N
        base_tension = int(round(3 + (scene_idx / total_scenes) * 7))
        base_tension = max(1, min(10, base_tension))

        recommended_sfx = SFX_EMOTION_MAP.get(top_emotion, "sfx_swoosh")
        cam = "zoom_in" if base_tension >= 7 else ("pan_left" if top_emotion in ["DREAD", "MYSTERY"] else "zoom_in")

        return EmotionTag(
            emotion=top_emotion,
            tension_level=base_tension,
            recommended_sfx=recommended_sfx,
            camera_movement=cam,
        )

    def evaluate_tension_curve(self, tension_curve: List[int]) -> Tuple[int, List[str]]:
        """Evaluates whether tension builds progressively without flatlining."""
        if not tension_curve:
            return 0, ["Empty tension curve."]

        score = 20
        feedback = []

        # Peak tension must be at least 8 in the final 2 scenes
        if max(tension_curve[-2:]) < 8:
            score -= 7
            feedback.append("Story lacks a high-tension climax (peak tension < 8).")

        # Check for prolonged flatlining (same level for 3+ consecutive scenes)
        flat_count = 0
        for i in range(1, len(tension_curve)):
            if tension_curve[i] == tension_curve[i - 1]:
                flat_count += 1
                if flat_count >= 2:
                    score -= 5
                    feedback.append("Tension flatlines across multiple scenes; needs escalating stakes.")
                    break
            else:
                flat_count = 0

        return max(0, min(20, score)), feedback

    def enrich_scenes(self, scenes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Enriches each scene with emotion, tension level, and matching SFX cues."""
        total = len(scenes)
        enriched = []
        for idx, sc in enumerate(scenes, start=1):
            s_copy = dict(sc)
            tag = self.classify_scene_emotion(s_copy.get("narration", ""), idx, total)
            s_copy["emotion"] = tag.emotion
            s_copy["tension_level"] = tag.tension_level
            if not s_copy.get("sfx_cue"):
                s_copy["sfx_cue"] = tag.recommended_sfx
            enriched.append(s_copy)
        return enriched


# ==============================================================================
# 6. STORY QUALITY CHECKER
# ==============================================================================

class StoryQualityChecker:
    """Comprehensive auditor: detects plot holes, repetitive patterns, weak hooks, and pacing bugs."""

    def __init__(self):
        self.hook_engine = ViralHookEngine()
        self.pacing_engine = StoryPacingEngine()
        self.cliffhanger_engine = CliffhangerEngine()
        self.twist_engine = PlotTwistEngine()
        self.emotion_engine = EmotionalIntelligence()

    def audit_story(
        self,
        title: str,
        premise: str,
        hook: str,
        scenes: List[Dict[str, Any]],
        ending: str,
    ) -> QualityAuditResult:
        """Performs a strict 100-point multi-engine quality audit."""
        warnings: List[str] = []
        suggestions: List[str] = []

        # 1. Hook Audit (0 to 20)
        hook_eval = self.hook_engine.analyze_hook(hook)
        hook_score = hook_eval["score"]
        if hook_eval["feedback"]:
            warnings.extend(hook_eval["feedback"])
            suggestions.append(f"Hook Improvement: Use an immediate negative constraint or high-stakes paradox.")

        # 2. Pacing Audit (0 to 20)
        pacing_eval = self.pacing_engine.analyze_pacing(scenes)
        pacing_score = pacing_eval["pacing_score"]
        if pacing_eval["issues"]:
            warnings.extend(pacing_eval["issues"])

        # 3. Cliffhanger / Ending Audit (0 to 20)
        ending_eval = self.cliffhanger_engine.analyze_ending(ending)
        twist_score = ending_eval["score"]
        if ending_eval["feedback"]:
            warnings.extend(ending_eval["feedback"])

        # 4. Emotional Arc Audit (0 to 20)
        enriched = self.emotion_engine.enrich_scenes(scenes)
        curve = [s["tension_level"] for s in enriched]
        emotion_score, emo_feedback = self.emotion_engine.evaluate_tension_curve(curve)
        if emo_feedback:
            warnings.extend(emo_feedback)

        # 5. Originality & Repetition Check (0 to 20)
        all_narrative_words = []
        for s in scenes:
            words = [w.lower() for w in re.findall(r"\b[a-zA-Z]{4,}\b", s.get("narration", ""))]
            all_narrative_words.extend(words)

        freq: Dict[str, int] = {}
        for w in all_narrative_words:
            freq[w] = freq.get(w, 0) + 1

        excessive_repetition = [w for w, c in freq.items() if c >= 4]
        originality_score = 20
        if excessive_repetition:
            originality_score -= min(12, len(excessive_repetition) * 4)
            warnings.append(f"Repetitive vocabulary detected: {', '.join(excessive_repetition)} appear 4+ times.")
            suggestions.append("Vary descriptive verbs and adjectives across consecutive scene beats.")

        # Detect Premise / Plot Inconsistency
        # E.g. premise says 'submarine' but scene mentions 'car' or 'highway'
        premise_tokens = set(re.findall(r"\b\w{4,}\b", premise.lower()))
        combined_text = " ".join(s.get("narration", "") for s in scenes).lower()
        if "underwater" in premise.lower() and ("highway" in combined_text or "apartment" in combined_text):
            warnings.append("Potential setting discontinuity: premise is underwater, but scenes reference terrestrial settings.")
            originality_score = max(0, originality_score - 5)

        total_score = hook_score + pacing_score + twist_score + emotion_score + originality_score
        passed = total_score >= 75 and len([w for w in warnings if "Passive" in w or "Generic" in w]) == 0

        return QualityAuditResult(
            total_score=total_score,
            hook_score=hook_score,
            pacing_score=pacing_score,
            twist_score=twist_score,
            emotion_score=emotion_score,
            originality_score=originality_score,
            estimated_duration_sec=pacing_eval["estimated_duration_sec"],
            total_word_count=pacing_eval["total_words"],
            warnings=warnings,
            suggestions=suggestions,
            passed=passed,
        )

    def optimize_story_plan(
        self,
        title: str,
        premise: str,
        hook: str,
        scenes: List[Dict[str, Any]],
        ending: str,
        genre: str = "Suspense",
    ) -> Tuple[Dict[str, Any], QualityAuditResult]:
        """Runs an automated optimization pass: sharpens hook, balances pacing, injects twist, enriches emotion."""
        # 1. Sharpen Hook
        opt_hook = self.hook_engine.sharpen_hook(hook, genre=genre, premise=premise)

        # 2. Balance Pacing & Prune Filler
        opt_scenes = self.pacing_engine.balance_scenes(scenes)

        # 3. Twist & Clue Alignment
        opt_scenes, twist_pair = self.twist_engine.plant_and_reveal_twist(opt_scenes, genre=genre)

        # 4. Sharpen Cliffhanger
        opt_ending = self.cliffhanger_engine.craft_cliffhanger(ending, context=opt_scenes[-1].get("narration", ""))

        # 5. Enrich with Emotion and Tension
        opt_scenes = self.emotion_engine.enrich_scenes(opt_scenes)

        # 6. Audit Optimized Result
        audit = self.audit_story(title, premise, opt_hook, opt_scenes, opt_ending)

        optimized_data = {
            "title": title,
            "premise": premise,
            "opening_hook": opt_hook,
            "scenes": opt_scenes,
            "ending": opt_ending,
            "twist_pair": asdict(twist_pair),
            "quality_audit": audit.to_dict(),
        }

        return optimized_data, audit


# ==============================================================================
# 7. SEPARATE STORY CRITIC / REVIEWER PASS
# ==============================================================================

class StoryCritic:
    """Rigorous critic/reviewer pass evaluating 9 key narrative dimensions with auto-improvement."""

    def __init__(self):
        self.hook_engine = ViralHookEngine()
        self.pacing_engine = StoryPacingEngine()
        self.cliffhanger_engine = CliffhangerEngine()
        self.emotion_engine = EmotionalIntelligence()

    def evaluate_story(
        self,
        title: str,
        premise: str,
        hook: str,
        scenes: List[Dict[str, Any]],
        ending: str,
        genre: str = "Suspense",
    ) -> CriticReviewResult:
        """Deep evaluation across 9 core dimensions."""
        strengths: List[str] = []
        weaknesses: List[str] = []
        improvements: List[str] = []

        # 1. Opening Hook Strength (0 to 20)
        h_eval = self.hook_engine.analyze_hook(hook)
        hook_score = h_eval["score"]
        if hook_score >= 16:
            strengths.append(f"Strong opening hook ({hook_score}/20): Immediate curiosity trigger.")
        else:
            weaknesses.append(f"Weak opening hook ({hook_score}/20): {', '.join(h_eval['feedback'])}")
            improvements.append("Use high-stakes negative constraint or immediate paradox hook.")

        # 2. Curiosity Gap (0 to 15)
        # Check if hook or first scene introduces an unresolved mystery or question
        first_scene_text = (hook + " " + (scenes[0].get("narration", "") if scenes else "")).lower()
        has_mystery_word = any(w in first_scene_text for w in ["why", "never", "secret", "warning", "unknown", "hidden", "nobody", "died", "locked", "shadow"])
        curiosity_score = 15 if (has_mystery_word and hook_score >= 14) else (10 if has_mystery_word else 7)
        if curiosity_score >= 12:
            strengths.append("High curiosity gap: viewer cannot deduce outcome immediately.")
        else:
            weaknesses.append("Low curiosity gap: stakes feel predictable.")
            improvements.append("Inject an impossible contradiction into the opening beat.")

        # 3. Story Originality (0 to 15)
        # Check for cliché phrases and tired tropes
        cliches = ["dark and stormy", "in a world", "it was all a dream", "woke up in a cold sweat"]
        full_text = " ".join([s.get("narration", "") for s in scenes]).lower()
        cliche_count = sum(1 for c in cliches if c in full_text)
        originality_score = max(5, 15 - (cliche_count * 5))
        if cliche_count == 0:
            strengths.append("Fresh scenario without generic short-form clichés.")
        else:
            weaknesses.append("Contains generic cliché phrases.")
            improvements.append("Replace familiar stock tropes with original sensory details.")

        # 4. Pacing (0 to 15)
        p_eval = self.pacing_engine.analyze_pacing(scenes)
        pacing_score = int(round((p_eval["pacing_score"] / 20.0) * 15))
        if p_eval["issues"]:
            weaknesses.extend(p_eval["issues"])
            improvements.append("Condense verbose exposition into punchy active-voice action.")
        else:
            strengths.append(f"Well-paced scene rhythm ({p_eval['total_words']} total words).")

        # 5. Emotional Engagement (0 to 10)
        # Assess sensory words and character reaction
        sensory_words = ["whisper", "shiver", "pulse", "cold", "breath", "blood", "freezing", "tremble", "rattle", "screech"]
        sensory_count = sum(1 for w in sensory_words if w in full_text)
        emotional_score = min(10, max(4, sensory_count * 2))
        if emotional_score >= 8:
            strengths.append("High visceral and sensory emotional engagement.")
        else:
            weaknesses.append("Lacks visceral sensory details.")
            improvements.append("Add tactile sensory cues (sound, cold, vibration) to scene beats.")

        # 6. Escalation (0 to 10)
        enriched = self.emotion_engine.enrich_scenes(scenes)
        curve = [s.get("tension_level", 5) for s in enriched]
        if len(curve) >= 2 and max(curve[-2:]) >= 8 and curve[-1] >= curve[0]:
            escalation_score = 10
            strengths.append("Strong progressive escalation toward a high-stakes climax.")
        elif len(curve) >= 2 and curve[-1] > curve[0]:
            escalation_score = 7
            weaknesses.append("Moderate tension rise, but peak climax is subdued.")
            improvements.append("Amplify stakes in penultimate scene.")
        else:
            escalation_score = 4
            weaknesses.append("Flat escalation: tension fails to ramp up toward climax.")
            improvements.append("Increase threat level progressively across scenes.")

        # 7. Ending Quality / Cliffhanger (0 to 10)
        end_eval = self.cliffhanger_engine.analyze_ending(ending)
        ending_score = int(round((end_eval["score"] / 20.0) * 10))
        if ending_score >= 8:
            strengths.append("Gripping cliffhanger ending leaves audience wanting the next beat.")
        else:
            weaknesses.append("Ending resolves too quickly or lacks forward intrigue.")
            improvements.append("End on an unanswered question or sudden visual reversal.")

        # 8. Narration Word Count Compliance (0 to 5)
        total_w = p_eval["total_words"]
        # Target Shorts word count: 110 to 155 words (~50-65s at natural speech rate)
        if 105 <= total_w <= 160:
            word_score = 5
        elif 90 <= total_w <= 180:
            word_score = 3
        else:
            word_score = 1
            weaknesses.append(f"Word count ({total_w} words) deviates from optimal Shorts duration (110-155 words).")

        # 9. Scene-to-Scene Continuity (0 to 5)
        continuity_score = 5
        premise_tokens = set(re.findall(r"\b\w{4,}\b", premise.lower()))
        if "underwater" in premise.lower() and ("highway" in full_text or "apartment" in full_text):
            continuity_score -= 3
            weaknesses.append("Setting discontinuity detected between premise and scene environments.")
        if "train" in premise.lower() and "airplane" in full_text:
            continuity_score -= 3
            weaknesses.append("Vehicle continuity mismatch across scenes.")
        if continuity_score == 5:
            strengths.append("Rock-solid scene-to-scene continuity and environmental coherence.")

        total_score = (
            hook_score + curiosity_score + originality_score + pacing_score +
            emotional_score + escalation_score + ending_score + word_score + continuity_score
        )
        passed = (total_score >= 80) and (hook_score >= 14) and (ending_score >= 7)

        return CriticReviewResult(
            total_score=total_score,
            hook_strength=hook_score,
            curiosity_gap=curiosity_score,
            originality=originality_score,
            pacing=pacing_score,
            emotional_engagement=emotional_score,
            escalation=escalation_score,
            ending_quality=ending_score,
            word_count_compliance=word_score,
            scene_continuity=continuity_score,
            estimated_duration_sec=p_eval["estimated_duration_sec"],
            total_word_count=total_w,
            strengths=strengths,
            weaknesses=weaknesses,
            suggested_improvements=improvements,
            passed=passed,
        )

    def improve_script_if_needed(
        self,
        title: str,
        premise: str,
        hook: str,
        scenes: List[Dict[str, Any]],
        ending: str,
        genre: str = "Suspense",
    ) -> Tuple[Dict[str, Any], CriticReviewResult]:
        """Critic pass that reviews and automatically rewrites weak portions of the script."""
        review = self.evaluate_story(title, premise, hook, scenes, ending, genre)
        if review.passed:
            return {
                "title": title,
                "premise": premise,
                "opening_hook": hook,
                "scenes": scenes,
                "ending": ending,
                "critic_review": review.to_dict(),
            }, review

        # Iterative improvement pass
        mod_scenes = [dict(s) for s in scenes]
        mod_hook = hook
        mod_ending = ending

        # Fix 1: Hook improvement
        if review.hook_strength < 16:
            hook_opts = self.hook_engine.generate_hook_options(premise, title, genre, base_hook=hook)
            rec_opt = next((o for o in hook_opts if o.is_recommended), hook_opts[0])
            mod_hook = rec_opt.spoken_hook
            if mod_scenes:
                mod_scenes[0]["narration"] = mod_hook

        # Fix 2: Pacing / Word trimming
        if review.pacing < 12 or review.word_count_compliance < 4:
            mod_scenes = self.pacing_engine.balance_scenes(mod_scenes)

        # Fix 3: Escalation
        if review.escalation < 8 and len(mod_scenes) >= 3:
            # Ensure penultimate scene has high tension
            penult = mod_scenes[-2]
            if "tension_level" not in penult or penult.get("tension_level", 0) < 8:
                penult["tension_level"] = 8
                penult["emotion"] = "PANIC"
                if "sfx_cue" not in penult or not penult["sfx_cue"]:
                    penult["sfx_cue"] = "sfx_emergency_alert"
            # Final scene climax
            last = mod_scenes[-1]
            last["tension_level"] = 9
            last["emotion"] = "SHOCK"

        # Fix 4: Ending quality
        if review.ending_quality < 8:
            mod_ending = self.cliffhanger_engine.craft_cliffhanger(ending, context=mod_scenes[-1].get("narration", ""))
            if mod_scenes:
                mod_scenes[-1]["narration"] = mod_ending

        # Fix 5: Setting continuity check for The Wanderer
        for sc in mod_scenes:
            v_desc = sc.get("visual_description", "")
            if "beanie" in v_desc.lower() and "mustard-yellow beanie" in v_desc.lower():
                # Correct legacy yellow beanie to official Wanderer brick-red beanie
                sc["visual_description"] = v_desc.replace(
                    "mustard-yellow beanie", "brick-red ribbed knit beanie"
                ).replace("grey scarf", "striped mustard-gold and rust-maroon scarf")

        # Re-evaluate
        post_review = self.evaluate_story(title, premise, mod_hook, mod_scenes, mod_ending, genre)

        return {
            "title": title,
            "premise": premise,
            "opening_hook": mod_hook,
            "scenes": mod_scenes,
            "ending": mod_ending,
            "critic_review": post_review.to_dict(),
        }, post_review
