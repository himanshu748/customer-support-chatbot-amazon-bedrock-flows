# Live Flow verification

Run date: August 21, 2026

Region: `us-east-1`

Published Flow version: `5`

Alias: `live`

Automated cases: `10`

Flow invocation errors: `0`

## Deployed bug path

The deployed Flow definition contains this exact path:

`FlowInput -> ClassifyRequest -> RouteRequest -> BugReportAssistant -> CreateBugReport -> BugOutput`

`CreateBugReport` is a `LambdaFunction` Flow node. The live alias routes to Flow
version 5.

## Flow-created ticket proof

Input sent to the deployed Flow:

> Please file a bug. Description: checkout freezes after pressing Continue.
> Steps: add a blue mug, open checkout, press Continue. Environment: Chrome 128
> on macOS Sonoma.

Flow response:

> Bug report created successfully. Ticket ID:
> `e73694db-d71d-4ef5-a47f-e695ad5c4156`. Status: OPEN. Description: checkout
> freezes after pressing Continue. Steps to reproduce: add a blue mug, open
> checkout, press Continue. Environment: Chrome 128 on macOS Sonoma.

The `BugReports` item queried by that exact ticket ID contains:

| Attribute | Value |
| --- | --- |
| `ticketId` | `e73694db-d71d-4ef5-a47f-e695ad5c4156` |
| `createdAt` | `2026-08-21T13:50:26.871829Z` |
| `status` | `OPEN` |
| `description` | `checkout freezes after pressing Continue` |
| `stepsToReproduce` | `add a blue mug, open checkout, press Continue` |
| `environment` | `Chrome 128 on macOS Sonoma` |
| `source` | `BEDROCK_FLOW` |

## Follow-up proof

Input:

> The checkout button freezes every time I press it. I want to report this bug.

Response:

> Please provide steps to reproduce the problem and environment information
> such as browser, operating system or device.

No ticket is claimed when the required details are incomplete.

## FAQ and other-path proof

| Route | Input | Live Flow response |
| --- | --- | --- |
| Covered FAQ | Where can I track my order? | You can track your order in your Account > Orders > Track shipment. Tracking updates can take up to 24 hours after dispatch. |
| Uncovered FAQ | Do you offer gift wrapping for orders? | I do not have that information. Please call our support at +1-800-555-0147 for more details. |
| Other request | Can you help me write a résumé for a software job? | The request is declined and redirected to +1-800-555-0147, Monday to Friday, 9 AM to 6 PM Eastern Time. |

The complete model responses are preserved in
[`output_eval_dataset.jsonl`](output_eval_dataset.jsonl). The traced node sequence
for every case is preserved in [`eval-run.log`](eval-run.log).
