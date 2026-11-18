"""Project scaffolding command (`scenecraft init`)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional


def run_init(name: str, target_dir: Optional[Path | str] = None) -> int:
    """Scaffold a fresh Scenecraft project directory."""
    project_slug = name.strip().replace(" ", "_")
    base_dir = Path(target_dir).resolve() if target_dir else Path.cwd()
    project_dir = base_dir / project_slug

    if project_dir.exists() and any(project_dir.iterdir()):
        print(f"[!] Warning: Directory '{project_dir}' already exists and is not empty.")
    
    project_dir.mkdir(parents=True, exist_ok=True)
    images_dir = project_dir / "images"
    scripts_dir = project_dir / "scripts"
    images_dir.mkdir(exist_ok=True)
    scripts_dir.mkdir(exist_ok=True)

    # 1. Starter project.json
    starter_project = {
        "title": name.replace("_", " ").title(),
        "genre": "survival_suspense",
        "aspect_ratio": "9:16",
        "opening_hook": "When the siren sounded, the station went dark.",
        "summary": f"Premise for {name.replace('_', ' ').title()}",
        "scenes": [
            {
                "scene_index": 1,
                "title": "The Awakening",
                "narration": "When the siren sounded, the station went dark.",
                "visual_description": "A survivor standing in an industrial bunker looking up as emergency lights flicker amber.",
                "camera_movement": "zoom_in",
                "sfx_cue": "sfx_alarm"
            },
            {
                "scene_index": 2,
                "title": "The Corridor",
                "narration": "You reach for the radio, listening to the static echo down the empty hall.",
                "visual_description": "Moving down a shadowy concrete corridor holding a glowing portable radio.",
                "camera_movement": "pan_left",
                "sfx_cue": "sfx_radio_static"
            },
            {
                "scene_index": 3,
                "title": "The Sealed Door",
                "narration": "You lock the heavy blast door behind you, realizing you were never alone.",
                "visual_description": "Close-up of hands turning a heavy iron door wheel as shadows loom on the reinforced glass.",
                "camera_movement": "zoom_in",
                "sfx_cue": "sfx_door_lock"
            }
        ]
    }

    proj_file = project_dir / "project.json"
    with open(proj_file, "w", encoding="utf-8") as f:
        json.dump(starter_project, f, indent=2)

    # 2. Starter script in scripts/
    script_file = scripts_dir / "story_script.txt"
    script_text = (
        f"# {starter_project['title']}\n\n"
        f"Genre: {starter_project['genre']}\n"
        f"Aspect Ratio: {starter_project['aspect_ratio']}\n\n"
        "## Scene 1: The Awakening\n"
        "Narration: When the siren sounded, the station went dark.\n"
        "Visual: A survivor standing in an industrial bunker looking up as emergency lights flicker amber.\n"
        "SFX: sfx_alarm\n\n"
        "## Scene 2: The Corridor\n"
        "Narration: You reach for the radio, listening to the static echo down the empty hall.\n"
        "Visual: Moving down a shadowy concrete corridor holding a glowing portable radio.\n"
        "SFX: sfx_radio_static\n\n"
        "## Scene 3: The Sealed Door\n"
        "Narration: You lock the heavy blast door behind you, realizing you were never alone.\n"
        "Visual: Close-up of hands turning a heavy iron door wheel as shadows loom on the reinforced glass.\n"
        "SFX: sfx_door_lock\n"
    )
    script_file.write_text(script_text, encoding="utf-8")

    # 3. Project README
    readme_file = project_dir / "README.md"
    readme_text = f"""# {starter_project['title']}

Scenecraft video project scaffolded with `scenecraft init`.

## Structure
- `project.json`: Scene-by-scene script, narration, camera movements, and SFX cues.
- `images/`: Put custom scene illustrations here (`scene_01.jpg`, `scene_02.jpg`, `scene_03.jpg`) if you provide your own.
- `scripts/`: Text/Markdown script drafts.

## Quick Production

### Option A: Render with your own images (100% offline)
Place `scene_01.jpg`, `scene_02.jpg`, `scene_03.jpg` into `images/`, then run:
```bash
scenecraft make project.json --images-dir images/
```

### Option B: Generate visuals with Google Flow
```bash
scenecraft make project.json
```
"""
    readme_file.write_text(readme_text, encoding="utf-8")

    print("\n" + "=" * 60)
    print(f"📁 SCENECRAFT PROJECT INITIALIZED: {project_dir.resolve()}")
    print("=" * 60)
    print("Files created:")
    print(f"  • {proj_file.relative_to(base_dir)}")
    print(f"  • {script_file.relative_to(base_dir)}")
    print(f"  • {images_dir.relative_to(base_dir)}/")
    print(f"  • {readme_file.relative_to(base_dir)}")
    print("-" * 60)
    print("To produce this video:")
    print(f"  cd {project_slug}")
    print("  scenecraft make project.json")
    print("=" * 60 + "\n")
    return 0
