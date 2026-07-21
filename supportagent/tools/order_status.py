"""The V1 stub tool.

Canned data, on purpose. Its only job is to make the loop real: without a tool
the model would answer in one turn and the loop would never iterate. The honest
version that reaches a real system arrives with the tools video.
"""

from __future__ import annotations

from . import Tool

_CANNED = {
    "88213": "delivered 2026-07-19",
    "88320": "processing",
}


def get_order_status(order_id: str) -> str:
    return _CANNED.get(order_id, f"unknown order {order_id}")


order_status_tool = Tool(
    name="get_order_status",
    description="Return the delivery status for an order id.",
    fn=get_order_status,
    parameters={
        "type": "object",
        "properties": {
            "order_id": {"type": "string", "description": "The order id to look up."},
        },
        "required": ["order_id"],
    },
)
