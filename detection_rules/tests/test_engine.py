from pathlib import Path
import yaml

from detection_rules.engine import _load_jsonl, score_conversation


def test_ruleset_scores_safe_example_high():
    base = Path(__file__).resolve().parents[1]
    convo = base / "examples" / "conversation_safe.jsonl"
    rules = base / "ruleset_v1.yml"

    messages = _load_jsonl(convo)
    ruleset = yaml.safe_load(rules.read_text(encoding="utf-8"))

    total, fired = score_conversation(messages, ruleset)

    # Expect multiple trajectory signals and a non trivial score
    assert total >= 40

    fired_ids = {f.rule_id for f in fired}

    # Turning point signal, plus adaptive follow up after friction
    assert ("R001" in fired_ids) or ("R003" in fired_ids)
    assert "R011" in fired_ids
