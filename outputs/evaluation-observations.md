# Evaluation observations

Run date: August 21, 2026  
Region: `us-east-1`  
Published Flow version: 4  
Test cases: 10  
Flow invocation errors: 0

## Automated test observations

- All three bug prompts reached `BugReportAssistant` and `BugOutput`.
- The complete bug report used the supplied Safari 18 and iPhone 16 environment without requesting an unnecessary operating system field.
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

The perfect normalized score confirms that the generated responses matched the reference expectations across bug intake, FAQ answers, fallback behavior and routing edge cases.
