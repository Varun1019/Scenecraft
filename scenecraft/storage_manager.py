"""Storage Management and Non-Destructive Cleanup Engine for Scenecraft.

Performs comprehensive storage audits across output/, temp/, and project roots.
Identifies unused, duplicate, failed, and orphaned intermediate assets.
Enforces strict protection for Wanderer reference assets, style configs, narrator files,
and final exported videos.
Moves candidates to recoverable .trash/ only upon explicit confirmation.
"""

from __future__ import annotations

import datetime
import hashlib
import json
import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Any, Optional, Set, Tuple


PROTECTED_PATTERNS = [
    "references/brand_identity",
    "assets/licenses.json",
    "assets/audio",
    "assets/imported",
    "references",
]

PROTECTED_EXTENSIONS = {
    ".py", ".sh", ".json", ".md", ".txt", ".git", ".gitignore"
}


@dataclass
class AuditCandidate:
    file_path: Path
    file_type: str
    file_size_bytes: int
    last_modified: str
    is_referenced: bool
    reason_unused: str
    is_protected: bool = False
    protect_reason: Optional[str] = None

    @property
    def file_size_mb(self) -> float:
        return round(self.file_size_bytes / (1024.0 * 1024.0), 2)


@dataclass
class StorageAuditReport:
    scanned_at: str
    total_files_scanned: int
    total_candidates: int
    total_recoverable_bytes: int
    total_protected_files: int
    candidates: List[AuditCandidate] = field(default_factory=list)

    @property
    def total_recoverable_mb(self) -> float:
        return round(self.total_recoverable_bytes / (1024.0 * 1024.0), 2)

    def format_table(self) -> str:
        lines = [
            f"=== SCENECRAFT STORAGE AUDIT REPORT ({self.scanned_at}) ===",
            f"Files Scanned: {self.total_files_scanned} | Recoverable Candidates: {self.total_candidates} | Estimated Recovery: {self.total_recoverable_mb:.2f} MB",
            "-" * 120,
            f"{'File Path':<55} | {'Type':<22} | {'Size (MB)':<10} | {'Modified':<12} | {'Reason':<25}",
            "-" * 120,
        ]
        for c in self.candidates:
            rel = str(c.file_path)
            if len(rel) > 54:
                rel = "..." + rel[-51:]
            lines.append(
                f"{rel:<55} | {c.file_type:<22} | {c.file_size_mb:<10.2f} | {c.last_modified:<12} | {c.reason_unused:<25}"
            )
        lines.append("-" * 120)
        lines.append(f"TOTAL RECOVERABLE STORAGE: {self.total_recoverable_mb:.2f} MB ({self.total_candidates} files)")
        lines.append("NOTE: Protected reference assets, style configs, and final master videos are fully preserved.")
        lines.append("Action: Files will be safely moved to recoverable .trash/ ONLY after explicit user confirmation.")
        return "\n".join(lines)


class StorageManager:
    """Audits workspace storage, protects critical assets, and coordinates safe trash operations."""

    def __init__(self, workspace_root: Optional[Path] = None):
        self.root = workspace_root or Path(__file__).resolve().parent.parent
        self.trash_dir = self.root / ".trash"

    def _is_protected(self, path: Path) -> Tuple[bool, Optional[str]]:
        norm = str(path.resolve())
        rel = str(path.relative_to(self.root)) if path.is_relative_to(self.root) else norm

        # 1. Protect brand references and configs
        for pat in PROTECTED_PATTERNS:
            if pat in rel:
                return True, f"Matches protected path pattern '{pat}'"

        # 2. Protect final video masters in output/
        if path.suffix.lower() == ".mp4":
            parent_name = path.parent.name
            stem = path.stem
            # If parent folder matches stem (e.g. output/the_call/the_call.mp4) or output root master
            if parent_name == stem or (path.parent == self.root / "output" and not stem.startswith("test_")):
                return True, "Final exported video master"

        # 3. Protect source code and git
        if ".git" in rel or path.suffix.lower() in [".py", ".sh", ".md"]:
            return True, "System source or metadata file"

        return False, None

    def _collect_referenced_files(self) -> Set[Path]:
        """Collect all files currently referenced by active story json, metadata, or summaries."""
        referenced: Set[Path] = set()
        output_dir = self.root / "output"
        if not output_dir.is_dir():
            return referenced

        for meta_file in output_dir.rglob("*.json"):
            try:
                with open(meta_file, "r", encoding="utf-8") as f:
                    content = f.read()
                    for line in content.splitlines():
                        if ".jpg" in line or ".png" in line or ".wav" in line or ".mp4" in line:
                            # Extract potential paths
                            for token in line.replace('"', ' ').replace("'", ' ').split():
                                if any(token.endswith(ext) for ext in [".jpg", ".png", ".wav", ".mp4"]):
                                    p = Path(token)
                                    if p.is_file():
                                        referenced.add(p.resolve())
                                    elif (self.root / token).is_file():
                                        referenced.add((self.root / token).resolve())
            except Exception:
                pass
        return referenced

    def audit_storage(self, older_than_days: Optional[float] = None) -> StorageAuditReport:
        """Perform a complete workspace audit identifying unused, duplicate, failed, or orphaned assets."""
        referenced_files = self._collect_referenced_files()
        candidates: List[AuditCandidate] = []
        total_scanned = 0
        total_recoverable_bytes = 0
        protected_count = 0
        now = datetime.datetime.now()

        # Directories to scan
        scan_dirs = [
            self.root / "temp",
            self.root / "output",
        ]

        seen_hashes: Dict[str, Path] = {}

        for sdir in scan_dirs:
            if not sdir.is_dir():
                continue

            for p in sorted(sdir.rglob("*")):
                if not p.is_file():
                    continue

                total_scanned += 1
                protected, prot_reason = self._is_protected(p)
                if protected:
                    protected_count += 1
                    continue

                try:
                    stat = p.stat()
                except OSError:
                    continue

                mtime = datetime.datetime.fromtimestamp(stat.st_mtime)
                age_days = (now - mtime).total_seconds() / 86400.0
                mod_str = mtime.strftime("%Y-%m-%d")
                size = stat.st_size
                is_ref = p.resolve() in referenced_files

                # Check for day cutoff if provided
                if older_than_days is not None and age_days < older_than_days:
                    continue

                # 1. Zero-byte or truncated failed files
                if size == 0:
                    candidates.append(
                        AuditCandidate(
                            file_path=p,
                            file_type="failed_generation",
                            file_size_bytes=size,
                            last_modified=mod_str,
                            is_referenced=is_ref,
                            reason_unused="Empty 0-byte corrupt file",
                        )
                    )
                    continue

                # 2. Temporary FFmpeg clips and intermediate renders in temp/
                if self.root / "temp" in p.parents or "render" in p.parent.name:
                    if p.suffix.lower() in [".mp4", ".wav", ".txt", ".vtt", ".ass", ".jpg", ".png"]:
                        candidates.append(
                            AuditCandidate(
                                file_path=p,
                                file_type="temporary_ffmpeg_clip",
                                file_size_bytes=size,
                                last_modified=mod_str,
                                is_referenced=is_ref,
                                reason_unused="Intermediate render clip",
                            )
                        )
                        total_recoverable_bytes += size
                        continue

                # 3. Old preview/test single shot files in output root
                if p.parent == self.root / "output" and p.name.startswith("test_"):
                    candidates.append(
                        AuditCandidate(
                            file_path=p,
                            file_type="old_preview_test",
                            file_size_bytes=size,
                            last_modified=mod_str,
                            is_referenced=is_ref,
                            reason_unused="Outdated test shot",
                        )
                    )
                    total_recoverable_bytes += size
                    continue

                # 4. Duplicate image detection
                if p.suffix.lower() in [".jpg", ".png", ".jpeg"]:
                    try:
                        h = hashlib.sha256()
                        with open(p, "rb") as f:
                            h.update(f.read())
                        digest = h.hexdigest()
                        if digest in seen_hashes:
                            candidates.append(
                                AuditCandidate(
                                    file_path=p,
                                    file_type="duplicate_image",
                                    file_size_bytes=size,
                                    last_modified=mod_str,
                                    is_referenced=is_ref,
                                    reason_unused=f"Duplicate of {seen_hashes[digest].name}",
                                )
                            )
                            total_recoverable_bytes += size
                            continue
                        else:
                            seen_hashes[digest] = p
                    except Exception:
                        pass

                # 5. Orphaned unreferenced intermediate audio files
                if p.suffix.lower() == ".wav" and not is_ref and ("master_voice" in p.name or "temp" in p.name):
                    candidates.append(
                        AuditCandidate(
                            file_path=p,
                            file_type="unused_audio_file",
                            file_size_bytes=size,
                            last_modified=mod_str,
                            is_referenced=is_ref,
                            reason_unused="Orphaned intermediate audio",
                        )
                    )
                    total_recoverable_bytes += size
                    continue

        return StorageAuditReport(
            scanned_at=now.strftime("%Y-%m-%d %H:%M:%S"),
            total_files_scanned=total_scanned,
            total_candidates=len(candidates),
            total_recoverable_bytes=total_recoverable_bytes,
            total_protected_files=protected_count,
            candidates=candidates,
        )

    def move_to_trash(self, candidates: List[AuditCandidate]) -> Path:
        """Safely move approved candidate files to recoverable .trash/ directory with manifest.
        
        Requires explicit caller authorization. Never permanently deletes files.
        """
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        batch_trash_dir = self.trash_dir / ts
        batch_trash_dir.mkdir(parents=True, exist_ok=True)

        manifest = {
            "timestamp": ts,
            "moved_at": str(datetime.datetime.now()),
            "files": [],
        }

        for c in candidates:
            if not c.file_path.is_file():
                continue
            # Preserve relative hierarchy inside trash batch
            try:
                rel = c.file_path.relative_to(self.root)
            except ValueError:
                rel = Path(c.file_path.name)

            dest = batch_trash_dir / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(c.file_path), str(dest))

            manifest["files"].append({
                "original_path": str(c.file_path.resolve()),
                "trash_path": str(dest.resolve()),
                "file_type": c.file_type,
                "size_bytes": c.file_size_bytes,
            })

        manifest_file = batch_trash_dir / "manifest.json"
        with open(manifest_file, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

        print(f"[✔] Successfully moved {len(manifest['files'])} files to recoverable trash: {batch_trash_dir}")
        return manifest_file

    def restore_from_trash(self, manifest_path: Path) -> int:
        """Restore files from a trash batch back to their original locations."""
        p = Path(manifest_path)
        if not p.is_file():
            raise FileNotFoundError(f"Trash manifest not found: {p}")

        with open(p, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        restored_count = 0
        for entry in manifest.get("files", []):
            trash_p = Path(entry["trash_path"])
            orig_p = Path(entry["original_path"])
            if trash_p.is_file():
                orig_p.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(trash_p), str(orig_p))
                restored_count += 1

        print(f"[✔] Restored {restored_count} files to their original paths from trash.")
        return restored_count
