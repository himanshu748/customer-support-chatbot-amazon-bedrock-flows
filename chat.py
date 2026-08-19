#!/usr/bin/env python3
"""Small terminal client for a deployed customer support Bedrock Flow."""

import argparse

import boto3

from flow_runtime import input_request_text, invoke_flow_turn


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--flow-id", required=True)
    parser.add_argument("--flow-alias-id", required=True)
    parser.add_argument("--region")
    parser.add_argument("--trace", action="store_true")
    args = parser.parse_args()

    client = boto3.client("bedrock-agent-runtime", region_name=args.region)
    print("Northstar Shop support. Press Ctrl+C to exit.")

    while True:
        try:
            text = input("You: ").strip()
            if not text:
                continue
            execution_id = None
            target_node = "FlowInput"

            while True:
                result = invoke_flow_turn(
                    client,
                    args.flow_id,
                    args.flow_alias_id,
                    text,
                    execution_id=execution_id,
                    target_node=target_node,
                    enable_trace=args.trace,
                )
                execution_id = result.execution_id
                for output in result.outputs:
                    print(f"Support: {output}")
                if result.input_request:
                    print(f"Support: {input_request_text(result.input_request)}")
                    text = input("You: ").strip()
                    target_node = result.input_request["nodeName"]
                    continue
                break
        except (EOFError, KeyboardInterrupt):
            print()
            return 0


if __name__ == "__main__":
    raise SystemExit(main())
