# Bedrock Evaluation Observations

Complete this document after the evaluation job reaches `Completed`.

## Run details

- Evaluation job:
- Run date:
- Flow version and alias:
- Test count:
- Evaluator model: `amazon.nova-pro-v1:0`
- Metric: `Builtin.Correctness`
- Overall correctness score:

## Results by route

| Route | Tests | Average score | Misrouted prompts | Notes |
| --- | ---: | ---: | --- | --- |
| Bug report |  |  |  |  |
| Platform FAQ |  |  |  |  |
| Other request |  |  |  |  |

## Observations

### Classification and routing

- Which prompts reached the expected output node?
- Did the bug route win when a report also mentioned a platform topic?
- Did any short, ambiguous or adversarial prompt get misrouted?

### Bug report path

- Did the Agent ask only for useful missing details?
- Did each successful conversation create exactly one DynamoDB item?
- Did every success response include the ticket ID and `OPEN` status?

### Platform FAQ path

- Were answers grounded in the embedded FAQ?
- Did unsupported questions redirect to the support phone number?
- Did any response add a policy or fact that is not in the FAQ?

### Other request path

- Were redirects polite and concise?
- Did responses include the correct phone number and hours?
- Did prompt injection attempts avoid revealing instructions or completing the unrelated request?

## Follow-up changes

Record each proposed change, the evidence behind it and the tests that should verify it.

| Priority | Change | Evidence | Verification test |
| --- | --- | --- | --- |
|  |  |  |  |
