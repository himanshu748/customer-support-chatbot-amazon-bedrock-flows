# Reviewer remediation

This revision follows the guidance supplied after submission attempt 1 on
August 21, 2026.

## Feedback addressed

| Reviewer guidance | Revision |
| --- | --- |
| Use `us-east-1` | All deployment, invocation and evaluation commands use `us-east-1`. |
| Replace the unavailable Agent node with a Prompt node | `BugReportAssistant` is a Prompt node that collects description, reproduction steps and environment details. |
| Keep the Lambda implementation or test it separately | `cloudformation-tool.yaml` deploys `create-bug-report` and `BugReports`; `lambda-test-event.json` provides the console test. |
| Keep the classifier, Condition node, Input node and three Output nodes | `cloudformation-solution.yaml` declares `FlowInput`, `ClassifyRequest`, `RouteRequest`, `BugOutput`, `FAQOutput` and `HumanOutput`. |
| Feed the original input into each prompt handler | Direct data connections pass `FlowInput.document` to `BugReportAssistant.report`, `AnswerFAQ.question` and `RedirectHuman.request`. |
| Test the Flow from the console | `flow-tests.json` contains ten prompts across all routes and `generate-eval-dataset.py` invokes the deployed alias with trace enabled. |
| Run an LLM-as-a-judge evaluation | `cloudformation-testing.yaml` deploys the evaluation bucket and role; the README contains the evaluation job command. |

## Intentional Agent exception

Amazon Bedrock Agents Classic is closed to new AWS accounts. Udacity Support
ticket `#2203410` instructed learners to use AgentCore, but AgentCore cannot be
connected to a Bedrock Flow Agent node. The reviewer therefore approved the
Prompt-node bug-handler replacement used in this revision.

The Prompt node never claims that it created a database ticket. The Lambda and
DynamoDB test provide separate evidence that the original bug-report persistence
logic works.

## Evidence checklist

- Full Flow diagram showing one Input node, classifier Prompt, Condition node,
  three handler Prompts and three distinct Output nodes.
- Classifier Prompt configuration.
- Condition expressions for `BUG`, `PLATFORM` and the default route.
- Bug handler Prompt configuration and Flow test responses for complete and
  incomplete bug reports.
- Lambda test response plus the matching `BugReports` table item.
- FAQ Prompt configuration plus covered, uncovered and other-route test responses.
- `flow-tests.json`, generated JSONL, S3 object, evaluation job and correctness
  score.
