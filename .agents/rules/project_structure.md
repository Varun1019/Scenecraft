# Project Structure Rule: Video Folder Isolation

Every produced video must have its own isolated project folder inside `output/<video_title_slug>/`.

Never scatter video files, audio tracks, or raw images across the root directory.

Each project directory must strictly encapsulate all related assets:
- `output/<video_title_slug>/<video_title_slug>.mp4` (Final master video)
- `output/<video_title_slug>/images/` (All final scene images)
- `output/<video_title_slug>/images_raw/` (Raw AI generations before border/watermark cleanup)
- `output/<video_title_slug>/audio/` (Narration tracks, scene WAVs, mixed audio)
- `output/<video_title_slug>/video/` (Individual scene video clips)
- `output/<video_title_slug>/shorts/` (All extracted 9:16 vertical shorts)
- `output/<video_title_slug>/metadata/` (Title, description, chapter timestamps, shorts captions, tags)
- `output/<video_title_slug>/subtitles.ass` (Master subtitles)
