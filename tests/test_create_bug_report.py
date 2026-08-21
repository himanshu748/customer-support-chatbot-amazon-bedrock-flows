import json
import unittest

import create_bug_report


class FakeTable:
    def __init__(self):
        self.calls = []

    def put_item(self, **kwargs):
        self.calls.append(kwargs)
        return {"ResponseMetadata": {"HTTPStatusCode": 200}}


def event(parameters, function="create_bug_report", version="1.0"):
    return {
        "messageVersion": version,
        "actionGroup": "bug-report-actions",
        "function": function,
        "sessionId": "test-session-001",
        "parameters": [
            {"name": name, "type": "string", "value": value}
            for name, value in parameters.items()
        ],
        "sessionAttributes": {"session": "kept"},
        "promptSessionAttributes": {"turn": "kept"},
    }


VALID_PARAMETERS = {
    "description": "The checkout page becomes unresponsive.",
    "stepsToReproduce": "Add item, open checkout, press Continue.",
    "environment": "Chrome 120 on macOS Sonoma",
}


def flow_event(payload):
    return {
        "messageVersion": "1.0",
        "flow": {
            "flowArn": "arn:aws:bedrock:us-east-1:111122223333:flow/TESTFLOW",
            "flowAliasArn": (
                "arn:aws:bedrock:us-east-1:111122223333:flow/TESTFLOW/alias/LIVE"
            ),
        },
        "node": {
            "name": "CreateBugReport",
            "inputs": [
                {
                    "name": "bugReport",
                    "type": "String",
                    "expression": "$.data",
                    "value": json.dumps(payload),
                }
            ],
        },
    }


class CreateBugReportTests(unittest.TestCase):
    def setUp(self):
        self.table = FakeTable()
        create_bug_report._table = self.table

    def tearDown(self):
        create_bug_report._table = None

    def response_payload(self, response):
        body = response["response"]["functionResponse"]["responseBody"]
        return json.loads(body["TEXT"]["body"])

    def test_creates_open_ticket(self):
        response = create_bug_report.lambda_handler(event(VALID_PARAMETERS), None)

        self.assertEqual("1.0", response["messageVersion"])
        self.assertNotIn(
            "responseState", response["response"]["functionResponse"]
        )
        self.assertEqual(1, len(self.table.calls))
        item = self.table.calls[0]["Item"]
        self.assertIn("ticketId", item)
        self.assertEqual(VALID_PARAMETERS["description"], item["description"])
        self.assertEqual(
            VALID_PARAMETERS["stepsToReproduce"], item["stepsToReproduce"]
        )
        self.assertEqual(VALID_PARAMETERS["environment"], item["environment"])
        self.assertEqual("OPEN", item["status"])
        self.assertEqual("test-session-001", item["sessionId"])
        payload = self.response_payload(response)
        self.assertEqual(item["ticketId"], payload["ticketId"])
        self.assertEqual("OPEN", payload["status"])

    def test_missing_field_requests_reprompt_without_write(self):
        parameters = dict(VALID_PARAMETERS)
        parameters.pop("description")

        response = create_bug_report.lambda_handler(event(parameters), None)

        function_response = response["response"]["functionResponse"]
        self.assertEqual("REPROMPT", function_response["responseState"])
        self.assertIn("description", self.response_payload(response)["error"])
        self.assertEqual([], self.table.calls)

    def test_accepts_optional_fields_when_omitted(self):
        parameters = {"description": "The search page is blank."}

        response = create_bug_report.lambda_handler(event(parameters), None)

        self.assertNotIn(
            "responseState", response["response"]["functionResponse"]
        )
        item = self.table.calls[0]["Item"]
        self.assertNotIn("stepsToReproduce", item)
        self.assertNotIn("environment", item)

    def test_rejects_unknown_function(self):
        response = create_bug_report.lambda_handler(
            event(VALID_PARAMETERS, function="delete_ticket"), None
        )

        self.assertEqual(
            "FAILURE", response["response"]["functionResponse"]["responseState"]
        )
        self.assertEqual([], self.table.calls)

    def test_preserves_agent_session_attributes(self):
        response = create_bug_report.lambda_handler(event(VALID_PARAMETERS), None)

        self.assertEqual({"session": "kept"}, response["sessionAttributes"])
        self.assertEqual({"turn": "kept"}, response["promptSessionAttributes"])

    def test_flow_event_creates_ticket_and_returns_matching_ticket_id(self):
        response = create_bug_report.lambda_handler(
            flow_event(
                {
                    "status": "READY",
                    **VALID_PARAMETERS,
                }
            ),
            None,
        )

        self.assertEqual(1, len(self.table.calls))
        item = self.table.calls[0]["Item"]
        self.assertIn(item["ticketId"], response)
        self.assertIn("Bug report created successfully", response)
        self.assertIn("Status: OPEN", response)
        self.assertEqual("BEDROCK_FLOW", item["source"])
        self.assertEqual(VALID_PARAMETERS["description"], item["description"])
        self.assertEqual(
            VALID_PARAMETERS["stepsToReproduce"], item["stepsToReproduce"]
        )
        self.assertEqual(VALID_PARAMETERS["environment"], item["environment"])

    def test_incomplete_flow_event_asks_for_details_without_writing(self):
        response = create_bug_report.lambda_handler(
            flow_event(
                {
                    "status": "NEEDS_INFO",
                    "message": (
                        "Please provide the steps to reproduce and your browser, "
                        "operating system or device."
                    ),
                }
            ),
            None,
        )

        self.assertIn("steps to reproduce", response)
        self.assertIn("browser", response)
        self.assertEqual([], self.table.calls)

    def test_ready_flow_event_requires_all_three_bug_fields(self):
        response = create_bug_report.lambda_handler(
            flow_event(
                {
                    "status": "READY",
                    "description": VALID_PARAMETERS["description"],
                    "stepsToReproduce": "",
                    "environment": VALID_PARAMETERS["environment"],
                }
            ),
            None,
        )

        self.assertIn("steps to reproduce", response.lower())
        self.assertEqual([], self.table.calls)


if __name__ == "__main__":
    unittest.main()
