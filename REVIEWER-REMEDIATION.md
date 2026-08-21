# Reviewer remediation

This revision follows the guidance supplied after submission attempts 1 and 2
on August 21, 2026.

## Feedback addressed

| Reviewer guidance | Revision |
| --- | --- |
| Use `us-east-1` | All deployment, invocation and evaluation commands use `us-east-1`. |
| Replace the unavailable Agent node with a Prompt node | `BugReportAssistant` is a Prompt node that collects description, reproduction steps and environment details. |
| Connect ticket persistence to the Flow | Flow version 5 adds the `CreateBugReport` `LambdaFunction` node between `BugReportAssistant` and `BugOutput`. |
| Keep the classifier, Condition node, Input node and three Output nodes | `cloudformation-solution.yaml` declares `FlowInput`, `ClassifyRequest`, `RouteRequest`, `BugOutput`, `FAQOutput` and `HumanOutput`. |
| Feed the original input into each prompt handler | Direct data connections pass `FlowInput.document` to `BugReportAssistant.report`, `AnswerFAQ.question` and `RedirectHuman.request`. |
| Test the Flow from the console | `flow-tests.json` contains ten prompts across all routes and `generate-eval-dataset.py` invokes the deployed alias with trace enabled. |
| Run an LLM-as-a-judge evaluation | `cloudformation-testing.yaml` deploys the evaluation bucket and role; the README contains the evaluation job command. |

## Attempt 2 fixes

| Reviewer request | Verified fix |
| --- | --- |
| Show a successful Flow test that creates a ticket and returns confirmation or a ticket ID | The live Flow returned `Bug report created successfully`, an `OPEN` status and ticket ID `e73694db-d71d-4ef5-a47f-e695ad5c4156`. See [`14-bug-flow-ticket-created.png`](outputs/evidence/14-bug-flow-ticket-created.png). |
| Show the matching `BugReports` item created by that Flow run | A read by the same ticket ID returned the preserved description, reproduction steps, environment, `OPEN` status and `BEDROCK_FLOW` source. See [`15-dynamodb-matching-flow-ticket.png`](outputs/evidence/15-dynamodb-matching-flow-ticket.png). |
| Add readable FAQ Prompt, covered FAQ, uncovered FAQ and other-request evidence | See [`16-faq-prompt-readable.png`](outputs/evidence/16-faq-prompt-readable.png), [`17-faq-covered-readable.png`](outputs/evidence/17-faq-covered-readable.png), [`18-faq-uncovered-readable.png`](outputs/evidence/18-faq-uncovered-readable.png) and [`19-other-request-readable.png`](outputs/evidence/19-other-request-readable.png). |

## Intentional Agent exception

Amazon Bedrock Agents Classic is closed to new AWS accounts. Udacity Support
ticket `#2203410` instructed learners to use AgentCore, but AgentCore cannot be
connected to a Bedrock Flow Agent node. The reviewer therefore approved the
Prompt-node bug-handler replacement used in this revision.

The Prompt node emits strict JSON. The native Flow Lambda node validates that
JSON, writes complete reports to `BugReports` and returns the generated ticket
ID to `BugOutput`. Incomplete reports return a targeted follow-up without a
database write.

## Evidence checklist

- Full Flow diagram showing one Input node, classifier Prompt, Condition node,
  three handler Prompts, the Lambda node and three distinct Output nodes.
- Classifier Prompt configuration.
- Condition expressions for `BUG`, `PLATFORM` and the default route.
- Bug handler Prompt configuration and Flow test responses for complete and
  incomplete bug reports.
- Live Flow ticket response plus the matching `BugReports` table item.
- FAQ Prompt configuration plus covered, uncovered and other-route test responses.
- `flow-tests.json`, generated JSONL, S3 object, evaluation job and correctness
  score.
