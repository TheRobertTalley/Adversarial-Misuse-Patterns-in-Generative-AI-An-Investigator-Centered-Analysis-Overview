#!/usr/bin/env python3
"""
Transparent rule based trajectory scorer.

Input format: JSONL with objects like:
{"role":"user","content":"text here"}
{"role":"assistant","content":"text here"}

Output: total score and a list of fired rules with evidence.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml


@dataclass
class Message:
    role: str
    content: str


@dataclass
class FiredRule:
    rule_id: str
    name: str
    points: int
    message_index: int
    evidence: str


def _load_jsonl(path: Path) -> List[Message]:
    msgs: List[Message] = []
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            role = str(obj.get("role", "")).strip().lower()
            content = str(obj.get("content", "")).strip()
            if role not in {"user", "assistant"}:
                raise ValueError(f"Invalid role at line {line_no}: {role!r}")
            msgs.append(Message(role=role, content=content))
    return msgs


def _compile_patterns(patterns: List[str]) -> List[re.Pattern]:
    return [re.compile(p) for p in patterns]


def _clamp(n: int, lo: int = 0, hi: int = 100) -> int:
    return max(lo, min(hi, n))


def score_conversation(
    messages: List[Message],
    ruleset: Dict[str, Any],
) -> Tuple[int, List[FiredRule]]:
    rules = ruleset.get("rules", [])
    compiled: Dict[str, Dict[str, Any]] = {}

    for r in rules:
        rid = r["id"]
        compiled[rid] = {
            "id": rid,
            "name": r.get("name", rid),
            "points": int(r.get("points", 0)),
            "applies_to": r.get("applies_to", "user"),
            "patterns": _compile_patterns(r.get("patterns", [])),
            "depends_on": r.get("depends_on"),
            "window_turns": int(r.get("window_turns", 0)),
        }

    fired: List[FiredRule] = []
    fired_by_id: Dict[str, List[int]] = {}

    # Pass 1: basic pattern rules (no depends_on)
    for i, m in enumerate(messages):
        for rid, r in compiled.items():
            if r["depends_on"]:
                continue
            if m.role != r["applies_to"]:
                continue
            for pat in r["patterns"]:
                match = pat.search(m.content)
                if match:
                    points = r["points"]
                    fired.append(
                        FiredRule(
                            rule_id=rid,
                            name=r["name"],
                            points=points,
                            message_index=i,
                            evidence=match.group(0)[:180],
                        )
                    )
                    fired_by_id.setdefault(rid, []).append(i)
                    break

    # Pass 2: dependent rules (example: adaptive follow up after friction)
    for rid, r in compiled.items():
        dep = r["depends_on"]
        if not dep:
            continue
        dep_hits = fired_by_id.get(dep, [])
        if not dep_hits:
            continue

        window = r["window_turns"]
        for dep_i in dep_hits:
            for j in range(dep_i + 1, min(dep_i + 1 + window + 1, len(messages))):
                m = messages[j]
                if m.role != r["applies_to"]:
                    continue
                for pat in r["patterns"]:
                    match = pat.search(m.content)
                    if match:
                        fired.append(
                            FiredRule(
                                rule_id=rid,
                                name=r["name"],
                                points=r["points"],
                                message_index=j,
                                evidence=match.group(0)[:180],
                            )
                        )
                        fired_by_id.setdefault(rid, []).append(j)
                        break
                else:
                    continue
                break

    total = sum(fr.points for fr in fired)
    total = _clamp(total, 0, 100)
    # Stable ordering for readability
    fired.sort(key=lambda x: (x.message_index, x.rule_id))
    return total, fired


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="Path to conversation JSONL")
    ap.add_argument("--rules", required=True, help="Path to ruleset YAML")
    args = ap.parse_args()

    inp = Path(args.input)
    rules_path = Path(args.rules)

    messages = _load_jsonl(inp)
    ruleset = yaml.safe_load(rules_path.read_text(encoding="utf-8"))

    total, fired = score_conversation(messages, ruleset)

    print(f"Total risk score: {total}/100")
    print("")
    if not fired:
        print("No rules fired.")
        return 0

    print("Fired rules:")
    for fr in fired:
        msg = messages[fr.message_index]
        snippet = msg.content.replace("\n", " ")
        snippet = snippet[:160] + ("..." if len(snippet) > 160 else "")
        print(
            f"- [{fr.rule_id}] +{fr.points} on msg {fr.message_index} ({msg.role}): {fr.name}\n"
            f"  evidence: {fr.evidence!r}\n"
            f"  snippet: {snippet}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
