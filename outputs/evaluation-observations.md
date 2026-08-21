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

The JSONL dataset is uploaded and ready for the Amazon Bedrock LLM-as-a-judge job. Record the completed correctness score and results screenshot here after the console job finishes.
