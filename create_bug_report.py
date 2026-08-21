"""Create bug reports from Bedrock Flow Lambda nodes or Agent action groups."""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Iterable

import boto3


SUPPORTED_FIELDS = ("description", "stepsToReproduce", "environment")
MAX_LENGTHS = {
    "description": 4000,
    "stepsToReproduce": 4000,
    "environment": 1000,
}

_table = None


def _get_table():
    global _table
    if _table is None:
        table_name = os.environ.get("BUG_REPORT_TABLE")
        if not table_name:
            raise RuntimeError("BUG_REPORT_TABLE is not configured")
        _table = boto3.resource("dynamodb").Table(table_name)
    return _table


def _normalise_parameters(parameters: Iterable[Dict[str, Any]]) -> Dict[str, str]:
    values: Dict[str, str] = {}
    for parameter in parameters or []:
        name = str(parameter.get("name", "")).strip()
        if not name:
            continue
        value = parameter.get("value", "")
        values[name] = str(value).strip()
    return values


def _validate(parameters: Dict[str, str]) -> Dict[str, str]:
    if not parameters.get("description", "").strip():
        raise ValueError("Missing required field: description")

    cleaned = {
        field: parameters.get(field, "").strip() for field in SUPPORTED_FIELDS
    }

    for field, maximum in MAX_LENGTHS.items():
        if len(cleaned[field]) > maximum:
            raise ValueError(f"{field} must not exceed {maximum} characters")

    return cleaned


def _flow_inputs(event: Dict[str, Any]) -> Dict[str, Any]:
    """Return the named inputs supplied by a Bedrock Flow Lambda node."""
    return {
        str(item.get("name", "")).strip(): item.get("value")
        for item in event.get("node", {}).get("inputs", [])
        if item.get("name")
    }


def _parse_flow_payload(value: Any) -> Dict[str, Any]:
    """Parse the prompt node's strict JSON response defensively."""
    if not isinstance(value, str):
        raise ValueError("The bug intake response was not text.")
    candidate = value.strip()
    if candidate.startswith("```"):
        lines = candidate.splitlines()
        lines = lines[1:] if lines else lines
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        candidate = "\n".join(lines).strip()
    try:
        payload = json.loads(candidate)
    except json.JSONDecodeError as error:
        raise ValueError("The bug intake response was not valid JSON.") from error
    if not isinstance(payload, dict):
        raise ValueError("The bug intake response must be a JSON object.")
    return payload


def _create_item(
    fields: Dict[str, str],
    *,
    source: str,
    session_id: str | None = None,
    flow_arn: str | None = None,
) -> Dict[str, str]:
    ticket_id = str(uuid.uuid4())
    item = {
        "ticketId": ticket_id,
        "createdAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": "OPEN",
        "description": fields["description"],
        "source": source,
    }
    for field in ("stepsToReproduce", "environment"):
        if fields.get(field):
            item[field] = fields[field]
    if session_id:
        item["sessionId"] = session_id
    if flow_arn:
        item["flowArn"] = flow_arn
    _get_table().put_item(
        Item=item,
        ConditionExpression="attribute_not_exists(ticketId)",
    )
    return item


def _handle_flow_event(event: Dict[str, Any]) -> str:
    inputs = _flow_inputs(event)
    payload = _parse_flow_payload(inputs.get("bugReport"))
    status = str(payload.get("status", "")).strip().upper()
    if status == "NEEDS_INFO":
        message = str(payload.get("message", "")).strip()
        return message or (
            "Please provide a description, steps to reproduce and environment "
            "information such as your browser, operating system or device."
        )
    if status != "READY":
        return "I could not validate the bug report details. Please try again."

    fields = {
        field: str(payload.get(field, "")).strip() for field in SUPPORTED_FIELDS
    }
    missing = [field for field in SUPPORTED_FIELDS if not fields[field]]
    if missing:
        labels = {
            "description": "a clear description",
            "stepsToReproduce": "steps to reproduce",
            "environment": "browser, operating system or device information",
        }
        return "Please provide " + ", ".join(labels[field] for field in missing) + "."

    fields = _validate(fields)
    flow = event.get("flow", {})
    item = _create_item(
        fields,
        source="BEDROCK_FLOW",
        flow_arn=str(flow.get("flowArn", "")).strip() or None,
    )
    return (
        "Bug report created successfully. "
        f"Ticket ID: {item['ticketId']}. Status: OPEN. "
        f"Description: {item['description']} "
        f"Steps to reproduce: {item['stepsToReproduce']} "
        f"Environment: {item['environment']}"
    )


def _response(event: Dict[str, Any], body: Dict[str, Any], state: str | None = None):
    function_response: Dict[str, Any] = {
        "responseBody": {"TEXT": {"body": json.dumps(body, separators=(",", ":"))}}
    }
    if state:
        function_response["responseState"] = state

    return {
        "messageVersion": "1.0",
        "response": {
            "actionGroup": event.get("actionGroup", "bug-report-actions"),
            "function": event.get("function", "create_bug_report"),
            "functionResponse": function_response,
        },
        "sessionAttributes": event.get("sessionAttributes", {}),
        "promptSessionAttributes": event.get("promptSessionAttributes", {}),
    }


def lambda_handler(event: Dict[str, Any], context: Any):
    """Validate a Bedrock Flow or Agent event and create one support ticket."""
    if event.get("messageVersion") != "1.0":
        return _response(event, {"error": "Unsupported message version"}, "FAILURE")
    if event.get("flow") and event.get("node"):
        try:
            return _handle_flow_event(event)
        except ValueError as error:
            return f"I could not validate the bug report: {error}"
        except Exception:
            return "The ticket service is temporarily unavailable. Please try again later."
    if event.get("function") != "create_bug_report":
        return _response(event, {"error": "Unsupported function"}, "FAILURE")

    try:
        fields = _validate(_normalise_parameters(event.get("parameters", [])))
        item = _create_item(
            fields,
            source="BEDROCK_AGENT",
            session_id=str(event.get("sessionId", "")).strip() or None,
        )
        return _response(
            event,
            {
                "ticketId": item["ticketId"],
                "status": "OPEN",
                "message": "Bug report created successfully.",
            },
        )
    except ValueError as error:
        return _response(event, {"error": str(error)}, "REPROMPT")
    except Exception:
        # Do not expose internal exception details to the model or customer.
        return _response(
            event,
            {"error": "The ticket service is temporarily unavailable."},
            "FAILURE",
        )
