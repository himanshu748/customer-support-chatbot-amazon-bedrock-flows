#!/usr/bin/env python3
"""Run a Bedrock Flow test suite and create judge-ready JSONL response data."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Tuple
from urllib.parse import urlparse

import boto3

from flow_runtime import input_request_text, invoke_flow_turn


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--flow-id", help="Bedrock Flow ID")
    parser.add_argument("--flow-alias-id", help="Bedrock Flow alias ID")
    parser.add_argument("--region", default="us-east-1", help="AWS Region")
    parser.add_argument(
        "--tests-json",
        "--tests",
        dest="tests_json",
        default="flow-tests.json",
        help="Input test suite JSON",
    )
    parser.add_argument(
        "--output", default="output_eval_dataset.jsonl", help="Output JSONL path"
    )
    parser.add_argument(
        "--model-identifier",
        default="my-flow-app",
        help="One stable source name for every precomputed response",
    )
    parser.add_argument("--s3-uri", help="Optional s3://bucket/key upload destination")
    parser.add_argument("--max-tests", type=int, help="Run only the first N tests")
    parser.add_argument(
        "--no-trace", action="store_true", help="Disable Flow trace requests"
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Validate the test file without calling AWS",
    )
    return parser.parse_args()


def load_test_suite(path: Path) -> Tuple[str, List[Dict[str, Any]]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    tests = payload.get("tests") if isinstance(payload, dict) else None
    if not isinstance(tests, list) or not tests:
        raise ValueError("The test file must contain a non-empty 'tests' array")
    flow_input = payload.get("flowInputNode", {})
    input_node_name = flow_input.get("nodeName")
    if not isinstance(input_node_name, str) or not input_node_name.strip():
        raise ValueError("flowInputNode.nodeName must name the Flow input node")

    seen = set()
    for index, case in enumerate(tests, start=1):
        if not isinstance(case, dict):
            raise ValueError(f"Test {index} must be an object")
        for required in ("id", "prompt", "expected"):
            if not isinstance(case.get(required), str) or not case[required].strip():
                raise ValueError(f"Test {index} has no valid '{required}'")
        if case["id"] in seen:
            raise ValueError(f"Duplicate test id: {case['id']}")
        seen.add(case["id"])
        follow_ups = case.get("follow_up_responses", [])
        if not isinstance(follow_ups, list) or not all(
            isinstance(value, str) and value.strip() for value in follow_ups
        ):
            raise ValueError(
                f"Test {case['id']} follow_up_responses must be an array of strings"
            )
    return input_node_name, tests


def run_case(
    client: Any,
    flow_id: str,
    flow_alias_id: str,
    case: Dict[str, Any],
    input_node_name: str,
    enable_trace: bool = True,
) -> Tuple[str, List[str]]:
    execution_id = None
    target_node = input_node_name
    next_text = case["prompt"]
    follow_ups = iter(case.get("follow_up_responses", []))
    transcript: List[str] = []
    traced_nodes: List[str] = []

    for _ in range(12):
        turn = invoke_flow_turn(
            client=client,
            flow_id=flow_id,
            flow_alias_id=flow_alias_id,
            text=next_text,
            execution_id=execution_id,
            target_node=target_node,
            enable_trace=enable_trace,
        )
        execution_id = turn.execution_id
        transcript.extend(f"Assistant: {output}" for output in turn.outputs)
        for trace_event in turn.traces:
            trace = trace_event.get("trace", {})
            for detail in trace.values():
                node_name = detail.get("nodeName") if isinstance(detail, dict) else None
                if node_name and node_name not in traced_nodes:
                    traced_nodes.append(node_name)

        if turn.input_request:
            request_text = input_request_text(turn.input_request)
            transcript.append(f"Assistant: {request_text}")
            try:
                next_text = next(follow_ups)
            except StopIteration as error:
                raise RuntimeError(
                    f"Test {case['id']} needs another follow_up_responses entry. "
                    f"The Agent asked: {request_text}"
                ) from error
            transcript.append(f"Customer: {next_text}")
            target_node = turn.input_request["nodeName"]
            continue

        if turn.completion_reason == "SUCCESS":
            break
        raise RuntimeError(
            f"Test {case['id']} ended with reason {turn.completion_reason!r}"
        )
    else:
        raise RuntimeError(f"Test {case['id']} exceeded 12 Flow turns")

    if not transcript:
        raise RuntimeError(f"Test {case['id']} returned no customer-visible response")
    return "\n".join(transcript), traced_nodes


def make_record(
    case: Dict[str, Any], response: str, model_identifier: str
) -> Dict[str, Any]:
    record = {
        "prompt": case["prompt"],
        "referenceResponse": case["expected"],
        "modelResponses": [
            {"response": response, "modelIdentifier": model_identifier}
        ],
    }
    if case.get("category"):
        record["category"] = case["category"]
    return record


def upload_file(path: Path, s3_uri: str, region: str = None) -> None:
    parsed = urlparse(s3_uri)
    if parsed.scheme != "s3" or not parsed.netloc or not parsed.path.lstrip("/"):
        raise ValueError("--s3-uri must include a bucket and object key")
    boto3.client("s3", region_name=region).upload_file(
        str(path), parsed.netloc, parsed.path.lstrip("/")
    )


def main() -> int:
    args = parse_args()
    input_node_name, tests = load_test_suite(Path(args.tests_json))
    if args.max_tests is not None:
        if args.max_tests < 1:
            raise ValueError("--max-tests must be at least 1")
        tests = tests[: args.max_tests]

    if args.validate_only:
        print(
            f"Validated {len(tests)} tests in {args.tests_json} "
            f"for input node {input_node_name}"
        )
        return 0
    if not args.flow_id or not args.flow_alias_id:
        raise ValueError("--flow-id and --flow-alias-id are required unless validating")

    client = boto3.client("bedrock-agent-runtime", region_name=args.region)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as output_file:
        for position, case in enumerate(tests, start=1):
            try:
                response, traced_nodes = run_case(
                    client,
                    args.flow_id,
                    args.flow_alias_id,
                    case,
                    input_node_name=input_node_name,
                    enable_trace=not args.no_trace,
                )
                trace_suffix = (
                    " -> ".join(traced_nodes) if traced_nodes else "no node trace"
                )
                print(
                    f"[{position}/{len(tests)}] {case['id']}: complete "
                    f"({trace_suffix})"
                )
            except Exception as error:
                response = f"[FLOW_ERROR] {type(error).__name__}: {error}"
                print(f"[{position}/{len(tests)}] {case['id']}: {response}")
            output_file.write(
                json.dumps(
                    make_record(case, response, args.model_identifier),
                    ensure_ascii=False,
                )
                + "\n"
            )

    print(f"Wrote {len(tests)} records to {output_path}")
    if args.s3_uri:
        upload_file(output_path, args.s3_uri, args.region)
        print(f"Uploaded dataset to {args.s3_uri}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
