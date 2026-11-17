# StoryForge Workspace Directives

## Mandatory Workflow Instruction
Before performing any video production, script adaptation, visual generation, audio synthesis, or rendering task in StoryForge, you MUST read and strictly adhere to the permanent StoryForge Production Workflow:

👉 [StoryForge Production Workflow](file:///home/varun/Desktop/StoryForge/.agents/rules/storyforge_production_workflow.md)

### Strict Production Rules
1. **Follow the 20-Step Order**: Strictly execute steps 1 through 20 in order without skipping phases.
2. **Permanent Voice**: Use StoryForge Voice Option A (`6f7af622`, Rooftop Survivor) via VoiceStudio on port 3900.
3. **Automatic Thumbnail**: Always create an independent, dedicated thumbnail prompt and deliver `thumbnail.png` without waiting for the user to request it. Never extract a frame from video.
4. **Non-Overlapping Subtitles**: Generate separate word-aligned ASS subtitle tracks. Subtitle cues must never overlap; each cue must disappear before the next begins.
5. **Watermark Policy**: Do not alter or bypass existing watermark handling or provider watermark policies. Keep existing watermark implementations intact.
6. **Project Isolation**: Store all generated assets in `output/<project_slug>/` as defined in `.agents/rules/project_structure.md`.
7. **Credit Safety**: Never submit billable Flow batches or consume credits without explicit prior user approval.
