"""Amazon Bedrock Agent action for creating a bug report in DynamoDB."""

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
    """Validate an Agent function-details event and create one support ticket."""
    if event.get("messageVersion") != "1.0":
        return _response(event, {"error": "Unsupported message version"}, "FAILURE")
    if event.get("function") != "create_bug_report":
        return _response(event, {"error": "Unsupported function"}, "FAILURE")

    try:
        fields = _validate(_normalise_parameters(event.get("parameters", [])))
        ticket_id = str(uuid.uuid4())
        created_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        item = {
            "ticketId": ticket_id,
            "createdAt": created_at,
            "status": "OPEN",
            "description": fields["description"],
        }
        if fields["stepsToReproduce"]:
            item["stepsToReproduce"] = fields["stepsToReproduce"]
        if fields["environment"]:
            item["environment"] = fields["environment"]
        if event.get("sessionId"):
            item["sessionId"] = str(event["sessionId"])
        _get_table().put_item(
            Item=item,
            ConditionExpression="attribute_not_exists(ticketId)",
        )
        return _response(
            event,
            {
                "ticketId": ticket_id,
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
