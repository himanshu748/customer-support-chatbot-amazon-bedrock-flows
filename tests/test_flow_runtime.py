import unittest

from flow_runtime import input_request_text, invoke_flow_turn, parse_response_stream


class FakeClient:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def invoke_flow(self, **kwargs):
        self.calls.append(kwargs)
        return self.response


class FlowRuntimeTests(unittest.TestCase):
    def test_parses_output_completion_and_trace(self):
        result = parse_response_stream(
            "execution-1",
            [
                {
                    "flowOutputEvent": {
                        "content": {"document": "answer"},
                        "nodeName": "FAQOutput",
                    }
                },
                {"flowTraceEvent": {"trace": {"conditionNodeResultTrace": {}}}},
                {"flowCompletionEvent": {"completionReason": "SUCCESS"}},
            ],
        )

        self.assertEqual(["answer"], result.outputs)
        self.assertEqual("SUCCESS", result.completion_reason)
        self.assertEqual(1, len(result.traces))

    def test_initial_invocation_targets_flow_input_output(self):
        client = FakeClient(
            {
                "executionId": "execution-1",
                "responseStream": [
                    {"flowCompletionEvent": {"completionReason": "SUCCESS"}}
                ],
            }
        )

        invoke_flow_turn(client, "flow-id", "alias-id", "hello")

        flow_input = client.calls[0]["inputs"][0]
        self.assertEqual("FlowInput", flow_input["nodeName"])
        self.assertEqual("document", flow_input["nodeOutputName"])
        self.assertNotIn("executionId", client.calls[0])

    def test_resume_invocation_targets_agent_input(self):
        client = FakeClient(
            {
                "executionId": "execution-1",
                "responseStream": [
                    {"flowCompletionEvent": {"completionReason": "SUCCESS"}}
                ],
            }
        )

        invoke_flow_turn(
            client,
            "flow-id",
            "alias-id",
            "my email is me@example.com",
            execution_id="execution-1",
            target_node="BugAgent",
        )

        call = client.calls[0]
        self.assertEqual("execution-1", call["executionId"])
        self.assertEqual("agentInputText", call["inputs"][0]["nodeInputName"])
        self.assertNotIn("nodeOutputName", call["inputs"][0])

    def test_reads_multi_turn_request(self):
        result = parse_response_stream(
            "execution-1",
            [
                {
                    "flowMultiTurnInputRequestEvent": {
                        "nodeName": "BugAgent",
                        "nodeType": "AgentNode",
                        "content": {"document": "What is your email?"},
                    }
                },
                {"flowCompletionEvent": {"completionReason": "INPUT_REQUIRED"}},
            ],
        )

        self.assertEqual("INPUT_REQUIRED", result.completion_reason)
        self.assertEqual("What is your email?", input_request_text(result.input_request))


if __name__ == "__main__":
    unittest.main()
