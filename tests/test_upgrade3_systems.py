"""Tests for Upgrade 3: Audio chain, Rendering profiles, Resource Management, Storage, and Doctor."""

import unittest
import tempfile
from pathlib import Path
from scenecraft.resource_manager import ResourceManager, ImageAssetWorker, AudioWorker, VideoWorker
from scenecraft.storage_manager import StorageManager
from scenecraft.dependency_graph import DependencyGraph, compute_sha256
from scenecraft.metadata_generator import MetadataGenerator
from scenecraft.doctor import SystemDoctor


class TestUpgrade3Systems(unittest.TestCase):

    def test_resource_manager_metrics(self):
        """Verify ResourceManager polls CPU, RAM, and GPU safely."""
        rm = ResourceManager()
        metrics = rm.get_metrics()
        self.assertIsInstance(metrics.cpu_percent, float)
        self.assertIsInstance(metrics.safe_to_render, bool)
        self.assertGreaterEqual(metrics.ram_total_mb, 1000.0)

    def test_storage_manager_audit_and_protection(self):
        """Verify storage manager audits files while strictly protecting critical assets."""
        sm = StorageManager()
        # Brand reference must be protected
        ref_file = sm.root / "references" / "brand_identity" / "style_config.json"
        is_prot, reason = sm._is_protected(ref_file)
        self.assertTrue(is_prot)

        # Audit run returns valid report
        rep = sm.audit_storage()
        self.assertGreaterEqual(rep.total_files_scanned, 0)
        self.assertIsInstance(rep.total_recoverable_mb, float)

    def test_dependency_graph_invalidation(self):
        """Verify dependency graph tracks scene changes surgically."""
        with tempfile.TemporaryDirectory() as td:
            graph = DependencyGraph(Path(td))
            h1 = graph.compute_scene_narration_hash({"narration": "Hello world", "emotion": "SUSPENSE"}, "voice1", "+0%")
            h2 = graph.compute_scene_narration_hash({"narration": "Hello world", "emotion": "SUSPENSE"}, "voice1", "+0%")
            h3 = graph.compute_scene_narration_hash({"narration": "Changed text", "emotion": "SUSPENSE"}, "voice1", "+0%")
            self.assertEqual(h1, h2)
            self.assertNotEqual(h1, h3)

    def test_metadata_generator(self):
        """Verify YouTube Shorts publishing metadata generation."""
        gen = MetadataGenerator()
        scenes = [{"narration": "You hear breathing outside the locked door."}]
        meta = gen.generate_metadata(
            story_title="The Locked Door",
            story_summary="A suspenseful encounter behind a deadbolt.",
            scenes=scenes,
            hook_text="You hear breathing outside.",
        )
        self.assertIn("The Locked Door", meta.youtube_title)
        self.assertIn("#Shorts", meta.hashtags)
        self.assertIn("#TheWanderer", meta.hashtags)
        self.assertIn("The Wanderer", meta.description)

    def test_system_doctor_preflight(self):
        """Verify system doctor checks run and return comprehensive report."""
        doc = SystemDoctor()
        checks = doc.run_all_checks()
        self.assertGreaterEqual(len(checks), 8)
        names = [c.name for c in checks]
        self.assertIn("Python Environment", names)
        self.assertIn("FFmpeg Installation", names)
        self.assertIn("The Wanderer Brand Identity", names)


if __name__ == "__main__":
    unittest.main()
