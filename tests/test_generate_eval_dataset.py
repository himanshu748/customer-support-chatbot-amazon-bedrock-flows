import json
import importlib.util
import tempfile
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).parents[1] / "generate-eval-dataset.py"
SPEC = importlib.util.spec_from_file_location("generate_eval_dataset", SCRIPT_PATH)
generate_eval_dataset = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(generate_eval_dataset)
load_test_suite = generate_eval_dataset.load_test_suite
make_record = generate_eval_dataset.make_record


class GenerateEvalDatasetTests(unittest.TestCase):
    def write_suite(self, payload):
        temporary = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        with temporary:
            json.dump(payload, temporary)
        self.addCleanup(Path(temporary.name).unlink, missing_ok=True)
        return Path(temporary.name)

    def test_loads_required_contract_and_optional_follow_ups(self):
        path = self.write_suite(
            {
                "flowInputNode": {"nodeName": "FlowInput"},
                "tests": [
                    {
                        "id": "bug-1",
                        "prompt": "Checkout freezes",
                        "expected": "Create a ticket",
                        "follow_up_responses": ["Chrome on macOS"],
                    }
                ],
            }
        )

        node_name, tests = load_test_suite(path)

        self.assertEqual("FlowInput", node_name)
        self.assertEqual("bug-1", tests[0]["id"])

    def test_rejects_duplicate_test_ids(self):
        case = {"id": "same", "prompt": "hello", "expected": "reply"}
        path = self.write_suite(
            {
                "flowInputNode": {"nodeName": "FlowInput"},
                "tests": [case, dict(case)],
            }
        )

        with self.assertRaisesRegex(ValueError, "Duplicate test id"):
            load_test_suite(path)

    def test_builds_bedrock_precomputed_inference_record(self):
        record = make_record(
            {
                "id": "faq-1",
                "category": "platform",
                "prompt": "Where is tracking?",
                "expected": "Explain Account > Orders",
            },
            "Assistant: Open Account > Orders.",
            "my-flow-app",
        )

        self.assertEqual("Where is tracking?", record["prompt"])
        self.assertEqual("platform", record["category"])
        self.assertEqual("Explain Account > Orders", record["referenceResponse"])
        self.assertEqual(
            {
                "response": "Assistant: Open Account > Orders.",
                "modelIdentifier": "my-flow-app",
            },
            record["modelResponses"][0],
        )


if __name__ == "__main__":
    unittest.main()
