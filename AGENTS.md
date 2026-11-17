# Scenecraft Workspace Directives

## Mandatory Workflow Instruction
Before performing any video production, script adaptation, visual generation, audio synthesis, or rendering task in Scenecraft, you MUST read and strictly adhere to the Scenecraft Production Workflow:

👉 [Scenecraft Production Workflow](.agents/rules/scenecraft_production_workflow.md)

### Strict Production Rules
1. **Follow the Production Order**: Strictly execute the pipeline steps in order without skipping phases.
2. **Narration Voice**: Use narrator settings and voice ID configured in `config.yaml` / `.env`.
3. **Automatic Thumbnail**: Always create an independent, dedicated thumbnail prompt and deliver `thumbnail.png`. Never extract a frame from video.
4. **Non-Overlapping Subtitles**: Generate word-aligned ASS subtitle tracks. Subtitle cues must never overlap; each cue must disappear before the next begins.
5. **Watermark Policy**: Keep watermark cleaning modular, reproducible, and compliant.
6. **Project Isolation**: Store all generated assets in `output/<project_slug>/`.
7. **Credit Safety**: Never submit billable Flow batches or consume credits without explicit prior user approval.
