import json
import os
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml
from yaml.nodes import MappingNode, ScalarNode, SequenceNode


PROJECT_ROOT = Path(__file__).parents[1]


class CloudFormationLoader(yaml.SafeLoader):
    pass


def construct_intrinsic(loader, tag_suffix, node):
    if isinstance(node, ScalarNode):
        return loader.construct_scalar(node)
    if isinstance(node, SequenceNode):
        return loader.construct_sequence(node)
    if isinstance(node, MappingNode):
        return loader.construct_mapping(node)
    raise TypeError(f"Unsupported CloudFormation node: {type(node).__name__}")


CloudFormationLoader.add_multi_constructor("!", construct_intrinsic)


def load_template(name):
    return yaml.load(
        (PROJECT_ROOT / name).read_text(encoding="utf-8"),
        Loader=CloudFormationLoader,
    )


class CloudFormationTests(unittest.TestCase):
    def test_tool_stack_uses_required_physical_names(self):
        template = load_template("cloudformation-tool.yaml")
        resources = template["Resources"]

        self.assertEqual(
            "BugReports", resources["BugReportTable"]["Properties"]["TableName"]
        )
        self.assertEqual(
            "create-bug-report-role",
            resources["BugReportFunctionRole"]["Properties"]["RoleName"],
        )
        self.assertEqual(
            "create-bug-report",
            resources["BugReportFunction"]["Properties"]["FunctionName"],
        )

    def test_deployed_inline_lambda_creates_open_ticket(self):
        template = load_template("cloudformation-tool.yaml")
        source = template["Resources"]["BugReportFunction"]["Properties"]["Code"]
        source = source["ZipFile"]

        class FakeTable:
            def __init__(self):
                self.items = []

            def put_item(self, **kwargs):
                self.items.append(kwargs["Item"])

        table = FakeTable()
        boto3_module = types.ModuleType("boto3")
        boto3_module.resource = lambda service: types.SimpleNamespace(
            Table=lambda name: table
        )
        namespace = {}
        with patch.dict(sys.modules, {"boto3": boto3_module}), patch.dict(
            os.environ, {"BUG_REPORT_TABLE": "BugReports"}
        ):
            exec(compile(source, "cloudformation-tool.yaml:ZipFile", "exec"), namespace)

        response = namespace["lambda_handler"](
            {
                "messageVersion": "1.0",
                "function": "create_bug_report",
                "actionGroup": "bug-report-actions",
                "parameters": [
                    {"name": "description", "value": "Checkout freezes"},
                    {"name": "environment", "value": "Chrome on macOS"},
                ],
            },
            None,
        )

        payload = response["response"]["functionResponse"]["responseBody"]
        payload = json.loads(payload["TEXT"]["body"])
        self.assertEqual("OPEN", payload["status"])
        self.assertEqual(1, len(table.items))
        self.assertEqual("Checkout freezes", table.items[0]["description"])

    def test_flow_has_three_exact_route_conditions_and_outputs(self):
        template = load_template("cloudformation-solution.yaml")
        definition = template["Resources"]["CustomerSupportFlow"]["Properties"]
        definition = definition["Definition"]
        nodes = {node["Name"]: node for node in definition["Nodes"]}
        conditions = nodes["RouteRequest"]["Configuration"]["Condition"]
        conditions = conditions["Conditions"]

        self.assertEqual(
            [
                {"Name": "Bug", "Expression": 'kind == "BUG"'},
                {"Name": "Platform", "Expression": 'kind == "PLATFORM"'},
                {"Name": "default"},
            ],
            conditions,
        )
        self.assertEqual(
            {"BugOutput", "FAQOutput", "HumanOutput"},
            {name for name, node in nodes.items() if node["Type"] == "Output"},
        )

    def test_each_conditional_handler_also_receives_message_data(self):
        template = load_template("cloudformation-solution.yaml")
        definition = template["Resources"]["CustomerSupportFlow"]["Properties"]
        connections = definition["Definition"]["Connections"]
        data_targets = {
            (
                connection["Target"],
                connection["Configuration"]["Data"]["TargetInput"],
            )
            for connection in connections
            if connection["Type"] == "Data"
        }
        conditional_targets = {
            connection["Configuration"]["Conditional"]["Condition"]: connection[
                "Target"
            ]
            for connection in connections
            if connection["Type"] == "Conditional"
        }

        self.assertTrue(
            {
                ("BugReportAssistant", "report"),
                ("AnswerFAQ", "question"),
                ("RedirectHuman", "request"),
            }.issubset(data_targets)
        )
        self.assertEqual(
            {
                "Bug": "BugReportAssistant",
                "Platform": "AnswerFAQ",
                "default": "RedirectHuman",
            },
            conditional_targets,
        )

    def test_bug_prompt_collects_required_fields_without_claiming_a_ticket(self):
        template = load_template("cloudformation-solution.yaml")
        definition = template["Resources"]["CustomerSupportFlow"]["Properties"]
        nodes = {node["Name"]: node for node in definition["Definition"]["Nodes"]}
        bug_node = nodes["BugReportAssistant"]
        self.assertEqual("Prompt", bug_node["Type"])
        inline = bug_node["Configuration"]["Prompt"]["SourceConfiguration"]["Inline"]
        prompt_text = inline["TemplateConfiguration"]["Text"]["Text"]
        self.assertIn("description", prompt_text.lower())
        self.assertIn("steps to reproduce", prompt_text.lower())
        self.assertIn("environment", prompt_text.lower())
        self.assertIn("explicitly labels them as steps", prompt_text.lower())
        self.assertIn("environment field as complete", prompt_text.lower())
        self.assertIn("Never claim that a database ticket", prompt_text)
        self.assertEqual(0, inline["InferenceConfiguration"]["Text"]["Temperature"])

        self.assertNotIn("BugReportAgent", template["Resources"])
        self.assertNotIn("BugReportAgentAlias", template["Resources"])

    def test_classifier_and_faq_prompts_match_rubric_contract(self):
        template = load_template("cloudformation-solution.yaml")
        definition = template["Resources"]["CustomerSupportFlow"]["Properties"]
        nodes = {node["Name"]: node for node in definition["Definition"]["Nodes"]}

        classifier = nodes["ClassifyRequest"]["Configuration"]["Prompt"]
        classifier = classifier["SourceConfiguration"]["Inline"]
        classifier_text = classifier["TemplateConfiguration"]["Text"]["Text"]
        self.assertIn("Output only BUG,", classifier_text)
        self.assertIn("PLATFORM or OTHER", classifier_text)
        self.assertEqual(0, classifier["InferenceConfiguration"]["Text"]["Temperature"])

        faq = nodes["AnswerFAQ"]["Configuration"]["Prompt"]
        faq_text = faq["SourceConfiguration"]["Inline"]["TemplateConfiguration"]
        faq_text = faq_text["Text"]["Text"]
        self.assertIn("FAQ:", faq_text)
        self.assertIn("Track orders in Account > Orders > Track shipment", faq_text)
        self.assertIn("packaging requirement", faq_text)
        self.assertIn("account ownership before closing", faq_text)
        self.assertIn("${SupportPhone}", faq_text)

        redirect = nodes["RedirectHuman"]["Configuration"]["Prompt"]
        redirect_text = redirect["SourceConfiguration"]["Inline"]
        redirect_text = redirect_text["TemplateConfiguration"]["Text"]["Text"]
        self.assertIn("${SupportPhone}", redirect_text)

    def test_flow_version_rotates_when_deployment_revision_changes(self):
        template = load_template("cloudformation-solution.yaml")
        parameters = template["Parameters"]
        version = template["Resources"]["CustomerSupportFlowVersion"]
        description = version["Properties"]["Description"]

        self.assertIn("DeploymentRevision", parameters)
        self.assertIn("${DeploymentRevision}", description)

    def test_flow_tests_cover_all_routes_and_uncovered_faq(self):
        suite = json.loads((PROJECT_ROOT / "flow-tests.json").read_text(encoding="utf-8"))
        cases = suite["tests"]
        self.assertTrue({"bug", "platform", "other"}.issubset({case["category"] for case in cases}))
        uncovered = next(
            case for case in cases if case["id"] == "t7_platform_uncovered_gift_wrapping"
        )
        self.assertEqual("platform", uncovered["category"])
        self.assertIn("does not provide", uncovered["expected"])
        self.assertIn("+1-800-555-0147", uncovered["expected"])


if __name__ == "__main__":
    unittest.main()
