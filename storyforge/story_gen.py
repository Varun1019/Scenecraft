"""Story and scene generator for StoryForge, including Auto-Story mode."""

from __future__ import annotations

import json
import os
import random
import time
import urllib.request
from pathlib import Path
from typing import List, Dict, Any, Optional

DEFAULT_GEMINI_MODEL = os.environ.get("STORYFORGE_GEMINI_MODEL", "gemini-3.8-flash")


def _resolve_gemini_api_key(explicit_key: Optional[str] = None) -> Optional[str]:
    """Resolve Gemini API key from explicit argument, environment, or .env file."""
    if explicit_key and explicit_key.strip():
        return explicit_key.strip()

    for var in ["GEMINI_API_KEY", "GOOGLE_API_KEY"]:
        if var in os.environ and os.environ[var].strip():
            return os.environ[var].strip()

    env_paths = [
        Path.cwd() / ".env",
        Path(__file__).resolve().parent.parent / ".env",
        Path.home() / ".env",
    ]
    for p in env_paths:
        if p.is_file():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        for var in ["GEMINI_API_KEY", "GOOGLE_API_KEY"]:
                            if line.startswith(f"{var}=") and len(line) > len(var) + 1:
                                val = line.split("=", 1)[1].strip().strip('"').strip("'")
                                if val:
                                    return val
            except Exception:
                pass
    return None


def mask_api_key(key: Optional[str]) -> str:
    """Safely mask API key for logs and errors, never exposing sensitive credentials."""
    if not key:
        return "[NONE]"
    if len(key) <= 8:
        return "***"
    return f"{key[:4]}...{key[-4:]}"


def call_gemini_api(
    prompt: str,
    system_instruction: str,
    api_key: str,
    model: Optional[str] = None,
    timeout: float = 6.0,
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Execute Gemini REST API request with conservative token limits and strict error diagnostics.

    Returns:
        (parsed_json, error_message)
    """
    masked_key = mask_api_key(api_key)
    candidate_models = [
        model or DEFAULT_GEMINI_MODEL,
        "gemini-3-flash-preview",
    ]
    seen = set()
    models_to_try = []
    for m in candidate_models:
        clean = m.split("/", 1)[1] if "/" in m else m
        if clean not in seen:
            seen.add(clean)
            models_to_try.append(clean)

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "systemInstruction": {"parts": [{"text": system_instruction}]},
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": 0.75,
            "maxOutputTokens": 2048,
        },
    }
    req_body = json.dumps(payload).encode("utf-8")
    last_error = None

    for target in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{target}:generateContent?key={api_key}"
        req = urllib.request.Request(
            url,
            data=req_body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                candidates = data.get("candidates", [])
                if candidates:
                    raw_text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                    if raw_text:
                        parsed = json.loads(raw_text)
                        if isinstance(parsed, dict) and "scenes" in parsed and len(parsed["scenes"]) >= 3:
                            return parsed, None
                        last_error = "Gemini response missing valid scenes array."
        except urllib.error.HTTPError as he:
            if he.code == 429:
                last_error = f"Gemini API Quota Exceeded (HTTP 429, key {masked_key}). Rate limit or quota exhausted."
                break  # Do not retry on quota exhaustion
            elif he.code in [400, 401, 403]:
                last_error = f"Gemini API Authentication Failed (HTTP {he.code}, key {masked_key}). Invalid key or permissions."
                break  # Do not retry on auth failure
            elif he.code == 404:
                last_error = f"Gemini Model '{target}' Not Found (HTTP 404)."
                continue  # Try fallback model
            else:
                last_error = f"Gemini API HTTP Error {he.code} on model '{target}'."
                continue
        except urllib.error.URLError as ue:
            last_error = f"Gemini API Network Connection Failed: {ue.reason} (key {masked_key})."
            break  # Do not retry on connection failure
        except TimeoutError:
            last_error = f"Gemini API Request Timed Out (exceeded {timeout}s limit on {target})."
            break
        except Exception as e:
            last_error = f"Gemini API Unexpected Error: {type(e).__name__} (key {masked_key})."
            break

    return None, last_error

SYSTEM_PROMPT = """You are an expert short-form viral fiction writer and director for YouTube Shorts.
Write an original, gripping psychological suspense, horror, mystery, or survival story in second-person perspective ('You...').
The first sentence MUST be an immediate, irresistible hook within the first 2 seconds.
Target approximately 55-65 seconds of total spoken narration across 5 to 6 sequential scenes.
The permanent character is The Wanderer: a minimalist 2D dark comic stickman with an oversized smooth warm ivory oval head, two vertical black pill eyes, neutral slit mouth, thin black stick limbs and torso, wearing a chunky brick-red ribbed knit beanie, a thick winter scarf with alternating mustard-gold and rust-maroon horizontal stripes with fringe, and a dark charcoal short-sleeved t-shirt.

For each scene provide:
- scene_index: integer 1..N (5 or 6 scenes)
- title: punchy scene title
- narration: 2 clear, suspenseful sentences spoken by narrator with natural pacing
- visual_description: detailed visual description of The Wanderer and the moody atmospheric background environment
- camera_movement: one of 'zoom_in', 'zoom_out', 'pan_left', 'pan_right'
- sfx_cue: sound effect cue ('sfx_alarm', 'sfx_knock', 'sfx_water', 'sfx_swoosh', or null)

Output valid JSON:
{
  "story_title": "...",
  "genre": "Psychological Suspense",
  "summary": "...",
  "scenes": [
    {
      "scene_index": 1,
      "title": "...",
      "narration": "...",
      "visual_description": "...",
      "camera_movement": "zoom_in",
      "sfx_cue": null
    }
  ]
}
"""

CURATED_AUTO_CONCEPTS = [
    {
        "story_title": "The Knock at 3:17 AM",
        "genre": "Psychological Suspense",
        "summary": "A high-rise resident receives an automated warning right as rhythmic knocks begin on the 30th floor door.",
        "scenes": [
            {
                "scene_index": 1,
                "title": "The Silence of the 30th Floor",
                "narration": "Whatever you do, do not check the hallway peephole at 3:17 AM. You live on the 30th floor, where nobody ever visits after midnight.",
                "visual_description": "Stickman character with round white head, black dot eyes, mustard-yellow beanie, and grey scarf standing alone in a dark apartment living room, illuminated only by a warm floor lamp and moonlight through a rainy window.",
                "camera_movement": "zoom_in",
                "sfx_cue": "sfx_swoosh"
            },
            {
                "scene_index": 2,
                "title": "The Red Broadcast",
                "narration": "Then your phone lights up across the floor with a blinding red emergency broadcast. Do not respond to human voices outside your flat.",
                "visual_description": "Stickman sitting tensely on a green couch in the dark living room, staring down at a smartphone glowing with a bright red warning exclamation triangle.",
                "camera_movement": "zoom_in",
                "sfx_cue": "sfx_alarm"
            },
            {
                "scene_index": 3,
                "title": "The Corridor Pounding",
                "narration": "Right on cue, three heavy, deliberate knocks rattle against your heavy front door. A familiar voice whispers your name from the other side.",
                "visual_description": "Stickman standing frozen in the dark hallway, staring at the apartment wooden door with deadbolts as shadows move beneath the door frame.",
                "camera_movement": "pan_left",
                "sfx_cue": "sfx_knock"
            },
            {
                "scene_index": 4,
                "title": "The Survival Instinct",
                "narration": "You back away quietly toward the bathroom, twisting the faucet to fill the tub before the building shuts down the main water pumps.",
                "visual_description": "Stickman kneeling urgently beside a white porcelain bathtub in a tiled bathroom, hands on the faucet as clean water pours into the tub under a dim mirror light.",
                "camera_movement": "zoom_in",
                "sfx_cue": "sfx_water"
            },
            {
                "scene_index": 5,
                "title": "The Chilling Truth",
                "narration": "You lean close to the peephole and peer into the empty, pitch-black hallway. The knocking wasn't coming from outside your door. It was coming from inside your closet.",
                "visual_description": "Dramatic close-up of stickman leaning against the front door, wide black dot eyes looking back into the dark apartment room toward an open closet door.",
                "camera_movement": "zoom_in",
                "sfx_cue": "sfx_knock"
            }
        ]
    },
    {
        "story_title": "The Blackout Protocol",
        "genre": "Apocalypse / Survival",
        "summary": "When the entire power grid dies simultaneously, surviving the first sixty minutes requires ruthless adherence to the rules.",
        "scenes": [
            {
                "scene_index": 1,
                "title": "Total Grid Failure",
                "narration": "When thirty city blocks go black in a single second, you have exactly six minutes before the municipal backup generators fail.",
                "visual_description": "Stickman in mustard-yellow knit beanie and grey scarf standing by floor-to-ceiling panoramic glass windows looking out over a massive city skyline plunged into complete darkness.",
                "camera_movement": "zoom_in",
                "sfx_cue": "sfx_swoosh"
            },
            {
                "scene_index": 2,
                "title": "The Final Transmission",
                "narration": "Your emergency radio hums with static before a robotic voice repeats: Civilians, barricade your doors and extinguish all indoor lights immediately.",
                "visual_description": "Stickman sitting on a green sofa, illuminated by a glowing battery-powered lantern, clutching an emergency radio with red indicators.",
                "camera_movement": "zoom_in",
                "sfx_cue": "sfx_alarm"
            },
            {
                "scene_index": 3,
                "title": "Securing The Lifeline",
                "narration": "You sprint to the bathroom and open every valve. In an urban collapse, water pressure is always the first casualty.",
                "visual_description": "Stickman in tiled bathroom kneeling beside a bathtub, filling clean water under a warm overhead lamp, steam rising as the water level rises.",
                "camera_movement": "zoom_in",
                "sfx_cue": "sfx_water"
            },
            {
                "scene_index": 4,
                "title": "Footsteps on the 30th Floor",
                "narration": "From the fire escape staircase, boots slam against concrete. Violent knocks begin on every apartment door in the hallway.",
                "visual_description": "Stickman standing tense in hallway entrance holding a heavy wrench, staring at the reinforced door deadbolts vibrating from impacts.",
                "camera_movement": "pan_left",
                "sfx_cue": "sfx_knock"
            },
            {
                "scene_index": 5,
                "title": "Rule Number One",
                "narration": "You hold your breath in the dark as footsteps pause directly outside your mat. Rule number one of the blackout: no matter who asks, you do not exist.",
                "visual_description": "Stickman in yellow beanie pressed against the interior wall next to the door in deep shadows, watching a thin beam of flashlight sweep under the door.",
                "camera_movement": "zoom_in",
                "sfx_cue": "sfx_swoosh"
            }
        ]
    },
    {
        "story_title": "The Elevator to Floor 99",
        "genre": "Uncanny Mystery",
        "summary": "A resident gets into an elevator that goes far higher than the building's physical top floor.",
        "scenes": [
            {
                "scene_index": 1,
                "title": "Late Night Departure",
                "narration": "You live in a thirty-story building, so when the elevator panel displays floor ninety-nine, you know you pressed the wrong button.",
                "visual_description": "Stickman wearing mustard-yellow beanie and grey scarf standing inside a metallic modern elevator cab, looking at glowing digital floor indicators.",
                "camera_movement": "zoom_in",
                "sfx_cue": "sfx_swoosh"
            },
            {
                "scene_index": 2,
                "title": "The Warning Tone",
                "narration": "The emergency phone inside the elevator rings with a screeching EAS tone. A voice says: Do not step out when the doors slide open.",
                "visual_description": "Stickman clutching the brass handrail inside the elevator as emergency red alarm lights flash overhead.",
                "camera_movement": "zoom_in",
                "sfx_cue": "sfx_alarm"
            },
            {
                "scene_index": 3,
                "title": "The Phantom Level",
                "narration": "With a soft chime, the doors part. Beyond lies your exact apartment, mirrored in reverse, with your own front door wide open.",
                "visual_description": "Elevator doors opening into a dim, eerie hallway that looks identical to the stickman's apartment floor, but completely silent and dark.",
                "camera_movement": "pan_right",
                "sfx_cue": "sfx_swoosh"
            },
            {
                "scene_index": 4,
                "title": "The Urgent Escape",
                "narration": "Heavy footsteps approach the threshold. Someone inside your mirrored flat is frantically hammering on the bathroom walls.",
                "visual_description": "Stickman backing up against the elevator wall, looking through the open doors into the mirrored apartment entrance.",
                "camera_movement": "zoom_in",
                "sfx_cue": "sfx_knock"
            },
            {
                "scene_index": 5,
                "title": "The Reflection",
                "narration": "You smash the door close button just as a figure steps into the light, wearing your yellow beanie and staring with your own eyes.",
                "visual_description": "Dramatic close-up of elevator doors sliding shut as two identical stickmen with yellow beanies and scarves lock eyes across the threshold.",
                "camera_movement": "zoom_in",
                "sfx_cue": "sfx_alarm"
            }
        ]
    }
]


def generate_auto_story(
    genre: Optional[str] = None,
    fallback_mode: str = "local",
    api_key: Optional[str] = None,
    allow_local_on_gemini_fail: bool = False,
) -> Dict[str, Any]:
    """Generate an original ~60s suspense story for Auto-Story mode.

    Gemini is only invoked if fallback_mode == 'gemini'. Default is 'local' (zero API cost).
    """
    if fallback_mode == "gemini":
        key = _resolve_gemini_api_key(api_key)
        if not key:
            raise RuntimeError(
                "Gemini story fallback requested (--story-fallback gemini), but no API key configured. "
                "Set GEMINI_API_KEY in .env or choose --story-fallback local."
            )
        genre_hint = f"Genre: {genre}" if genre else "Genre: High-suspense psychological thriller or survival twist"
        prompt = f"{genre_hint}\nGenerate an original viral YouTube Shorts story with a 2-second hook and 5 sequential scenes totaling 60 seconds."
        data, err = call_gemini_api(prompt, SYSTEM_PROMPT, key)
        if data and "scenes" in data and len(data["scenes"]) >= 3:
            return data

        if not allow_local_on_gemini_fail:
            raise RuntimeError(
                f"Gemini story generation failed: {err}\n"
                f"Stopped to prevent unverified quota usage. Use --allow-local-fallback to allow procedural fallback."
            )
        print(f"  [*] Gemini API failed ({err}). Activating local story engine fallback.")

    elif fallback_mode == "none":
        raise RuntimeError("No story script provided and story fallback is disabled (--story-fallback none).")

    # Local concept fallback (default)
    if genre:
        matches = [c for c in CURATED_AUTO_CONCEPTS if genre.lower() in c.get("genre", "").lower()]
        if matches:
            return json.loads(json.dumps(random.choice(matches)))
    concept = random.choice(CURATED_AUTO_CONCEPTS)
    return json.loads(json.dumps(concept))


def _generate_procedural_story(title: str) -> Dict[str, Any]:
    """Fallback high-quality procedural story generator matching reference style."""
    t_lower = title.lower()

    if "water" in t_lower or "thirst" in t_lower:
        theme = "water"
    elif "cold" in t_lower or "winter" in t_lower or "freeze" in t_lower:
        theme = "freeze"
    elif "knock" in t_lower or "neighbor" in t_lower or "door" in t_lower:
        theme = "neighbor"
    else:
        theme = "apocalypse"

    if theme == "water":
        scenes = [
            {
                "scene_index": 1,
                "title": "High Rise Isolation",
                "narration": f"You wake up to the silence of '{title}'. On the 30th floor, the world feels completely cut off.",
                "visual_description": "Stickman wearing mustard yellow beanie and grey scarf standing by floor-to-ceiling window overlooking silent dark city skyline at dawn.",
                "camera_movement": "zoom_in",
                "sfx_cue": "sfx_swoosh"
            },
            {
                "scene_index": 2,
                "title": "The Dry Tap",
                "narration": "You turn the faucet. A dry hiss escapes the pipes. Not a single drop.",
                "visual_description": "Stickman in bathroom staring down in disbelief at an empty chrome sink faucet, hands on the counter.",
                "camera_movement": "zoom_in",
                "sfx_cue": "sfx_water"
            },
            {
                "scene_index": 3,
                "title": "Emergency Alert",
                "narration": "Then your phone vibrates across the wooden floor. An emergency broadcast blinks in red.",
                "visual_description": "Close up of stickman sitting on a green couch holding a smartphone displaying a glowing red warning triangle.",
                "camera_movement": "zoom_in",
                "sfx_cue": "sfx_alarm"
            },
            {
                "scene_index": 4,
                "title": "Footsteps Outside",
                "narration": "Heavy footsteps echo down the corridor. Someone is frantically testing every door knob.",
                "visual_description": "Stickman freezing in hallway, looking toward the apartment wooden front door as shadows move under the door frame.",
                "camera_movement": "pan_left",
                "sfx_cue": "sfx_knock"
            },
            {
                "scene_index": 5,
                "title": "Filling The Reserve",
                "narration": "You rush to the tub, opening the valve just as the pressure dies for good.",
                "visual_description": "Stickman kneeling urgently beside a white bathtub, watching the last inches of clean water fill the tub.",
                "camera_movement": "zoom_in",
                "sfx_cue": "sfx_water"
            },
            {
                "scene_index": 6,
                "title": "The First Rule",
                "narration": "The knocks stop. You look through the peephole into the dark hallway, knowing the real rule: do not open.",
                "visual_description": "Stickman with yellow beanie standing in dark apartment entrance, looking closely through the door peephole.",
                "camera_movement": "zoom_in",
                "sfx_cue": "sfx_knock"
            }
        ]
    else:
        scenes = [
            {
                "scene_index": 1,
                "title": "The Sanctuary",
                "narration": f"The story of '{title}' begins thirty floors above the asphalt. The night looked ordinary until the lights flickered.",
                "visual_description": "Stickman in mustard yellow knit beanie and grey scarf holding a mug by panoramic apartment window looking out over glowing city.",
                "camera_movement": "zoom_in",
                "sfx_cue": "sfx_swoosh"
            },
            {
                "scene_index": 2,
                "title": "The Scream of Sirens",
                "narration": "At 9:40, every phone in the district screeched in unison: Stay inside. Lock your doors. Do not help the injured.",
                "visual_description": "Stickman sitting on green sofa staring at a glowing phone with red emergency warning triangle, warm lamp light casting long shadows.",
                "camera_movement": "zoom_in",
                "sfx_cue": "sfx_alarm"
            },
            {
                "scene_index": 3,
                "title": "Street Level Chaos",
                "narration": "Thirty floors down, the intersection is packed with running crowds. Some of them aren't running away.",
                "visual_description": "Top-down birds-eye view of a four-way city crossroad at night with traffic lights and miniature stick people running across pedestrian crosswalks.",
                "camera_movement": "zoom_out",
                "sfx_cue": "sfx_swoosh"
            },
            {
                "scene_index": 4,
                "title": "The Knocking",
                "narration": "Your neighbor pounds on every apartment door in the hallway. You check the peephole and hold your breath.",
                "visual_description": "Stickman standing tense in dark hallway inside front door, listening to muffled pounding against the door.",
                "camera_movement": "pan_right",
                "sfx_cue": "sfx_knock"
            },
            {
                "scene_index": 5,
                "title": "First Problem: Water",
                "narration": "Rule one of high-rise survival: fill every container before the municipal pumps cut power.",
                "visual_description": "Stickman kneeling by white bathroom bathtub, filling it with clean water under warm bathroom mirror lights.",
                "camera_movement": "zoom_in",
                "sfx_cue": "sfx_water"
            },
            {
                "scene_index": 6,
                "title": "The Long Night",
                "narration": "The corridor falls silent. You lock the deadbolt, knowing the first night is only the beginning.",
                "visual_description": "Stickman leaning against heavy apartment door with deadbolts engaged, staring into the dark apartment room.",
                "camera_movement": "zoom_in",
                "sfx_cue": "sfx_knock"
            }
        ]

    return {
        "story_title": title,
        "genre": "Survival Suspense",
        "summary": f"Survival suspense story for {title}",
        "scenes": scenes
    }


def generate_story(
    title: str,
    api_key: Optional[str] = None,
    fallback_mode: str = "local",
    allow_local_on_gemini_fail: bool = False,
) -> Dict[str, Any]:
    """Generate storyboard scenes from title using configured mode (default: local procedural, zero API cost)."""
    data = None

    if fallback_mode == "gemini":
        key = _resolve_gemini_api_key(api_key)
        if not key:
            raise RuntimeError(
                "Gemini story fallback requested (--story-fallback gemini), but no API key configured. "
                "Set GEMINI_API_KEY in .env or choose --story-fallback local."
            )
        prompt = f"Title: {title}\nGenerate a complete storyboard following the system instructions."
        raw, err = call_gemini_api(prompt, SYSTEM_PROMPT, key)
        if raw and "scenes" in raw and len(raw["scenes"]) >= 3:
            data = raw
        elif not allow_local_on_gemini_fail:
            raise RuntimeError(
                f"Gemini story generation failed: {err}\n"
                f"Stopped to prevent unverified quota usage. Use --allow-local-fallback to permit procedural generation."
            )
        else:
            print(f"  [*] Gemini API failed ({err}). Activating local procedural story fallback.")
            data = _generate_procedural_story(title)
    elif fallback_mode == "none":
        raise RuntimeError(f"No script provided for '{title}' and fallback is disabled (--story-fallback none).")
    else:
        # Default: local procedural generation (zero Gemini API calls)
        data = _generate_procedural_story(title)

    from storyforge.story_enhancer import StoryQualityChecker, StoryCritic, ViralHookEngine
    hook_engine = ViralHookEngine()
    qc = StoryQualityChecker()
    critic = StoryCritic()

    premise = data.get("summary", f"Suspense short for {title}")
    genre = data.get("genre", "Psychological Suspense")
    raw_hook = data["scenes"][0].get("narration", "") if data.get("scenes") else ""

    # Generate 3 alternative hooks
    hook_opts = hook_engine.generate_hook_options(premise, title, genre, base_hook=raw_hook)
    rec_hook = next((h for h in hook_opts if h.is_recommended), hook_opts[0])

    # Run standard optimization
    opt_data, audit = qc.optimize_story_plan(
        title=data.get("story_title", title),
        premise=premise,
        hook=rec_hook.spoken_hook,
        scenes=data["scenes"],
        ending=data["scenes"][-1].get("narration", "") if data.get("scenes") else "",
        genre=genre,
    )

    # Run separate Critic / Reviewer pass to evaluate and improve weak scripts
    crit_data, crit_review = critic.improve_script_if_needed(
        title=data.get("story_title", title),
        premise=premise,
        hook=opt_data["opening_hook"],
        scenes=opt_data["scenes"],
        ending=opt_data["ending"],
        genre=genre,
    )

    data["scenes"] = crit_data["scenes"]
    data["opening_hook"] = crit_data["opening_hook"]
    data["ending"] = crit_data["ending"]
    data["quality_audit"] = audit.to_dict()
    data["critic_review"] = crit_review.to_dict()
    data["hook_options"] = [h.to_dict() for h in hook_opts]
    data["recommended_hook_id"] = rec_hook.id
    data["on_screen_hook_text"] = rec_hook.on_screen_text
    data["twist_pair"] = opt_data.get("twist_pair")
    return data
