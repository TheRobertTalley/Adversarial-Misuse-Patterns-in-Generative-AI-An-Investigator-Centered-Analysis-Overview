# Detection rules (optional)

This folder provides a small, transparent, rule based scoring engine for conversation risk signals.

Goals
- Make trajectory signals reproducible
- Support analyst training and consistent documentation
- Provide a testable playground for false positive and false negative tradeoffs

Non goals
- Production enforcement logic
- Automated bans
- Replacing analyst judgment
- Sharing abuse playbooks

How it works
- Input: a conversation as JSON lines (one message per line)
- Rules: YAML rules that score specific behavioral signals
- Output: a scored report that lists which rules fired and why

Run locally
- Python 3.11+
- pip install -r detection_rules/requirements.txt
- python detection_rules/engine.py --input detection_rules/examples/conversation_safe.jsonl --rules detection_rules/ruleset_v1.yml
