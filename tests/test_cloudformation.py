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
                ("BugAgent", "agentInputText"),
                ("AnswerFAQ", "question"),
                ("RedirectHuman", "request"),
            }.issubset(data_targets)
        )
        self.assertEqual(
            {
                "Bug": "BugAgent",
                "Platform": "AnswerFAQ",
                "default": "RedirectHuman",
            },
            conditional_targets,
        )


if __name__ == "__main__":
    unittest.main()
