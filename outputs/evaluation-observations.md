# Evaluation observations

Run date: August 21, 2026

Region: `us-east-1`

Published Flow version: 5

Test cases: 10

Flow invocation errors: 0

## Automated test observations

- All three bug prompts reached `BugReportAssistant`, `CreateBugReport` and `BugOutput`.
- The complete bug report used the supplied Safari 18 and iPhone 16 environment, created an `OPEN` ticket and returned its ticket ID.
- Both incomplete bug reports asked for explicit reproduction steps and environment information without claiming a ticket ID.
- All five platform prompts reached `AnswerFAQ` and `FAQOutput`.
- Covered FAQ answers included required return exclusions, account-ownership verification and the international-shipping restriction.
- The uncovered gift-wrapping question used the support phone fallback instead of inventing a policy.
- Both other-request prompts reached `RedirectHuman` and `HumanOutput`.
- Both prompt-injection cases resisted the embedded instruction and stayed within the correct route.

## Judge result

The Amazon Bedrock LLM-as-a-judge job completed successfully using Amazon Nova Pro as the evaluator and `my-flow-app` as the precomputed inference source.

- Metric: Correctness
- Normalized average score: **1.00**
- Prompts evaluated: 10
- Job status: Completed
- Failure messages: None
- Evidence: [`12-evaluation-results.jpg`](evidence/12-evaluation-results.jpg)

The completed judge result scored the original submitted dataset. After the
reviewer-requested persistence fix, the version 5 dataset was regenerated with
the same ten prompts and zero Flow errors. The new live regression evidence is
recorded in [`live-flow-verification.md`](live-flow-verification.md).
