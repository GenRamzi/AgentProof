# Contributing to AgentProof

AgentProof is an independent verification project. Contributions should preserve the principle **evidence first; AI reasoning second** and should work for AI-written, human-written, and mixed pull requests.

## Development

Install the package and test dependencies, then run `python -m pytest -q`. Every new verification rule should have a stable AP rule ID, unit tests, an adversarial fixture, and an explanation available through `agentproof explain APxxx`.

## Adding rules

Rules must report neutral evidence rather than accuse an author of malicious intent. A rule should include the changed file, line when available, a concise message, and a reproducible evidence sample. False positives belong in the regression suite so improvements do not remove prior detection.

## Adding adapters

Adapters should detect only the canonical command and parse evidence conservatively. If multiple commands are plausible, the CLI must ask the user to configure the canonical suite instead of silently choosing a narrower command.

## Pull requests

Describe the evidence model, the expected verdict, policy implications, and fixture coverage. Do not add secrets, privileged workflow events, or network-dependent tests. Changes to the runner security model require a corresponding update to `SECURITY.md` and a threat-model review.
