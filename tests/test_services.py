import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SERVER_ROOT = ROOT / "app" / "server"
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))

import config

TEST_LOG_ROOT = os.path.join(tempfile.gettempdir(), "steaimct-tutor-test-logs")
os.makedirs(TEST_LOG_ROOT, exist_ok=True)
config.ANALYSIS_LOG_FILE = os.path.join(TEST_LOG_ROOT, "analysis-log.txt")
config.MISTRAL_PROMPT_LOG_FILE = os.path.join(TEST_LOG_ROOT, "mistral-prompt-log.txt")

import email_service
import mistral_service
import settings_service
import step2_service
import text_utils


class TextUtilsTests(unittest.TestCase):
    def test_parse_subjects_value_accepts_json_and_delimited_text(self):
        self.assertEqual(text_utils.parse_subjects_value('["Arts", "Physics"]'), ["Arts", "Physics"])
        self.assertEqual(text_utils.parse_subjects_value("Arts; Physics, Arts"), ["Arts", "Physics"])

    def test_build_conversation_text_formats_messages(self):
        conversation = [
            {"role": "tutor", "text": "Hello", "time": "10:00"},
            {"role": "teacher", "text": "Please adapt it"},
        ]
        text = text_utils.build_conversation_text(conversation)
        self.assertIn("[10:00] tutor: Hello", text)
        self.assertIn("teacher: Please adapt it", text)


class Step2ServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="steaimct-test-")
        self.original_curricula_root = config.CURRICULA_ROOT
        self.original_amendments_root = config.AMENDMENTS_ROOT
        config.CURRICULA_ROOT = os.path.join(self.temp_dir, "curricula")
        config.AMENDMENTS_ROOT = os.path.join(self.temp_dir, "amendments")

    def tearDown(self):
        config.CURRICULA_ROOT = self.original_curricula_root
        config.AMENDMENTS_ROOT = self.original_amendments_root
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_ensure_step2_folder_structure_creates_country_and_subject_folders(self):
        result = step2_service.ensure_step2_folder_structure("Czech Republic", ["Informatics / CS", "Arts"])

        self.assertEqual(result["countrySlug"], "czech-republic")
        subject_slugs = [item["slug"] for item in result["subjects"]]
        self.assertEqual(subject_slugs, ["informatics-cs", "arts"])
        for item in result["subjects"]:
            self.assertTrue(os.path.isdir(item["curriculum"]))
            self.assertTrue(os.path.isdir(item["amendments"]))

    def test_ensure_step2_folder_structure_uses_unknown_subject_fallback(self):
        result = step2_service.ensure_step2_folder_structure("", [])

        self.assertEqual(result["countrySlug"], "unknown-country")
        self.assertEqual(result["subjects"][0]["slug"], "unknown-subject")


class MistralServiceTests(unittest.TestCase):
    def test_parse_json_response_block_repairs_common_model_mistakes(self):
        raw = """```json
        {summary: "ok", "done": True, "items": ["a",],}
        ```"""

        parsed, block = mistral_service.parse_json_response_block(raw)

        self.assertEqual(parsed["summary"], "ok")
        self.assertTrue(parsed["done"])
        self.assertEqual(parsed["items"], ["a"])
        self.assertIsInstance(block, str)

    def test_build_step3_memory_summary_includes_recent_context(self):
        payload = {
            "sessionId": "abc123",
            "country": "Austria",
            "subjects": ["Physics"],
            "userMessage": "This takes longer.",
            "currentNode": {"label": "Time scope", "pointTitle": "Timing is tight"},
            "draft": {
                "changes": [
                    {
                        "title": "Split lesson",
                        "beforeValue": "90 min",
                        "afterValue": "2 lessons",
                        "reason": "Reduce pressure",
                    }
                ]
            },
            "conversation": [
                {"role": "teacher", "text": "Please split it.", "time": "12:00"}
            ],
        }

        summary = mistral_service.build_step3_memory_summary(payload)

        self.assertIn("Session: abc123", summary)
        self.assertIn("Current focus: Time scope - Timing is tight", summary)
        self.assertIn("Latest teacher reply: This takes longer.", summary)
        self.assertIn("Split lesson (90 min -> 2 lessons): Reduce pressure", summary)
        self.assertIn("[12:00] teacher: Please split it.", summary)


class EmailServiceTests(unittest.TestCase):
    def test_build_change_steps_text_contains_only_change_package_content(self):
        context = {
            "sessionId": "mail-test",
            "sourceDocument": {"filename": "lesson.docx"},
            "draft": {
                "summary": "A short lesson summary.",
                "meta": {
                    "country": "Austria",
                    "subjects": ["Arts"],
                    "gradeRange": "2 to ?",
                    "ageRange": "7 to 8",
                },
                "changes": [
                    {
                        "title": "Add arts focus",
                        "source": "Steps",
                        "reason": "Selected subject is Arts.",
                        "beforeValue": "Build a ramp",
                        "afterValue": "Design and decorate a ramp",
                    }
                ],
            },
        }

        text = email_service.build_change_steps_text(context)

        self.assertIn("STEaiM-CT Tutor change steps", text)
        self.assertIn("Uploaded file: lesson.docx", text)
        self.assertIn("Subject(s): Arts", text)
        self.assertIn("1. Add arts focus @ Steps", text)
        self.assertIn("Before: Build a ramp", text)
        self.assertIn("After: Design and decorate a ramp", text)

    def test_build_analysis_points_text_formats_pros_and_cons(self):
        context = {
            "payload": {
                "analysis": {
                    "strengths": [{"title": "Clear goals", "short_explanation": "Goals are measurable."}],
                    "issues": [{"title": "Tight timing", "why_it_matters": "Transitions need more time."}],
                }
            }
        }

        pros = email_service.build_analysis_points_text(context, "strengths", "Pros")
        cons = email_service.build_analysis_points_text(context, "issues", "Cons")

        self.assertIn("1. Clear goals", pros)
        self.assertIn("Goals are measurable.", pros)
        self.assertIn("1. Tight timing", cons)
        self.assertIn("Transitions need more time.", cons)


class SettingsServiceTests(unittest.TestCase):
    def test_write_env_values_updates_existing_lines_and_preserves_others(self):
        temp_dir = tempfile.mkdtemp(prefix="steaimct-env-test-")
        env_path = os.path.join(temp_dir, ".env")
        try:
            with open(env_path, "w", encoding="utf-8") as env_file:
                env_file.write(
                    "\n".join([
                        "MISTRAL_API_KEY=old-key",
                        "# keep this comment",
                        "MISTRAL_MODEL=old-model",
                        "SMTP_HOST=smtp.example.test",
                    ])
                    + "\n"
                )

            settings_service.write_env_values({
                "MISTRAL_API_URL": "https://api.example.test/v1/chat/completions",
                "MISTRAL_MODEL": "new-model",
            }, path=env_path)

            content = Path(env_path).read_text(encoding="utf-8")
            self.assertIn("MISTRAL_API_KEY=old-key", content)
            self.assertIn("# keep this comment", content)
            self.assertIn("MISTRAL_MODEL=new-model", content)
            self.assertIn("SMTP_HOST=smtp.example.test", content)
            self.assertIn("MISTRAL_API_URL=https://api.example.test/v1/chat/completions", content)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
