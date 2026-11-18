"""CLI interface for Scenecraft with Story Engine, Planning, and Production modes."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import shutil
import subprocess


def open_path(path: Path | str) -> bool:
    """Open a file or URL in the default application cross-platform."""
    p_str = str(path)
    try:
        if os.name == 'nt':
            os.startfile(p_str)
            return True
        elif sys.platform == 'darwin' and shutil.which("open"):
            subprocess.run(["open", p_str], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        elif shutil.which("xdg-open"):
            subprocess.run(["xdg-open", p_str], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
    except Exception:
        pass
    return False


def cmd_script(args):
    """Manage, validate, and inspect pre-authored story scripts."""
    from scenecraft.script_handoff import validate_script, load_script, save_script, slugify
    action = getattr(args, "script_action", "list")
    workspace = Path(args.workspace or Path.cwd()).resolve()

    if action == "validate":
        target = Path(args.path)
        if not target.is_file():
            print(f"Error: Script file not found: {target}")
            sys.exit(1)
        res = validate_script(target)
        print("\n" + res.format_report() + "\n")
        if not res.valid:
            sys.exit(1)

    elif action == "list":
        scripts_dir = workspace / "scripts"
        if not scripts_dir.is_dir():
            print("\n[*] No 'scripts/' directory found in workspace.\n")
            return
        story_folders = [p for p in sorted(scripts_dir.iterdir()) if p.is_dir()]
        print("\n" + "=" * 70)
        print("📁 SCENECRAFT REGISTERED SCRIPTS & REVISIONS")
        print("=" * 70)
        total_found = 0
        for sf in story_folders:
            versions = sorted(sf.glob("v*.*"), key=lambda p: p.name)
            if not versions:
                continue
            print(f"• Story: {sf.name}")
            for v in versions:
                total_found += 1
                try:
                    res = validate_script(v)
                    status_str = "VALID" if res.valid else "INVALID"
                    print(f"    - {v.name:<10} | {res.total_scenes} scenes | {res.total_word_count:>3} words (~{res.estimated_duration_sec:>4.1f}s) | [{status_str}] | {v.resolve()}")
                except Exception as e:
                    print(f"    - {v.name:<10} | (Error: {e}) | {v.resolve()}")
        print("-" * 70)
        print(f"Total script files: {total_found}")
        print("======================================================================\n")

    elif action == "new":
        title = args.title.strip()
        slug = slugify(title)
        template_data = {
            "version": 1,
            "story_title": title,
            "genre": args.genre or "Survival Suspense",
            "aspect_ratio": getattr(args, "aspect_ratio", "9:16"),
            "style": getattr(args, "style", "earthy_explainer"),
            "summary": f"Premise for {title}",
            "opening_hook": f"When the alarm sounded, {title} began.",
            "scenes": [
                {
                    "scene_index": 1,
                    "title": "The Boundary",
                    "narration": f"When the alarm sounded, {title} began.",
                    "visual_description": "The Wanderer standing in the center of the frame under dim amber lighting.",
                    "camera_movement": "zoom_in",
                    "sfx_cue": "sfx_alarm"
                },
                {
                    "scene_index": 2,
                    "title": "The Escalation",
                    "narration": "You check the emergency broadcast as the corridor descends into total darkness.",
                    "visual_description": "The Wanderer checking glowing emergency radio in shadowy concrete corridor.",
                    "camera_movement": "pan_left",
                    "sfx_cue": "sfx_radio_static"
                },
                {
                    "scene_index": 3,
                    "title": "The Final Revelation",
                    "narration": "You lock the hatch behind you, realizing you were never alone on this floor.",
                    "visual_description": "Close up of The Wanderer's face as shadows move along the iron doorway.",
                    "camera_movement": "zoom_in",
                    "sfx_cue": "sfx_knock"
                }
            ],
            "ending": "You lock the hatch behind you, realizing you were never alone on this floor.",
            "engagement_question": "Would you open the door or climb to the roof?"
        }
        fmt = getattr(args, "format", "json")
        out_p, ver = save_script(template_data, title=title, base_dir=workspace, format=fmt)
        print(f"\n[✔] Created starter script ({fmt.upper()} v{ver}):")
        print(f"    {out_p.resolve()}")
        print("To produce this video after authoring, run:")
        print(f"    scenecraft run --script \"{out_p.resolve()}\"\n")


def cmd_produce(args):
    """Produce long-form cinematic video production with resume capability."""
    from scenecraft.pipeline_longform import LongformPipeline
    workspace = Path(args.workspace or Path.cwd()).resolve()
    pipeline = LongformPipeline(workspace_dir=workspace, video_model=getattr(args, "model", "omni-flash"))
    pipeline.produce(
        theme=args.theme or "You are trapped inside a supermarket during a zombie apocalypse",
        genre=args.genre or "zombie_apocalypse",
        duration_minutes=args.duration or 15,
        project_name=args.name,
        use_mock_video_if_flow_offline=getattr(args, "mock", False),
    )


def cmd_status(args):
    """Inspect environment, Flow Connector status, and audio licensing."""
    from scenecraft.flow_client import FlowClient
    from scenecraft.audio_manager import AudioManager
    print("\n--- Scenecraft Environment & Status ---")
    client = FlowClient()
    print(f"Flow Connector CLI installed: {'YES' if client.cli_available else 'NO'}")
    
    conn = client.check_connection()
    if conn.get("connected"):
        print("Google Flow (flow.google.com): CONNECTED via Flow Connector")
    else:
        print(f"Google Flow: NOT CONNECTED ({conn.get('reason', 'Check extension and Chrome')})")

    remaining = client.get_remaining_quota()
    print(f"Flow Daily Quota Remaining: {remaining} / {client.daily_limit} images")

    audio = AudioManager()
    print("\nVerified Audio Assets (YouTube Monetization Safe):")
    for name, item in audio.licenses.items():
        print(f"  - [{item.get('category').upper()}] {name}: {item.get('license')} ({item.get('status')})")
    print("---------------------------------------\n")


def cmd_plan(args):
    """Generate and display a high-retention Story Plan before spending any image credits."""
    from scenecraft.story_engine import StoryEngine, slugify
    workspace = Path(args.workspace or Path.cwd()).resolve()
    engine = StoryEngine(workspace)
    title = args.title or "The 30th Floor Lockdown"
    plan = engine.plan_standalone_story(concept=title, genre=args.genre)

    print("\n" + plan.format_approval_outline() + "\n")
    
    out_dir = workspace / "output" / "plans"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = Path(args.out) if args.out else (out_dir / f"{slugify(plan.title)}_plan.json")
    plan.to_json(out_file)
    print(f"[✔] Story Plan saved for approval at:\n{out_file.resolve()}")
    print("To produce this video after approval, run:")
    print(f"  scenecraft run --plan \"{out_file.resolve()}\"\n")


def cmd_adapt(args):
    """Adapt a pasted script or .txt file into a cinematic Story Plan."""
    workspace = Path(args.workspace or Path.cwd()).resolve()
    engine = StoryEngine(workspace)
    
    input_str = args.script.strip()
    plan = engine.adapt_script(
        script_input=input_str,
        mode=args.mode,
        title=args.title,
        genre=args.genre,
    )

    print("\n" + plan.format_approval_outline() + "\n")

    out_dir = workspace / "output" / "plans"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = Path(args.out) if args.out else (out_dir / f"{slugify(plan.title)}_adapted_{args.mode}.json")
    plan.to_json(out_file)
    print(f"[✔] Adapted Story Plan ({args.mode} mode) saved at:\n{out_file.resolve()}")
    print("To produce this video after approval, run:")
    print(f"  scenecraft run --plan \"{out_file.resolve()}\"\n")


def cmd_series(args):
    """Manage episodic series and persistent story bibles."""
    workspace = Path(args.workspace or Path.cwd()).resolve()
    engine = StoryEngine(workspace)
    series_sub = args.series_sub

    if series_sub == "create":
        title = args.title.strip()
        premise = args.premise.strip()
        bible = engine.create_series(title, premise=premise, genre=args.genre)
        print(f"\n[✔] Created Episodic Series Bible: '{bible.series_name}'")
        print(f"Bible Path: {bible.bible_path.resolve()}")
        print(f"Genre:      {bible.data.get('genre')}")
        print(f"Logline:    {bible.data.get('logline')}\n")

    elif series_sub == "plan":
        title = args.title.strip()
        episodes_count = args.episodes
        plans = engine.plan_series_arc(title, num_episodes=episodes_count)
        print(f"\n==================================================================")
        print(f"EPISODIC SERIES ARC: {title.upper()} ({len(plans)} Episodes)")
        print(f"==================================================================")
        out_dir = workspace / "output" / "plans"
        out_dir.mkdir(parents=True, exist_ok=True)

        for p in plans:
            print("\n" + p.format_approval_outline())
            out_file = out_dir / f"{slugify(p.title)}_plan.json"
            p.to_json(out_file)
            print(f"Saved Episode Plan: {out_file.resolve()}")
        print("\n[✔] Series Arc planned without spending image credits. Review above.\n")

    elif series_sub == "list":
        series_dir = workspace / "series"
        if not series_dir.exists():
            print("No series found.")
            return
        slugs = [p.name for p in series_dir.iterdir() if p.is_dir() and (p / "bible.json").exists()]
        print(f"\n--- Registered Episodic Series ({len(slugs)}) ---")
        for s in slugs:
            b = SeriesBible(s, base_dir=series_dir)
            ep_count = len(b.data.get("episodes", []))
            print(f"  - {b.series_name} ({b.data.get('genre')}): {ep_count} episodes recorded")
        print("--------------------------------------------------\n")

    elif series_sub == "show":
        title = args.title.strip()
        b = SeriesBible(title, base_dir=workspace / "series")
        if not b.bible_path.is_file():
            print(f"Error: Series '{title}' not found at {b.bible_path}")
            return
        print(f"\n--- Series Bible: {b.series_name} ---")
        print(json.dumps(b.data, indent=2))
        print("------------------------------------\n")


def cmd_audit(args):
    """Audit a StoryPlan or script file across all 6 quality vectors."""
    workspace = Path(args.workspace or Path.cwd()).resolve()
    engine = StoryEngine(workspace)
    target = Path(args.target)
    if target.is_file():
        content = target.read_text(encoding="utf-8")
        if target.suffix.lower() == ".json":
            try:
                data = json.loads(content)
                plan = StoryPlan.from_dict(data)
            except Exception:
                plan = engine.adapt_script(content, title=target.stem)
        else:
            plan = engine.adapt_script(content, title=target.stem)
    else:
        plan = engine.plan_standalone_story(concept=args.target)

    audit = engine.audit_story_plan(plan)
    print("\n==================================================================")
    print(f"STORY QUALITY AUDIT: {plan.title.upper()}")
    print("==================================================================")
    status_str = "PASSED" if audit.passed else "NEEDS REVIEW"
    print(f"Total Score:         {audit.total_score}/100 [{status_str}]")
    print(f"  - Hook Score:      {audit.hook_score}/20 (Speed to curiosity: {round(len(plan.opening_hook.split())/2.3, 1)}s)")
    print(f"  - Pacing Score:    {audit.pacing_score}/20 ({audit.total_word_count} words, ~{audit.estimated_duration_sec}s spoken)")
    print(f"  - Twist Score:     {audit.twist_score}/20")
    print(f"  - Emotion Score:   {audit.emotion_score}/20")
    print(f"  - Originality:     {audit.originality_score}/20")
    print("------------------------------------------------------------------")
    if audit.warnings:
        print("Warnings:")
        for w in audit.warnings:
            print(f"  ! {w}")
    if audit.suggestions:
        print("Suggestions:")
        for s in audit.suggestions:
            print(f"  * {s}")
    if not audit.warnings and not audit.suggestions:
        print("No issues detected! Story is ready for high-retention production.")
    print("==================================================================\n")


def cmd_setup(args):
    """Download LaMa ONNX, Kokoro, and Whisper models with resumable progress."""
    from scenecraft.setup_cmd import run_setup
    code = run_setup(
        whisper_model=getattr(args, "whisper_model", "base"),
        force=getattr(args, "force", False),
        tts=getattr(args, "tts", "kokoro"),
        models_only=getattr(args, "models_only", False),
        quantized=not getattr(args, "full", False),
    )
    if code != 0:
        sys.exit(code)


def cmd_voices(args):
    """List available voice options or preview synthesis across engines."""
    from scenecraft.voices_cmd import run_voices
    code = run_voices(
        engine=getattr(args, "engine", None),
        preview=getattr(args, "preview", None),
        voice=getattr(args, "voice", None),
    )
    if code != 0:
        sys.exit(code)


def cmd_demo(args):
    """Render a 10-second offline demo video using bundled fixtures."""
    from scenecraft.demo_cmd import run_demo
    code = run_demo(
        live_tts=getattr(args, "live_tts", False),
        out_dir=getattr(args, "out", None),
        quiet=getattr(args, "quiet", False),
    )
    if code != 0:
        sys.exit(code)


def cmd_init(args):
    """Scaffold a fresh Scenecraft project directory."""
    from scenecraft.init_cmd import run_init
    code = run_init(
        name=args.name,
        target_dir=getattr(args, "target_dir", None),
    )
    if code != 0:
        sys.exit(code)


def cmd_make(args):
    """Run full deterministic pipeline from project.json or script."""
    from scenecraft.pipeline import ScenecraftPipeline
    project_path = Path(args.project).resolve()
    if not project_path.is_file():
        print(f"[!] Error: Project file not found: {project_path}")
        sys.exit(1)

    pipeline = ScenecraftPipeline(
        workspace_dir=Path(args.workspace or Path.cwd()).resolve(),
        dry_run=getattr(args, "dry_run", False),
        images_dir=getattr(args, "images_dir", None),
        clean_user_images=getattr(args, "clean", False),
        force=getattr(args, "force", False),
        quiet=getattr(args, "quiet", False),
        verbose=getattr(args, "verbose", False),
    )
    res = pipeline.run_plan(project_path)
    if getattr(args, "dry_run", False):
        return
    print("\n" + "=" * 60)
    print(f"🎬 Video Production Complete: {res.get('mp4_path') or res.get('video_path')}")
    print("=" * 60)


def cmd_visuals(args):
    """Generate visual image assets from project.json scenes via Google Flow."""
    from scenecraft.story_engine import slugify
    from scenecraft.flow_client import FlowClient
    project_path = Path(args.project).resolve()
    if not project_path.is_file():
        print(f"[!] Error: Project file not found: {project_path}")
        sys.exit(1)
    with open(project_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    scenes = data.get("scenes", [])
    if not scenes:
        print("[!] No scenes found in project.json")
        sys.exit(1)

    title = data.get("story_title", data.get("title", "project"))
    slug = slugify(title)
    out_dir = Path(args.output).resolve() if getattr(args, "output", None) else Path.cwd() / "output" / slug / "images"
    out_dir.mkdir(parents=True, exist_ok=True)

    client = FlowClient()
    if not getattr(args, "dry_run", False):
        status = client.check_connection()
        if not status.get("connected"):
            print("[!] Google Flow extension is not connected.")
            print("Run with --dry-run to preview visual prompts without generating.")
            sys.exit(1)

    print(f"[*] Processing visuals for {len(scenes)} scenes to: {out_dir}")
    generated = []
    for idx, scene in enumerate(scenes, 1):
        prompt = scene.get("prompt") or scene.get("image_prompt") or scene.get("visual_prompt")
        if not prompt:
            prompt = scene.get("description") or scene.get("narration") or f"Cinematic scene {idx}"
        target_path = out_dir / f"scene_{idx:02d}.jpg"
        print(f"  [{idx}/{len(scenes)}] Prompt: {prompt[:60]}...")
        if getattr(args, "dry_run", False):
            print(f"       [DRY RUN] Would write to {target_path}")
            continue
        res = client.generate_image(prompt=prompt, output_path=target_path, scene_idx=idx)
        generated.append(res)
    print(f"[✔] Visuals generation complete ({len(generated)} images).")


def cmd_clean(args):
    """Clean visible corner watermark from images or videos."""
    from scenecraft.cleaner import clean_directory, clean_image, CleanerOptions
    in_path = Path(args.input).resolve()
    out_dir = Path(args.output).resolve()
    opts = CleanerOptions(corner=getattr(args, "corner", "bottom-right"))

    if in_path.is_dir():
        results = clean_directory(in_path, out_dir, opts=opts)
        print(f"[✔] Cleaned {len(results)} images to: {out_dir}")
    elif in_path.is_file():
        out_f = out_dir if out_dir.suffix else out_dir / in_path.name
        res = clean_image(in_path, out_f, opts=opts)
        print(f"[✔] Cleaned file saved to: {res}")
    else:
        print(f"[!] Invalid input path: {in_path}")
        sys.exit(1)


def cmd_narrate(args):
    """Synthesize narration from project.json scenes."""
    project_path = Path(args.project).resolve()
    if not project_path.is_file():
        print(f"[!] Error: Project file not found: {project_path}")
        sys.exit(1)
    with open(project_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    scenes = data.get("scenes", [])
    title = data.get("story_title", data.get("title", "narration"))
    slug = slugify(title)
    out_dir = Path.cwd() / "output" / slug / "audio"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = Path(args.out).resolve() if getattr(args, "out", None) else out_dir / "narration.wav"

    text = " ".join(s.get("narration", "") for s in scenes)
    from scenecraft.tts import get_tts_engine
    tts = get_tts_engine(getattr(args, "engine", None))
    dur = tts.generate(text, out_file)
    print(f"[✔] Narration generated ({dur:.1f}s): {out_file}")


def cmd_subtitles(args):
    """Generate word-synced ASS subtitles from audio and project.json."""
    from scenecraft.narration import generate_synchronized_subtitles
    project_path = Path(args.project).resolve()
    if not project_path.is_file():
        print(f"[!] Error: Project file not found: {project_path}")
        sys.exit(1)
    with open(project_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    scenes = data.get("scenes", [])
    audio_path = Path(args.audio).resolve() if getattr(args, "audio", None) else None
    if not audio_path or not audio_path.is_file():
        title = data.get("story_title", data.get("title", "narration"))
        audio_path = Path.cwd() / "output" / slugify(title) / "audio" / "narration.wav"

    if not audio_path.is_file():
        print(f"[!] Audio file missing for subtitle extraction: {audio_path}")
        sys.exit(1)

    out_ass = Path(args.out).resolve() if getattr(args, "out", None) else audio_path.parent.parent / "subtitles" / "subtitles.ass"
    out_ass.parent.mkdir(parents=True, exist_ok=True)
    res_ass = generate_synchronized_subtitles(scenes, audio_path, out_ass)
    print(f"[✔] Subtitles generated: {res_ass}")


def cmd_validate(args):
    """Validate video stream integrity and audio/video specs."""
    vid_p = Path(args.video).resolve()
    if not vid_p.is_file():
        print(f"[!] Error: File not found: {vid_p}")
        sys.exit(1)

    print(f"[*] Validating video stream integrity: {vid_p.name}...")
    res = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(vid_p), "-f", "null", "-"],
        capture_output=True,
        text=True,
    )
    if res.returncode != 0 or res.stderr.strip():
        print(f"[✘] Stream corruption detected:\n{res.stderr.strip()}")
        sys.exit(1)
    print("[✔] Stream decode verified (zero bitstream corruption).")


def cmd_doctor(args):
    """Run comprehensive system diagnostics and pre-flight checks."""
    if getattr(args, "report", False):
        from scenecraft.report import generate_markdown_report
        workspace = Path(args.workspace) if getattr(args, "workspace", None) else None
        print(generate_markdown_report(workspace_root=workspace))
        return
    from scenecraft.doctor import SystemDoctor
    doc = SystemDoctor()
    print("\n" + doc.format_report() + "\n")
    if any(c.status == "FAIL" for c in doc.run_all_checks()):
        sys.exit(1)


def cmd_report(args):
    """Generate and print a sanitized Markdown diagnostic report for GitHub issues."""
    from scenecraft.report import generate_markdown_report
    workspace = Path(args.workspace) if getattr(args, "workspace", None) else None
    print(generate_markdown_report(workspace_root=workspace))


def cmd_storage(args):
    """Manage workspace storage, perform audits, and move unused assets to trash upon confirmation."""
    from scenecraft.storage_manager import StorageManager
    sm = StorageManager()
    action = getattr(args, "storage_action", "audit")
    days = getattr(args, "days", None)

    if action == "audit":
        rep = sm.audit_storage(older_than_days=days)
        print("\n" + rep.format_table() + "\n")
    elif action == "clean":
        rep = sm.audit_storage(older_than_days=days)
        if not rep.candidates:
            print("\n[*] No unused or orphaned candidates found. Storage is clean!\n")
            return
        print("\n" + rep.format_table() + "\n")
        if getattr(args, "yes", False):
            confirm = "yes"
        else:
            try:
                confirm = input("Move these approved files to recoverable .trash/? (yes/no): ").strip().lower()
            except EOFError:
                confirm = "no"
        if confirm in ["yes", "y"]:
            manifest = sm.move_to_trash(rep.candidates)
            print(f"[✔] Safely moved {len(rep.candidates)} files to .trash/. Manifest: {manifest.name}\n")
        else:
            print("[*] Storage clean cancelled. No files were modified.\n")
    elif action == "restore":
        manifest_path = getattr(args, "manifest", None)
        if not manifest_path:
            trash_batches = sorted(sm.trash_dir.glob("*/manifest.json"), key=lambda p: p.stat().st_mtime, reverse=True)
            if not trash_batches:
                print("[!] No trash manifests found to restore.")
                return
            manifest_path = trash_batches[0]
        sm.restore_from_trash(Path(manifest_path))


def cmd_auto(args):
    """Auto-Story mode: generates original story and produces finished video."""
    from scenecraft.pipeline import ScenecraftPipeline
    workspace = Path(args.workspace or Path.cwd()).resolve()
    pipeline = ScenecraftPipeline(
        workspace_dir=workspace,
        voice=args.voice,
        rate=args.rate,
        pitch=args.pitch,
        style=getattr(args, "style", "dark_cinematic"),
        voice_option=getattr(args, "voice_option", None),
        auto_approve=getattr(args, "auto_approve", False),
        story_fallback=getattr(args, "story_fallback", "local"),
        allow_local_on_gemini_fail=getattr(args, "allow_local_fallback", False),
    )
    try:
        result = pipeline.run_auto(genre=args.genre)
        print(f"\n[AUTO-STORY FINISHED]")
        print(f"Title: {result['title']}")
        print(f"Genre: {result['genre']}")
        print(f"Summary: {result['summary']}")
        print(f"Video Path: {result['mp4_path'].resolve()}")
        print(f"Bundle Directory: {result['bundle_dir'].resolve()}")
    except Exception as e:
        print(f"\nAuto-Story Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def cmd_run(args):
    """Generate finished short or horizontal film from story script, plan, or title."""
    from scenecraft.pipeline import ScenecraftPipeline
    workspace = Path(args.workspace or Path.cwd()).resolve()
    pipeline = ScenecraftPipeline(
        workspace_dir=workspace,
        voice=args.voice,
        rate=args.rate,
        pitch=args.pitch,
        style=getattr(args, "style", "dark_cinematic"),
        voice_option=getattr(args, "voice_option", None),
        auto_approve=getattr(args, "auto_approve", False),
        story_fallback=getattr(args, "story_fallback", "local"),
        allow_local_on_gemini_fail=getattr(args, "allow_local_fallback", False),
        flow_video=getattr(args, "flow_video", False),
        flow_video_model=getattr(args, "model", "omni-flash"),
        dry_run=getattr(args, "dry_run", False),
    )
    aspect_ratio = getattr(args, "aspect_ratio", "9:16")
    try:
        if getattr(args, "script", None):
            result = pipeline.run_script(args.script, aspect_ratio=aspect_ratio)
        elif args.plan:
            result = pipeline.run_plan(args.plan, aspect_ratio=aspect_ratio)
        else:
            title = (args.title or "").strip()
            if not title:
                print("Error: Please provide a story title, use --script <script.json/.md>, or use --plan <plan.json>")
                sys.exit(1)
            result = pipeline.run(title, aspect_ratio=aspect_ratio)

        print(f"\nSuccess! Output ready at:\n{result['mp4_path'].resolve()}")
        print(f"Bundle Directory: {result['bundle_dir'].resolve()}")
    except Exception as e:
        print(f"\nPipeline Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def cmd_flow_video(args):
    """Orchestrate Google Flow scene video generation with character continuity."""
    from scenecraft.flow_agent import FlowAgentDirector
    from scenecraft.script_handoff import load_script, validate_script

    workspace = Path(args.workspace or Path.cwd()).resolve()
    script_p = Path(args.script).resolve()
    if not script_p.is_file():
        print(f"Error: Script file not found: {script_p}")
        sys.exit(1)

    val = validate_script(script_p)
    if not val.valid:
        print("\n" + val.format_report() + "\n")
        print("Error: Script validation failed. Video generation halted.")
        sys.exit(1)

    story_data = load_script(script_p)
    story_title = story_data.get("story_title", script_p.stem)
    aspect_ratio = getattr(args, "aspect_ratio", story_data.get("aspect_ratio", "16:9"))
    model = getattr(args, "model", "omni-flash")
    dry_run = getattr(args, "dry_run", False)
    auto_approve = getattr(args, "auto_approve", False)

    chars = story_data.get("characters", [])
    char_name = getattr(args, "character", None) or (chars[0].get("name", "The Wanderer") if chars else "The Wanderer")
    ref_img = Path(args.reference_image).resolve() if getattr(args, "reference_image", None) else None

    safe_title = sanitize_filename(story_title)
    bundle_dir = workspace / "output" / f"flow_video_{safe_title}"
    bundle_dir.mkdir(parents=True, exist_ok=True)

    director = FlowAgentDirector(workspace_dir=workspace)
    scenes = story_data.get("scenes", [])

    print(f"\n============================================================")
    print(f"🎬 SCENECRAFT FLOW VIDEO PRODUCTION: '{story_title}'")
    print(f"============================================================")

    updated_scenes = director.generate_scenes(
        scenes=scenes,
        output_dir=bundle_dir,
        story_title=story_title,
        character_name=char_name,
        reference_image=ref_img,
        aspect_ratio=aspect_ratio,
        model=model,
        auto_approve=auto_approve,
        dry_run=dry_run,
    )

    if getattr(args, "assemble", False):
        print("\n[*] Assembling final MP4 from Flow video clips via Scenecraft Pipeline...")
        pipeline = ScenecraftPipeline(
            workspace_dir=workspace,
            auto_approve=True,
            flow_video=True,
            flow_video_model=model,
            dry_run=dry_run,
        )
        res = pipeline.run_script(script_p, aspect_ratio=aspect_ratio)
        print(f"\n[✔] Assembly complete! Final video: {res['mp4_path'].resolve()}")


def cmd_thumbnail(args):
    """Generate or regenerate a dedicated AI thumbnail via Google Flow."""
    from scenecraft.thumbnail_generator import ThumbnailGenerator
    from scenecraft.script_handoff import load_script

    workspace = Path(args.workspace or Path.cwd()).resolve()
    thumb_gen = ThumbnailGenerator(workspace_dir=workspace)

    dry_run = getattr(args, "dry_run", False)
    aspect_ratio = getattr(args, "aspect_ratio", "16:9")
    style = getattr(args, "style", "earthy_explainer")
    custom_prompt = getattr(args, "prompt", None)

    target_dir = None
    story_data = None

    if getattr(args, "bundle", None):
        target_dir = Path(args.bundle).resolve()
        script_file = target_dir / "story_script.json"
        if script_file.is_file():
            with open(script_file, "r", encoding="utf-8") as f:
                story_data = json.load(f)
    elif getattr(args, "script", None):
        script_p = Path(args.script).resolve()
        if not script_p.is_file():
            print(f"Error: Script not found: {script_p}")
            sys.exit(1)
        story_data = load_script(script_p)
        safe_title = sanitize_filename(story_data.get("story_title", script_p.stem))
        target_dir = workspace / "output" / f"thumbnail_{safe_title}"
        target_dir.mkdir(parents=True, exist_ok=True)
    else:
        out_root = workspace / "output"
        if out_root.is_dir():
            runs = sorted([p for p in out_root.iterdir() if p.is_dir() and not p.name.startswith(".")], key=lambda p: p.stat().st_mtime)
            if runs:
                target_dir = runs[-1]
                script_file = target_dir / "story_script.json"
                if script_file.is_file():
                    with open(script_file, "r", encoding="utf-8") as f:
                        story_data = json.load(f)
        if not target_dir or not story_data:
            print("Error: Please provide --script <path> or --bundle <dir>.")
            sys.exit(1)

    print(f"\n============================================================")
    print(f"🎨 SCENECRAFT GOOGLE FLOW AI THUMBNAIL GENERATOR")
    print(f"============================================================")
    print(f"Target Directory: {target_dir.resolve()}")
    print(f"Aspect Ratio:     {aspect_ratio}")
    print(f"Art Style Preset: {style}")
    if custom_prompt:
        print(f"Custom/Revised:   {custom_prompt}")

    if custom_prompt:
        res = thumb_gen.regenerate_thumbnail(
            output_dir=target_dir,
            revised_prompt=custom_prompt,
            story_data=story_data,
            aspect_ratio=aspect_ratio,
            style_preset=style,
            dry_run=dry_run,
        )
    else:
        res = thumb_gen.generate_flow_ai_thumbnail(
            story_data=story_data,
            output_dir=target_dir,
            aspect_ratio=aspect_ratio,
            style_preset=style,
            dry_run=dry_run,
        )

    print(f"\n[✔] Flow AI Thumbnail Ready:")
    print(f"    PNG (Master): {res['png'].resolve()}")
    print(f"    JPG:          {res['jpg'].resolve()}\n")


def cmd_test_flow(args):
    """Generate exactly 3 test images from Google Flow for a story title, without video render."""
    from scenecraft.flow_client import FlowClient
    from scenecraft.story_gen import generate_story
    from scenecraft.prompt_builder import build_prompts_from_scenes
    title = (args.title or "The 30th Floor").strip()
    print(f"\n==========================================")
    print(f"[*] Testing Google Flow Image Generation: '{title}'")
    print(f"==========================================")

    client = FlowClient()
    status = client.check_connection()
    if not status.get("connected"):
        print("\n[!] Google Flow is NOT connected!")
        print(status.get("raw") or status.get("reason"))
        sys.exit(1)

    print(f"[✔] Flow Connector is CONNECTED!")
    print(f"[*] Remaining daily quota: {client.get_remaining_quota()} images")

    story_data = generate_story(title)
    raw_scenes = story_data.get("scenes", [])[:3]
    scene_prompts = build_prompts_from_scenes(raw_scenes)

    out_dir = Path(__file__).resolve().parent.parent / "generated_images"
    out_dir.mkdir(parents=True, exist_ok=True)

    generated_files = []
    reference_char_img = None

    for sp in scene_prompts:
        print(f"\n--- Scene {sp.scene_index}: {sp.title} ---")
        prompt_text = sp.full_prompt()
        print(f"Prompt:\n{prompt_text}\n")

        target_file = out_dir / f"test_scene_{sp.scene_index:02d}.jpg"
        img = client.generate_image(
            prompt=prompt_text,
            output_path=target_file,
            scene_idx=sp.scene_index,
            reference_image=reference_char_img,
            folder_name="scenecraft_test",
        )
        generated_files.append(img)
        if sp.scene_index == 1:
            reference_char_img = img

    print("\n==========================================")
    print("[✔] 3 Flow Test Images Successfully Generated!")
    print(f"Saved in directory: {out_dir.resolve()}")
    for f in generated_files:
        print(f"  - {f.resolve()}")
    print("==========================================\n")


def cmd_flow_agent(args):
    """Generate comprehensive Flow Agent Master Prompt and 25-45 visual image beats for 1-3 min Reels."""
    from scenecraft.flow_agent import FlowAgentDirector, UNIVERSE_WANDERER, UNIVERSE_EXPERIMENTAL
    from scenecraft.script_handoff import load_script, validate_script
    from scenecraft.story_gen import generate_story, generate_auto_story
    from scenecraft.thumbnail_generator import ThumbnailGenerator

    workspace = Path(args.workspace or Path.cwd()).resolve()
    director = FlowAgentDirector(workspace_dir=workspace)
    thumb_gen = ThumbnailGenerator(workspace_dir=workspace)

    # 1. Resolve Story Input
    story_data = None
    if getattr(args, "script", None):
        script_p = Path(args.script).resolve()
        if not script_p.is_file():
            print(f"Error: Script file not found: {script_p}")
            sys.exit(1)
        val = validate_script(script_p)
        if not val.valid:
            print("\n" + val.format_report() + "\n")
            print("Error: Script validation failed.")
            sys.exit(1)
        story_data = load_script(script_p)
    elif getattr(args, "title", None):
        story_data = generate_story(args.title, fallback_mode="local")
    elif getattr(args, "auto", False):
        story_data = generate_auto_story(fallback_mode="local")
    else:
        print("Error: Please provide --script <path>, --title <string>, or --auto.")
        sys.exit(1)

    story_title = story_data.get("story_title") or story_data.get("title", "Story Project")
    safe_title = sanitize_filename(story_title)
    aspect_ratio = getattr(args, "aspect_ratio", "9:16")
    universe = getattr(args, "universe", UNIVERSE_WANDERER)
    style = getattr(args, "style", "dark_cinematic")
    exact_beats = getattr(args, "beats", None)
    if exact_beats:
        beats_min = beats_max = exact_beats
    else:
        beats_min = getattr(args, "beats_min", 25)
        beats_max = getattr(args, "beats_max", 45)
    batch_size = getattr(args, "batch_size", 10)

    char_spec = None
    if getattr(args, "character", None) or getattr(args, "character_desc", None) or getattr(args, "reference_image", None):
        char_spec = {
            "name": getattr(args, "character", "The Wanderer"),
            "description": getattr(args, "character_desc", None),
            "reference_image": Path(args.reference_image).resolve() if getattr(args, "reference_image", None) else None,
        }

    bundle_dir = Path(args.bundle).resolve() if getattr(args, "bundle", None) else workspace / "output" / f"flow_agent_{safe_title}"
    bundle_dir.mkdir(parents=True, exist_ok=True)

    print("\n" + "=" * 78)
    print(f"🎬 SCENECRAFT FLOW AGENT STORYBOARD DIRECTOR: '{story_title}'")
    print("=" * 78)
    print(f"Aspect Ratio:        {aspect_ratio} ({'1080x1920 Vertical Mobile Safe-Zone' if aspect_ratio == '9:16' else '1920x1080 Landscape'})")
    print(f"Creative Universe:   {universe.upper()}")
    print(f"Visual Beat Target:  {beats_min} to {beats_max} image beats (1-3 min Reel pacing)")
    print(f"Style Preset:        {style}")
    print(f"Output Directory:    {bundle_dir.resolve()}")
    print("-" * 78)

    # 2. Decompose into 25-45 visual image beats
    visual_beats = director.decompose_script_to_visual_beats(
        script_data=story_data,
        target_beats_range=(beats_min, beats_max),
        aspect_ratio=aspect_ratio,
        universe=universe,
        character_spec=char_spec,
    )
    print(f"[✔] Successfully broken down script into {len(visual_beats)} narrative visual beats.")

    # 3. Generate Flow Agent Master Prompt
    master_prompt, visual_beats = director.generate_master_agent_prompt(
        story_data=story_data,
        visual_beats=visual_beats,
        universe=universe,
        style_preset=style,
        aspect_ratio=aspect_ratio,
        character_spec=char_spec,
        target_beats_range=(beats_min, beats_max),
    )

    # 4. Generate Thumbnail Prompt
    thumb_analysis = thumb_gen.analyze_story_for_thumbnail(story_data)
    thumb_prompt = thumb_gen.build_thumbnail_prompt(thumb_analysis, aspect_ratio=aspect_ratio, style_preset=style)
    thumb_prompt_file = bundle_dir / "thumbnail_prompt.txt"
    thumb_prompt_file.write_text(
        f"=== SCENECRAFT FLOW AI THUMBNAIL PROMPT ===\n"
        f"Title:        {thumb_analysis['title']}\n"
        f"Visual Hook:  {thumb_analysis['visual_hook']}\n"
        f"Aspect Ratio: {aspect_ratio}\n"
        f"Prompt:\n{thumb_prompt}\n",
        encoding="utf-8"
    )

    # 5. Save all bundle files
    saved = director.save_master_prompt_bundle(
        output_dir=bundle_dir,
        story_data=story_data,
        visual_beats=visual_beats,
        master_prompt=master_prompt,
        aspect_ratio=aspect_ratio,
        style_preset=style,
        batch_size=batch_size,
    )

    with open(bundle_dir / "story_script.json", "w", encoding="utf-8") as f:
        json.dump(story_data, f, indent=2, default=str)

    print("\n" + "=" * 78)
    print("📋 FLOW AGENT MASTER PROMPT PREVIEW (COPY & PASTE INTO GOOGLE FLOW AGENT):")
    print("=" * 78)
    print(master_prompt)
    print("=" * 78)
    print("\n[✔] Master Prompt and Production Plan saved to:")
    print(f"    - Plain Text: {saved['prompt_txt'].resolve()}")
    print(f"    - Markdown:   {saved['prompt_md'].resolve()}")
    print(f"    - Storyboard: {saved['beats_json'].resolve()}")
    print(f"    - Thumbnail:  {thumb_prompt_file.resolve()}")
    print(f"    - Guide:      {saved['guide_txt'].resolve()}")
    print("\n[*] NEXT STEPS (Honest User Action Required):")
    print("    1. Paste the master prompt above into Google Flow Agent to generate the visual beats.")
    print(f"    2. Once generated, place images in '{bundle_dir / 'images'}' or run:")
    print(f"       python3 -m scenecraft.cli ingest-assets --bundle '{bundle_dir}' --source <download_folder>")
    print(f"    3. Render final Reel & auto thumbnail:")
    print(f"       python3 -m scenecraft.cli assemble --bundle '{bundle_dir}'\n")


def cmd_ingest_assets(args):
    """Retrieve and organize Flow Agent generated images into the project bundle."""
    from scenecraft.flow_agent import FlowAgentDirector

    workspace = Path(args.workspace or Path.cwd()).resolve()
    bundle_dir = Path(args.bundle).resolve()
    source_dir = Path(args.source).resolve()
    aspect_ratio = getattr(args, "aspect_ratio", "9:16")

    if not bundle_dir.is_dir():
        print(f"Error: Bundle directory not found: {bundle_dir}")
        sys.exit(1)
    if not source_dir.exists():
        print(f"Error: Source image directory or zip not found: {source_dir}")
        sys.exit(1)

    director = FlowAgentDirector(workspace_dir=workspace)
    ingested = director.ingest_agent_assets(
        source_path=source_dir,
        output_dir=bundle_dir,
        aspect_ratio=aspect_ratio,
    )
    print(f"[✔] Successfully ingested {len(ingested)} images into {bundle_dir / 'images'}")


def cmd_assemble(args):
    """Assemble final 1-3 min vertical Reel from ingested Flow Agent assets."""
    workspace = Path(args.workspace or Path.cwd()).resolve()
    bundle_dir = Path(args.bundle).resolve()

    if not bundle_dir.is_dir():
        print(f"Error: Bundle directory not found: {bundle_dir}")
        sys.exit(1)

    script_file = bundle_dir / "story_script.json"
    beats_file = bundle_dir / "storyboard_beats.json"

    if not script_file.is_file() and not beats_file.is_file():
        print(f"Error: No story_script.json or storyboard_beats.json found in {bundle_dir}")
        sys.exit(1)

    story_data = {}
    if script_file.is_file():
        with open(script_file, "r", encoding="utf-8") as f:
            story_data = json.load(f)
    elif beats_file.is_file():
        with open(beats_file, "r", encoding="utf-8") as f:
            b_data = json.load(f)
            story_data = {
                "story_title": b_data.get("title", bundle_dir.name),
                "aspect_ratio": b_data.get("aspect_ratio", "9:16"),
                "scenes": [],
            }

    aspect_ratio = getattr(args, "aspect_ratio", story_data.get("aspect_ratio", "9:16"))
    dry_run = getattr(args, "dry_run", False)
    auto_approve = getattr(args, "auto_approve", True)

    pipeline = ScenecraftPipeline(
        workspace_dir=workspace,
        auto_approve=auto_approve,
        dry_run=dry_run,
    )
    result = pipeline._execute_pipeline(
        story_title=story_data.get("story_title", bundle_dir.name),
        story_data=story_data,
        bundle_dir=bundle_dir,
    )
    print(f"\n[✔] Assembly complete! Output video: {result['mp4_path'].resolve()}")


def cmd_settings(args):
    """Inspect or update Scenecraft configuration settings."""
    from scenecraft.settings import load_settings, set_setting, set_auto_thumbnail_enabled

    workspace = Path(args.workspace or Path.cwd()).resolve()
    if getattr(args, "enable_auto_thumbnail", False):
        set_auto_thumbnail_enabled(True, workspace_dir=workspace)
        print("[✔] Automatic Flow AI thumbnail generation ENABLED.")
    elif getattr(args, "disable_auto_thumbnail", False):
        set_auto_thumbnail_enabled(False, workspace_dir=workspace)
        print("[✔] Automatic Flow AI thumbnail generation DISABLED.")

    if getattr(args, "set", None):
        for item in args.set:
            if "=" in item:
                k, v = item.split("=", 1)
                if v.lower() == "true":
                    val = True
                elif v.lower() == "false":
                    val = False
                elif v.isdigit():
                    val = int(v)
                else:
                    val = v
                set_setting(k.strip(), val, workspace_dir=workspace)
                print(f"[✔] Setting updated: {k.strip()} = {val}")

    cur = load_settings(workspace_dir=workspace)
    print("\n=== SCENECRAFT SETTINGS ===")
    for k, v in cur.items():
        print(f"  {k}: {v}")
    print("===========================\n")


def cmd_caption(args):
    """Preview, edit, or copy ready-to-post social media captions for YouTube Shorts and Instagram Reels."""
    base_dir = Path(__file__).resolve().parent.parent
    workspace = Path(args.workspace).resolve() if args.workspace else base_dir
    output_dir = workspace / "output"

    target_bundle = None
    if args.target:
        p = Path(args.target)
        if p.is_dir() and (p / "story_script.json").exists():
            target_bundle = p
        elif (output_dir / args.target).is_dir():
            target_bundle = output_dir / args.target
        else:
            # Match by glob pattern
            matches = list(output_dir.glob(f"*{args.target}*"))
            bundle_matches = [m for m in matches if m.is_dir() and ((m / "story_script.json").exists() or (m / "social_caption.json").exists())]
            if bundle_matches:
                target_bundle = sorted(bundle_matches, key=lambda x: x.stat().st_mtime, reverse=True)[0]

    if not target_bundle:
        # Find latest completed bundle
        candidates = [p for p in output_dir.iterdir() if p.is_dir() and ((p / "story_script.json").exists() or (p / "social_caption.json").exists())]
        if candidates:
            target_bundle = sorted(candidates, key=lambda x: x.stat().st_mtime, reverse=True)[0]

    if not target_bundle or not target_bundle.exists():
        print("Error: No story video bundle found. Generate a video first or specify bundle path.")
        sys.exit(1)

    caption_json_path = target_bundle / "social_caption.json"
    caption_txt_path = target_bundle / "social_caption.txt"
    caption_html_path = target_bundle / "caption_card.html"

    from scenecraft.caption_generator import CaptionGenerator, SocialCaption, copy_to_clipboard
    caption_gen = CaptionGenerator(workspace)

    # Load or generate caption
    caption_obj = None
    if caption_json_path.exists() and not args.regenerate:
        try:
            with open(caption_json_path, "r", encoding="utf-8") as f:
                cdata = json.load(f)
            caption_obj = SocialCaption(
                title=cdata.get("title", target_bundle.name),
                header=cdata.get("header", ""),
                description=cdata.get("description", ""),
                episode_info=cdata.get("episode_info"),
                engagement_question=cdata.get("engagement_question", ""),
                hashtags=cdata.get("hashtags", []),
                platform=args.platform,
                genre=cdata.get("genre", "Suspense"),
            )
        except Exception:
            pass

    if not caption_obj:
        # Generate from story_script.json or story_summary.txt
        script_file = target_bundle / "story_script.json"
        if script_file.exists():
            with open(script_file, "r", encoding="utf-8") as f:
                sdata = json.load(f)
        else:
            sdata = {"title": target_bundle.name, "genre": "Suspense", "summary": ""}
        caption_obj = caption_gen.generate_caption(sdata, platform=args.platform)
        caption_gen.save_caption_bundle(caption_obj, target_bundle)

    current_platform = args.platform

    # If --browser requested, open HTML widget immediately
    if args.browser:
        if open_path(caption_html_path):
            print(f"[✔] Opened Interactive Caption Card in browser: {caption_html_path}")
            return
        else:
            print(f"HTML Widget: file://{caption_html_path.resolve()}")

    # If --edit requested
    if args.edit:
        editor = os.environ.get("EDITOR", "nano" if shutil.which("nano") else None)
        if editor:
            subprocess.run([editor, str(caption_txt_path)])
            print(f"[✔] Saved edits to {caption_txt_path}")
            return
        else:
            print("\nEnter new suspenseful description (leave empty to keep current):")
            new_desc = input("> ").strip()
            if new_desc:
                caption_obj.description = new_desc
                caption_gen.save_caption_bundle(caption_obj, target_bundle)
                print("[✔] Caption updated and saved.")

    # If --copy requested, copy to clipboard and exit
    if args.copy:
        text_to_copy = caption_obj.format_text(current_platform)
        ok = copy_to_clipboard(text_to_copy)
        if ok:
            print(f"[✔] Copied {current_platform.replace('_', ' ').title()} caption to clipboard!")
        else:
            print("Note: Could not access clipboard directly. Copied text is below:\n")
            print(text_to_copy)
        return

    # Interactive display & menu
    def display_preview(plat: str):
        text = caption_obj.format_text(plat)
        plat_label = "YouTube Shorts" if "youtube" in plat else "Instagram Reels"
        words = len(text.split())
        chars = len(text)
        print("\n" + "=" * 65)
        print(f"  READY-TO-POST SOCIAL MEDIA CAPTION [{plat_label.upper()}]")
        print("=" * 65)
        print(text)
        print("-" * 65)
        print(f"Stats: {chars} chars | {words} words | Target: {target_bundle.name}")
        print(f"Files: {caption_txt_path.name} & {caption_html_path.name}")
        print("=" * 65)

    display_preview(current_platform)

    # Interactive prompt if running in interactive terminal
    if sys.stdin.isatty():
        while True:
            prompt = "\n[c] Copy to Clipboard | [e] Edit | [t] Toggle Platform | [o] Open Web UI | [q] Done: "
            try:
                choice = input(prompt).strip().lower()
            except (EOFError, KeyboardInterrupt):
                print()
                break

            if choice == "c":
                text = caption_obj.format_text(current_platform)
                ok = copy_to_clipboard(text)
                if ok:
                    print(f"  [✔] Copied {current_platform.replace('_', ' ').title()} caption to clipboard!")
                else:
                    print("  [!] Clipboard command failed. Please copy text from above.")
            elif choice == "t":
                current_platform = "instagram_reels" if "youtube" in current_platform else "youtube_shorts"
                caption_obj.platform = current_platform
                display_preview(current_platform)
            elif choice == "e":
                print("Enter new description (2-3 short, engaging sentences):")
                try:
                    new_desc = input("> ").strip()
                    if new_desc:
                        caption_obj.description = new_desc
                        caption_gen.save_caption_bundle(caption_obj, target_bundle)
                        print("  [✔] Saved updated caption!")
                        display_preview(current_platform)
                except (EOFError, KeyboardInterrupt):
                    pass
            elif choice == "o":
                if open_path(caption_html_path):
                    print(f"  [✔] Opened in browser: {caption_html_path.name}")
                else:
                    print(f"  Card URL: file://{caption_html_path.resolve()}")
            elif choice in ("q", ""):
                break


def main():
    parser = argparse.ArgumentParser(
        prog="scenecraft",
        description="Scenecraft: Story Engine and automated video production for vertical YouTube Shorts.",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # 'plan' subcommand (Feature 2 & 5)
    plan_parser = subparsers.add_parser("plan", help="Create a Story Plan for user approval without generating images")
    plan_parser.add_argument("title", type=str, nargs="?", default="The 30th Floor Lockdown", help="Story title or concept")
    plan_parser.add_argument("--genre", "-g", type=str, default="Psychological Suspense", help="Story genre")
    plan_parser.add_argument("--out", "-o", type=str, default=None, help="Save plan JSON path")
    plan_parser.add_argument("--workspace", "-w", type=str, default=None, help="Workspace directory")
    plan_parser.set_defaults(func=cmd_plan)

    # 'adapt' subcommand (Feature 1B)
    adapt_parser = subparsers.add_parser("adapt", help="Adapt a script text or .txt file into a Story Plan")
    adapt_parser.add_argument("script", type=str, help="Script text or path to .txt file")
    adapt_parser.add_argument("--mode", "-m", choices=["faithful", "creative"], default="faithful", help="faithful: preserve dialogue/plot; creative: tighten hook/twist")
    adapt_parser.add_argument("--title", "-t", type=str, default=None, help="Story title")
    adapt_parser.add_argument("--genre", "-g", type=str, default="Suspense", help="Story genre")
    adapt_parser.add_argument("--out", "-o", type=str, default=None, help="Save plan JSON path")
    adapt_parser.add_argument("--workspace", "-w", type=str, default=None, help="Workspace directory")
    adapt_parser.set_defaults(func=cmd_adapt)

    # 'series' subcommand (Feature 3)
    series_parser = subparsers.add_parser("series", help="Manage episodic series and persistent story bibles")
    series_sub = series_parser.add_subparsers(dest="series_sub", help="Series actions: create, plan, list, show")

    s_create = series_sub.add_parser("create", help="Create a new episodic series bible")
    s_create.add_argument("title", type=str, help="Series title")
    s_create.add_argument("--premise", "-p", type=str, required=True, help="Overarching premise / logline")
    s_create.add_argument("--genre", "-g", type=str, default="Psychological Suspense", help="Series genre")
    s_create.add_argument("--workspace", "-w", type=str, default=None)

    s_plan = series_sub.add_parser("plan", help="Plan a multi-episode series arc with Episode 3 turning point")
    s_plan.add_argument("title", type=str, help="Series title")
    s_plan.add_argument("--episodes", "-n", type=int, default=3, help="Number of episodes to plan (default: 3)")
    s_plan.add_argument("--workspace", "-w", type=str, default=None)

    s_list = series_sub.add_parser("list", help="List all registered episodic series")
    s_list.add_argument("--workspace", "-w", type=str, default=None)

    s_show = series_sub.add_parser("show", help="Show persistent story bible for a series")
    s_show.add_argument("title", type=str, help="Series title")
    s_show.add_argument("--workspace", "-w", type=str, default=None)

    series_parser.set_defaults(func=cmd_series)

    # 'script' subcommand (Story Authoring & Handoff)
    script_parser = subparsers.add_parser("script", help="Author, validate, and inspect pre-authored story scripts")
    script_sub = script_parser.add_subparsers(dest="script_action", help="Script action: validate, list, new")

    sc_val = script_sub.add_parser("validate", help="Validate a script file before production")
    sc_val.add_argument("path", type=str, help="Path to script file (.json, .md, or .txt)")
    sc_val.add_argument("--workspace", "-w", type=str, default=None)

    sc_list = script_sub.add_parser("list", help="List all registered script versions in workspace")
    sc_list.add_argument("--workspace", "-w", type=str, default=None)

    sc_new = script_sub.add_parser("new", help="Create a new starter script with revision tracking")
    sc_new.add_argument("title", type=str, help="Story title")
    sc_new.add_argument("--genre", "-g", type=str, default="Survival Suspense", help="Story genre")
    sc_new.add_argument("--style", "-s", type=str, default="earthy_explainer", help="Art style preset")
    sc_new.add_argument("--aspect-ratio", "-a", choices=["9:16", "16:9"], default="9:16", help="Aspect ratio")
    sc_new.add_argument("--format", "-f", choices=["json", "md"], default="json", help="File format")
    sc_new.add_argument("--workspace", "-w", type=str, default=None)

    script_parser.set_defaults(func=cmd_script)

    # 'auto' subcommand
    auto_parser = subparsers.add_parser("auto", help="Auto-Story mode: generates an original short story and finished MP4")
    auto_parser.add_argument("--genre", "-g", type=str, default=None, help="Story genre")
    auto_parser.add_argument("--workspace", "-w", type=str, default=None, help="Workspace directory")
    auto_parser.add_argument("--voice", "-v", type=str, default="en-US-AndrewMultilingualNeural", help="Narrator voice (Edge-TTS, Kokoro, ElevenLabs, or voicestudio:<profile>)")
    auto_parser.add_argument("--voice-option", choices=["A", "B", "C", "a", "b", "c"], default="A", help="Select auditioned voice option (A: Natural [Permanent Narrator — Recommended], B: Suspenseful, C: Serious)")
    auto_parser.add_argument("--style", "-s", type=str, choices=["dark_cinematic", "survival_explainer", "earthy_explainer"], default="dark_cinematic", help="Visual art style preset (dark_cinematic, earthy_explainer)")
    auto_parser.add_argument("--rate", type=str, default="+0%", help="TTS speaking rate")
    auto_parser.add_argument("--pitch", type=str, default="-2Hz", help="TTS pitch")
    auto_parser.add_argument("--story-fallback", choices=["local", "gemini", "none"], default="local", help="Fallback engine if no script provided (default: local, zero API cost)")
    auto_parser.add_argument("--allow-local-fallback", action="store_true", help="Permit falling back to local procedural engine if Gemini API fails")
    auto_parser.add_argument("--auto-approve", action="store_true", help="Automatically proceed through all 3 gates without interactive prompts")
    auto_parser.set_defaults(func=cmd_auto)

    # 'run' subcommand
    run_parser = subparsers.add_parser("run", help="Generate finished short from story script, title, or approved plan")
    run_parser.add_argument("title", type=str, nargs="?", default=None, help="Story title (e.g. 'The 30th Floor')")
    run_parser.add_argument("--script", "-sc", type=str, default=None, help="Path to pre-authored story script (.json or .md/.txt)")
    run_parser.add_argument("--plan", "-p", type=str, default=None, help="Path to pre-approved plan JSON")
    run_parser.add_argument("--workspace", "-w", type=str, default=None, help="Workspace directory")
    run_parser.add_argument("--voice", "-v", type=str, default="en-US-AndrewMultilingualNeural", help="Narrator voice (Edge-TTS, Kokoro, ElevenLabs, or voicestudio:<profile>)")
    run_parser.add_argument("--voice-option", choices=["A", "B", "C", "a", "b", "c"], default="A", help="Select auditioned voice option (A: Natural [Permanent Narrator — Recommended], B: Suspenseful, C: Serious)")
    run_parser.add_argument("--style", "-s", type=str, choices=["dark_cinematic", "survival_explainer", "earthy_explainer"], default="dark_cinematic", help="Visual art style preset (dark_cinematic, earthy_explainer)")
    run_parser.add_argument("--rate", type=str, default="+0%", help="TTS speaking rate")
    run_parser.add_argument("--pitch", type=str, default="-2Hz", help="TTS pitch")
    run_parser.add_argument("--aspect-ratio", "-a", choices=["16:9", "9:16"], default="9:16", help="Video aspect ratio: 16:9 (horizontal master) or 9:16 (vertical short)")
    run_parser.add_argument("--flow-video", action="store_true", help="Generate full scene video clips via Google Flow Video instead of still images")
    run_parser.add_argument("--model", "-m", type=str, default="omni-flash", choices=["omni-flash", "veo-3.1-lite", "veo-3.1-fast", "veo-3.1-quality"], help="Flow video generation model")
    run_parser.add_argument("--dry-run", action="store_true", help="Simulate Flow image/video generation without consuming credits")
    run_parser.add_argument("--story-fallback", choices=["local", "gemini", "none"], default="local", help="Fallback engine if no script provided (default: local, zero API cost)")
    run_parser.add_argument("--allow-local-fallback", action="store_true", help="Permit falling back to local procedural engine if Gemini API fails")
    run_parser.add_argument("--auto-approve", action="store_true", help="Automatically proceed through all 3 gates without interactive prompts")
    run_parser.set_defaults(func=cmd_run)

    # 'flow-video' subcommand
    flow_video_parser = subparsers.add_parser("flow-video", help="Generate scene video clips via Google Flow with character continuity")
    flow_video_parser.add_argument("--script", "-sc", type=str, required=True, help="Path to story script file (.json or .md)")
    flow_video_parser.add_argument("--aspect-ratio", "-a", choices=["16:9", "9:16"], default="16:9", help="Aspect ratio: 16:9 horizontal master or 9:16 vertical short")
    flow_video_parser.add_argument("--model", "-m", type=str, default="omni-flash", choices=["omni-flash", "veo-3.1-lite", "veo-3.1-fast", "veo-3.1-quality"], help="Flow video generation model")
    flow_video_parser.add_argument("--character", type=str, default=None, help="Main character name (defaults to script primary character or 'The Wanderer')")
    flow_video_parser.add_argument("--reference-image", "-ref", type=str, default=None, help="Path to custom character reference image")
    flow_video_parser.add_argument("--auto-approve", action="store_true", help="Approve scene plan and credit cost automatically")
    flow_video_parser.add_argument("--dry-run", action="store_true", help="Simulate generation without consuming Flow credits")
    flow_video_parser.add_argument("--assemble", action="store_true", help="Assemble final MP4 video after scene generation")
    flow_video_parser.add_argument("--workspace", "-w", type=str, default=None, help="Workspace directory")
    flow_video_parser.set_defaults(func=cmd_flow_video)

    # 'thumbnail' subcommand
    thumb_parser = subparsers.add_parser("thumbnail", help="Generate or regenerate dedicated AI thumbnail via Google Flow")
    thumb_parser.add_argument("--script", "-sc", type=str, default=None, help="Path to story script file (.json or .md)")
    thumb_parser.add_argument("--bundle", "-b", type=str, default=None, help="Path to existing video output bundle folder")
    thumb_parser.add_argument("--prompt", "-p", type=str, default=None, help="Revised custom prompt for thumbnail regeneration")
    thumb_parser.add_argument("--aspect-ratio", "-a", choices=["16:9", "9:16"], default="16:9", help="Thumbnail aspect ratio: 16:9 YouTube master or 9:16 vertical cover")
    thumb_parser.add_argument("--style", "-s", type=str, choices=["earthy_explainer", "dark_cinematic", "survival_explainer"], default="earthy_explainer", help="Art style preset")
    thumb_parser.add_argument("--dry-run", action="store_true", help="Simulate thumbnail generation without consuming Flow credits")
    thumb_parser.add_argument("--workspace", "-w", type=str, default=None, help="Workspace directory")
    thumb_parser.set_defaults(func=cmd_thumbnail)

    # 'doctor' subcommand
    doc_parser = subparsers.add_parser("doctor", help="Run comprehensive pre-flight self-tests across GPU, FFmpeg, Flow, and VoiceStudio")
    doc_parser.add_argument("--report", action="store_true", help="Print Markdown report suitable for GitHub bug reports")
    doc_parser.add_argument("--workspace", "-w", type=str, default=None, help="Workspace directory")
    doc_parser.set_defaults(func=cmd_doctor)

    # 'report' subcommand
    report_parser = subparsers.add_parser("report", help="Generate a sanitized Markdown diagnostic report for GitHub issues")
    report_parser.add_argument("--workspace", "-w", type=str, default=None, help="Workspace directory")
    report_parser.set_defaults(func=cmd_report)

    # 'storage' subcommand
    storage_parser = subparsers.add_parser("storage", help="Audit and clean unused intermediate assets, clips, and audio files")
    storage_sub = storage_parser.add_subparsers(dest="storage_action", help="Storage action: audit, clean, restore")

    st_audit = storage_sub.add_parser("audit", help="Audit unused files across workspace and print recovery report")
    st_audit.add_argument("--days", type=float, default=None, help="Filter files older than N days")

    st_clean = storage_sub.add_parser("clean", help="Move approved unused files to recoverable .trash/ folder")
    st_clean.add_argument("--days", type=float, default=None, help="Filter files older than N days")
    st_clean.add_argument("--yes", "-y", action="store_true", help="Skip confirmation prompt")

    st_restore = storage_sub.add_parser("restore", help="Restore files from trash back to original paths")
    st_restore.add_argument("--manifest", type=str, default=None, help="Path to trash manifest.json (defaults to latest)")

    storage_parser.set_defaults(func=cmd_storage)

    # 'test-flow' subcommand
    test_parser = subparsers.add_parser("test-flow", help="Test generating 3 images via Google Flow")
    test_parser.add_argument("title", type=str, default="The 30th Floor", nargs="?", help="Story title")
    test_parser.set_defaults(func=cmd_test_flow)

    # 'caption' subcommand
    caption_parser = subparsers.add_parser("caption", help="Preview, edit, or copy social media captions for YouTube Shorts & Reels")
    caption_parser.add_argument("target", type=str, nargs="?", default=None, help="Bundle folder name, plan file, or story title (defaults to latest)")
    caption_parser.add_argument("--platform", "-p", choices=["youtube_shorts", "instagram_reels"], default="youtube_shorts", help="Target platform (default: youtube_shorts)")
    caption_parser.add_argument("--copy", "-c", action="store_true", help="Copy caption directly to clipboard and exit")
    caption_parser.add_argument("--edit", "-e", action="store_true", help="Edit the caption description")
    caption_parser.add_argument("--browser", "-b", action="store_true", help="Open interactive HTML card in browser")
    caption_parser.add_argument("--regenerate", "-r", action="store_true", help="Force regenerate from story metadata")
    caption_parser.add_argument("--workspace", "-w", type=str, default=None, help="Workspace directory")
    caption_parser.set_defaults(func=cmd_caption)

    # 'status' subcommand
    status_parser = subparsers.add_parser("status", help="Check Flow connection, quota, and audio assets")
    status_parser.set_defaults(func=cmd_status)

    # 'audit' subcommand
    audit_parser = subparsers.add_parser("audit", help="Audit a story plan or script across all 6 quality vectors")
    audit_parser.add_argument("target", type=str, nargs="?", default="The 30th Floor Lockdown", help="Story title, concept, or path to script/plan file")
    audit_parser.add_argument("--workspace", "-w", type=str, default=None, help="Workspace directory")
    audit_parser.set_defaults(func=cmd_audit)

    # 'produce' subcommand
    produce_parser = subparsers.add_parser("produce", help="Produce long-form 16:9 cinematic AI video (10-20 min)")
    produce_parser.add_argument("--longform", action="store_true", default=True, help="Enable long-form multi-act production")
    produce_parser.add_argument("--theme", "-t", type=str, default="You are trapped inside a supermarket during a zombie apocalypse", help="Story theme/concept")
    produce_parser.add_argument("--genre", "-g", type=str, default="zombie_apocalypse", help="Genre (zombie_apocalypse, survival_horror, etc.)")
    produce_parser.add_argument("--duration", "-d", type=int, default=15, help="Target duration in minutes (10-20)")
    produce_parser.add_argument("--model", "-m", type=str, default="omni-flash", choices=["omni-flash", "veo-3.1-lite", "veo-3.1-fast", "veo-3.1-quality"], help="Flow video generation model")
    produce_parser.add_argument("--name", "-n", type=str, default=None, help="Custom project output directory name")
    produce_parser.add_argument("--mock", action="store_true", help="Generate mock video clips for offline testing")
    produce_parser.add_argument("--workspace", "-w", type=str, default=None, help="Workspace directory")
    produce_parser.set_defaults(func=cmd_produce)

    # 'flow-agent' / 'agent-prompt' subcommand
    agent_parser = subparsers.add_parser("flow-agent", aliases=["agent-prompt"], help="Generate Flow Agent Master Prompt and 25-45 visual image beats for 1-3 min Reels")
    agent_parser.add_argument("--script", "-sc", type=str, default=None, help="Path to story script file (.json or .md)")
    agent_parser.add_argument("--title", "-t", type=str, default=None, help="Story title to generate script for")
    agent_parser.add_argument("--auto", action="store_true", help="Generate an original procedural story script")
    agent_parser.add_argument("--aspect-ratio", "-a", choices=["9:16", "16:9"], default="9:16", help="Aspect ratio (default: 9:16 vertical Reel)")
    agent_parser.add_argument("--universe", "-u", choices=["wanderer", "experimental"], default="wanderer", help="Creative direction: wanderer or experimental")
    agent_parser.add_argument("--character", type=str, default=None, help="Character name")
    agent_parser.add_argument("--character-desc", type=str, default=None, help="Custom character appearance and description")
    agent_parser.add_argument("--reference-image", "-ref", type=str, default=None, help="Path to character reference image")
    agent_parser.add_argument("--style", "-s", choices=["dark_cinematic", "earthy_explainer", "survival_explainer"], default="dark_cinematic", help="Art style preset")
    agent_parser.add_argument("--beats", type=int, default=None, help="Exact number of image beats (e.g. 24)")
    agent_parser.add_argument("--batch-size", type=int, default=10, help="Batch size for Flow Agent generation turns (e.g. 10 or 24)")
    agent_parser.add_argument("--beats-min", type=int, default=25, help="Minimum visual beats for Reel (default: 25)")
    agent_parser.add_argument("--beats-max", type=int, default=45, help="Maximum visual beats for Reel (default: 45)")
    agent_parser.add_argument("--bundle", "-b", type=str, default=None, help="Output project bundle directory")
    agent_parser.add_argument("--workspace", "-w", type=str, default=None, help="Workspace directory")
    agent_parser.set_defaults(func=cmd_flow_agent)

    # 'ingest-assets' subcommand
    ingest_parser = subparsers.add_parser("ingest-assets", help="Organize and validate Flow Agent generated images into bundle")
    ingest_parser.add_argument("--bundle", "-b", type=str, required=True, help="Target project bundle directory")
    ingest_parser.add_argument("--source", "-s", type=str, required=True, help="Source folder or zip of downloaded Flow Agent images")
    ingest_parser.add_argument("--aspect-ratio", "-a", choices=["9:16", "16:9"], default="9:16", help="Target aspect ratio")
    ingest_parser.add_argument("--workspace", "-w", type=str, default=None, help="Workspace directory")
    ingest_parser.set_defaults(func=cmd_ingest_assets)

    # 'assemble' subcommand
    assemble_parser = subparsers.add_parser("assemble", help="Assemble final 1-3 min vertical Reel from ingested assets")
    assemble_parser.add_argument("--bundle", "-b", type=str, required=True, help="Project bundle directory with images and script")
    assemble_parser.add_argument("--aspect-ratio", "-a", choices=["9:16", "16:9"], default="9:16", help="Target aspect ratio")
    assemble_parser.add_argument("--dry-run", action="store_true", help="Simulate video assembly without real rendering")
    assemble_parser.add_argument("--workspace", "-w", type=str, default=None, help="Workspace directory")
    assemble_parser.set_defaults(func=cmd_assemble)

    # 'settings' / 'config' subcommand
    settings_parser = subparsers.add_parser("settings", aliases=["config"], help="Inspect or update Scenecraft configuration settings")
    settings_parser.add_argument("--enable-auto-thumbnail", action="store_true", help="Enable automatic Flow AI thumbnail generation")
    settings_parser.add_argument("--disable-auto-thumbnail", action="store_true", help="Disable automatic Flow AI thumbnail generation")
    settings_parser.add_argument("--set", nargs="+", help="Update settings in KEY=VALUE format (e.g. auto_thumbnail=true)")
    settings_parser.add_argument("--workspace", "-w", type=str, default=None, help="Workspace directory")
    settings_parser.set_defaults(func=cmd_settings)

    # 'demo' subcommand
    demo_parser = subparsers.add_parser("demo", help="Render a 10-second offline demo video using bundled fixtures")
    demo_parser.add_argument("--live-tts", action="store_true", help="Synthesize live narration using configured TTS engine")
    demo_parser.add_argument("-o", "--out", type=str, default=None, help="Output directory for demo MP4")
    demo_parser.add_argument("--quiet", "-q", action="store_true", help="Suppress progress output")
    demo_parser.set_defaults(func=cmd_demo)

    # 'init' subcommand
    init_parser = subparsers.add_parser("init", help="Scaffold a fresh Scenecraft project directory")
    init_parser.add_argument("name", type=str, help="Project name (e.g. my_story)")
    init_parser.add_argument("--target-dir", "-t", type=str, default=None, help="Parent directory (default: current working dir)")
    init_parser.set_defaults(func=cmd_init)

    # 'make' subcommand
    make_parser = subparsers.add_parser("make", help="Run the full deterministic pipeline from project.json or script")
    make_parser.add_argument("project", type=str, help="Path to project.json or script")
    make_parser.add_argument("--images-dir", type=str, default=None, help="Directory of existing scene images (skips watermark cleaning unless --clean)")
    make_parser.add_argument("--clean", action="store_true", help="Apply watermark cleaning to custom images from --images-dir")
    make_parser.add_argument("--force", action="store_true", help="Force re-execution of all pipeline steps ignoring state file")
    make_parser.add_argument("--dry-run", action="store_true", help="Print planned execution steps without generating")
    make_parser.add_argument("--quiet", "-q", action="store_true", help="Suppress progress banners and detailed logs")
    make_parser.add_argument("--verbose", action="store_true", help="Print verbose step logs")
    make_parser.add_argument("--workspace", "-w", type=str, default=None, help="Workspace directory")
    make_parser.set_defaults(func=cmd_make)

    # 'setup' subcommand
    setup_parser = subparsers.add_parser("setup", help="Download LaMa ONNX, Kokoro, and Whisper models with resumable progress")
    setup_parser.add_argument("--tts", choices=["kokoro", "piper", "none"], default="kokoro", help="Default local TTS model to download (default: kokoro)")
    setup_parser.add_argument("--full", action="store_true", help="Download full Kokoro fp32 model instead of int8 quantized")
    setup_parser.add_argument("--models-only", action="store_true", help="Download models without prompting environment checks")
    setup_parser.add_argument("--whisper-model", type=str, default="base", help="Faster-Whisper model name (default: base)")
    setup_parser.add_argument("--force", action="store_true", help="Force re-download of existing models")
    setup_parser.set_defaults(func=cmd_setup)

    # 'voices' subcommand
    voices_parser = subparsers.add_parser("voices", help="List available voices or preview narration across engines")
    voices_parser.add_argument("engine", nargs="?", default=None, choices=["kokoro", "edge_tts", "omnivoice", "piper", "elevenlabs", "openai"], help="Filter by engine")
    voices_parser.add_argument("--preview", type=str, default=None, choices=["kokoro", "edge_tts", "omnivoice", "piper", "elevenlabs", "openai"], help="Synthesize a 2-second preview WAV for the given engine")
    voices_parser.add_argument("--voice", type=str, default=None, help="Voice identifier to use for preview")
    voices_parser.set_defaults(func=cmd_voices)

    # 'visuals' subcommand
    visuals_parser = subparsers.add_parser("visuals", help="Generate AI visual assets from project.json via Google Flow")
    visuals_parser.add_argument("project", type=str, help="Path to project.json")
    visuals_parser.add_argument("-o", "--output", type=str, default=None, help="Output directory for generated images")
    visuals_parser.add_argument("--dry-run", action="store_true", help="Preview prompts without generating")
    visuals_parser.set_defaults(func=cmd_visuals)

    # 'clean' subcommand
    clean_parser = subparsers.add_parser("clean", help="Clean visible corner watermarks from images or video")
    clean_parser.add_argument("input", type=str, help="Input image file or directory")
    clean_parser.add_argument("-o", "--output", type=str, required=True, help="Output directory or file path")
    clean_parser.add_argument("--corner", default="bottom-right", choices=["bottom-right", "bottom-left", "top-right", "top-left"])
    clean_parser.set_defaults(func=cmd_clean)

    # 'narrate' subcommand
    narrate_parser = subparsers.add_parser("narrate", help="Generate narration audio from project.json")
    narrate_parser.add_argument("project", type=str, help="Path to project.json")
    narrate_parser.add_argument("-o", "--out", type=str, default=None, help="Output narration audio path")
    narrate_parser.add_argument("--engine", type=str, default=None, choices=["omnivoice", "edge_tts", "piper"])
    narrate_parser.set_defaults(func=cmd_narrate)

    # 'subtitles' subcommand
    subs_parser = subparsers.add_parser("subtitles", help="Generate word-synced ASS subtitles from project.json and audio")
    subs_parser.add_argument("project", type=str, help="Path to project.json")
    subs_parser.add_argument("--audio", "-a", type=str, default=None, help="Path to narration audio WAV")
    subs_parser.add_argument("-o", "--out", type=str, default=None, help="Output .ass subtitle path")
    subs_parser.set_defaults(func=cmd_subtitles)

    # 'validate' subcommand
    val_parser = subparsers.add_parser("validate", help="Validate video bitstream decode and stream integrity")
    val_parser.add_argument("video", type=str, help="Path to MP4 video file to validate")
    val_parser.set_defaults(func=cmd_validate)

    from scenecraft.logger import setup_logging
    setup_logging()

    args = parser.parse_args()
    if not args.command:
        if len(sys.argv) > 1 and not sys.argv[1].startswith("-"):
            args.title = sys.argv[1]
            args.plan = None
            args.workspace = None
            args.voice = "en-US-AndrewMultilingualNeural"
            args.rate = "+0%"
            args.pitch = "-2Hz"
            try:
                cmd_run(args)
            except KeyboardInterrupt:
                sys.exit(130)
            except Exception as exc:
                _handle_cli_crash(exc)
            return
        parser.print_help()
        sys.exit(0)

    try:
        args.func(args)
    except KeyboardInterrupt:
        sys.exit(130)
    except SystemExit:
        raise
    except Exception as exc:
        _handle_cli_crash(exc)


def _handle_cli_crash(exc: Exception):
    """Log unexpected CLI crash and print helpful user instructions."""
    import logging
    import traceback
    logging.getLogger("scenecraft").error("CLI unhandled crash: %s\n%s", exc, traceback.format_exc())
    print(
        "\n" + "=" * 70 + "\n"
        f"💥 SCENECRAFT CRASH DETECTED: {type(exc).__name__}: {exc}\n"
        + "=" * 70 + "\n"
        "An unexpected error occurred during execution.\n"
        "To report this issue or ask for help without leaking private data, run:\n\n"
        "    scenecraft report\n\n"
        "Paste the Markdown output into a GitHub issue at:\n"
        "https://github.com/Varun1019/Scenecraft/issues/new/choose\n"
        + "=" * 70 + "\n",
        file=sys.stderr,
    )
    sys.exit(1)


if __name__ == "__main__":
    main()
