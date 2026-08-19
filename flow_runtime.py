"""Helpers for invoking Amazon Bedrock Flows, including multi-turn Agent nodes."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional


@dataclass
class FlowTurnResult:
    execution_id: str
    completion_reason: Optional[str] = None
    outputs: List[str] = field(default_factory=list)
    input_request: Optional[Dict[str, Any]] = None
    traces: List[Dict[str, Any]] = field(default_factory=list)


def _document_text(content: Dict[str, Any]) -> str:
    document = content.get("document", "")
    return document if isinstance(document, str) else str(document)


def parse_response_stream(
    execution_id: str,
    response_stream: Iterable[Dict[str, Any]],
) -> FlowTurnResult:
    result = FlowTurnResult(execution_id=execution_id)
    for event in response_stream:
        if "flowOutputEvent" in event:
            result.outputs.append(
                _document_text(event["flowOutputEvent"].get("content", {}))
            )
        elif "flowMultiTurnInputRequestEvent" in event:
            result.input_request = event["flowMultiTurnInputRequestEvent"]
        elif "flowCompletionEvent" in event:
            result.completion_reason = event["flowCompletionEvent"].get(
                "completionReason"
            )
        elif "flowTraceEvent" in event:
            result.traces.append(event["flowTraceEvent"])
    return result


def invoke_flow_turn(
    client: Any,
    flow_id: str,
    flow_alias_id: str,
    text: str,
    execution_id: Optional[str] = None,
    target_node: str = "FlowInput",
    enable_trace: bool = False,
) -> FlowTurnResult:
    flow_input: Dict[str, Any] = {
        "content": {"document": text},
        "nodeName": target_node,
    }
    if execution_id:
        flow_input["nodeInputName"] = "agentInputText"
    else:
        flow_input["nodeOutputName"] = "document"

    request: Dict[str, Any] = {
        "flowIdentifier": flow_id,
        "flowAliasIdentifier": flow_alias_id,
        "inputs": [flow_input],
        "enableTrace": enable_trace,
    }
    if execution_id:
        request["executionId"] = execution_id

    response = client.invoke_flow(**request)
    return parse_response_stream(response["executionId"], response["responseStream"])


def input_request_text(input_request: Dict[str, Any]) -> str:
    return _document_text(input_request.get("content", {}))
