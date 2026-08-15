import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


MODULE_PATH = Path(__file__).parents[1] / "scripts" / "verify_workspace.py"
SPEC = importlib.util.spec_from_file_location("verify_workspace", MODULE_PATH)
verify_workspace = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(verify_workspace)


class WorkspaceFixture:
    repos = verify_workspace.EXPECTED_REPOSITORIES

    def __init__(self, root: Path):
        self.root = root
        for name in self.repos:
            (root / name).mkdir()

        self.write_json(
            "creator-brain/examples/brief.example.json",
            {
                "schema_version": "1.0.0",
                "human_gates": list(verify_workspace.REQUIRED_HUMAN_GATES),
            },
        )
        self.write_json(
            "creator-tool-arsenal/catalog/tools.json",
            [{"schema_version": "1.0.0", "id": "example"}],
        )
        self.write_json(
            "creator-production-platform/templates/episode/manifest.template.json",
            {
                "schema_version": "1.0.0",
                "human_gates": {
                    "claims_and_script": False,
                    "final_quality": False,
                    "public_posting": False,
                },
            },
        )
        self.write_json(
            "creator-governance/templates/approval-gates.json",
            {
                "schema_version": "1.0.0",
                "gates": [
                    {"id": gate, "actor": "human"}
                    for gate in verify_workspace.REQUIRED_HUMAN_GATES
                ],
            },
        )
        self.write_json(
            "creator-governance/templates/license-record.example.json",
            {"schema_version": "1.0.0", "review_status": "needs-human-review"},
        )
        self.write_json(
            "creatoros/contracts/examples/qc-report.example.json",
            {
                "schema_version": "1.0.0",
                "human_checks": {
                    "claims_and_script": False,
                    "final_quality": False,
                    "public_posting": False,
                },
            },
        )

    def write_json(self, relative: str, value):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value), encoding="utf-8")
        return path


class VerifyWorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.fixture = WorkspaceFixture(self.root)

    def tearDown(self):
        self.tempdir.cleanup()

    def assert_error_contains(self, errors, text):
        self.assertTrue(any(text in error for error in errors), errors)

    def test_valid_system_only_workspace_has_no_errors(self):
        self.assertEqual(verify_workspace.verify_workspace(self.root), [])

    def test_missing_expected_sibling_is_reported(self):
        shutil.rmtree(self.root / "creator-brain")
        errors = verify_workspace.verify_workspace(self.root)
        self.assert_error_contains(errors, "missing repository: creator-brain")

    def test_malformed_json_is_reported(self):
        bad = self.root / "creator-brain" / "broken.json"
        bad.write_text("{not json", encoding="utf-8")
        errors = verify_workspace.verify_workspace(self.root)
        self.assert_error_contains(errors, "invalid JSON")

    def test_examples_and_catalog_require_schema_version_1_0_0(self):
        self.fixture.write_json(
            "creator-brain/examples/brief.example.json",
            {"schema_version": "2.0.0", "human_gates": list(verify_workspace.REQUIRED_HUMAN_GATES)},
        )
        errors = verify_workspace.verify_workspace(self.root)
        self.assert_error_contains(errors, "schema_version must be 1.0.0")

    def test_npm_package_metadata_inside_examples_is_not_a_creatoros_contract(self):
        self.fixture.write_json(
            "creator-production-platform/examples/reference-short/package.json",
            {"name": "creatoros-reference-short", "private": True},
        )
        self.fixture.write_json(
            "creator-production-platform/examples/reference-short/package-lock.json",
            {"name": "creatoros-reference-short", "lockfileVersion": 3},
        )
        self.assertEqual(verify_workspace.verify_workspace(self.root), [])

    def test_audio_and_video_files_are_rejected(self):
        media = self.root / "creator-production-platform" / "example.mp4"
        media.write_bytes(b"not-real-media")
        errors = verify_workspace.verify_workspace(self.root)
        self.assert_error_contains(errors, "audio/video file is not allowed")

    def test_static_reference_images_are_allowed(self):
        image = self.root / "creator-production-platform" / "docs" / "reference" / "diagram.png"
        image.parent.mkdir(parents=True)
        image.write_bytes(b"synthetic-image-fixture")
        self.assertEqual(verify_workspace.verify_workspace(self.root), [])

    def test_untracked_files_are_ignored_in_git_repositories(self):
        repository = self.root / "creator-production-platform"
        subprocess.run(
            ["git", "init", "-q", str(repository)],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "-C", str(repository), "add", "."],
            check=True,
            capture_output=True,
        )
        (repository / "local-preview.wav").write_bytes(b"untracked-local-fixture")
        self.assertEqual(verify_workspace.verify_workspace(self.root), [])

    def test_private_content_directories_are_rejected(self):
        private = self.root / "creatoros" / "episodes" / "EP999-private"
        private.mkdir(parents=True)
        (private / "script.md").write_text("private", encoding="utf-8")
        errors = verify_workspace.verify_workspace(self.root)
        self.assert_error_contains(errors, "private-content path is not allowed")

    def test_absolute_private_paths_in_examples_are_rejected(self):
        example = self.root / "creatoros" / "contracts" / "examples" / "bad.json"
        example.parent.mkdir(parents=True, exist_ok=True)
        private_path = "/" + "Users/alice/private.wav"
        example.write_text(
            json.dumps({"schema_version": "1.0.0", "path": private_path}),
            encoding="utf-8",
        )
        errors = verify_workspace.verify_workspace(self.root)
        self.assert_error_contains(errors, "absolute private path")

    def test_absolute_private_paths_in_documentation_are_rejected(self):
        documentation = self.root / "creator-content-workspace" / "README.md"
        documentation.write_text(
            "Real content is at `" + "/" + "Users/alice/private`.",
            encoding="utf-8",
        )
        errors = verify_workspace.verify_workspace(self.root)
        self.assert_error_contains(errors, "absolute private path")

    def test_schema_definitions_are_not_treated_as_example_records(self):
        schema = self.root / "creator-governance" / "schemas" / "license-record.schema.json"
        self.fixture.write_json(
            "creator-governance/schemas/license-record.schema.json",
            {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "properties": {
                    "review_status": {
                        "enum": ["needs-human-review", "approved", "rejected"]
                    }
                },
            },
        )
        self.assertTrue(schema.exists())
        self.assertEqual(verify_workspace.verify_workspace(self.root), [])

    def test_all_canonical_contract_schemas_exist_and_are_valid_json(self):
        schemas = MODULE_PATH.parents[1] / "contracts" / "schemas"
        expected = {
            "content-brief.schema.json",
            "episode-manifest.schema.json",
            "license-record.schema.json",
            "production-plan.schema.json",
            "qc-report.schema.json",
            "tool-record.schema.json",
        }
        self.assertEqual({path.name for path in schemas.glob("*.json")}, expected)
        for path in schemas.glob("*.json"):
            self.assertIsInstance(json.loads(path.read_text(encoding="utf-8")), dict)

    def test_component_contract_must_match_canonical_contract(self):
        canonical = {"$schema": "https://json-schema.org/draft/2020-12/schema", "title": "canonical"}
        component = {"$schema": "https://json-schema.org/draft/2020-12/schema", "title": "stale"}
        self.fixture.write_json(
            "creatoros/contracts/schemas/license-record.schema.json", canonical
        )
        self.fixture.write_json(
            "creator-governance/schemas/license-record.schema.json", component
        )

        errors = verify_workspace.verify_workspace(self.root)
        self.assert_error_contains(errors, "contract diverges from canonical schema")

    def test_human_gate_defaults_must_remain_unapproved(self):
        manifest = self.root / "creator-production-platform/templates/episode/manifest.template.json"
        data = json.loads(manifest.read_text(encoding="utf-8"))
        data["human_gates"]["public_posting"] = True
        manifest.write_text(json.dumps(data), encoding="utf-8")
        errors = verify_workspace.verify_workspace(self.root)
        self.assert_error_contains(errors, "human-gate defaults")

    def test_cli_returns_nonzero_and_prints_errors(self):
        shutil.rmtree(self.root / "creator-brain")
        result = subprocess.run(
            [sys.executable, str(MODULE_PATH), "--repos-root", str(self.root)],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("missing repository: creator-brain", result.stderr)


if __name__ == "__main__":
    unittest.main()
