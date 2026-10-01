from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

from azure.core.exceptions import ResourceExistsError
from azure.storage.queue import QueueClient


@dataclass
class QueueMessage:
    job_id: str
    payload: dict[str, Any]

    def to_json(self) -> str:
        return json.dumps({"job_id": self.job_id, "payload": self.payload}, ensure_ascii=False)

    @staticmethod
    def from_json(raw: str) -> "QueueMessage":
        data = json.loads(raw)
        return QueueMessage(job_id=str(data["job_id"]), payload=dict(data["payload"]))


class AzureJobQueue:
    def __init__(self, conn: str, queue_name: str) -> None:
        self.client = QueueClient.from_connection_string(conn_str=conn, queue_name=queue_name)
        try:
            self.client.create_queue()
        except ResourceExistsError:
            pass

    def enqueue(self, msg: QueueMessage) -> None:
        self.client.send_message(msg.to_json())

    def receive_batch(self, max_messages: int = 1, visibility_timeout: int = 1800):
        pager = self.client.receive_messages(messages_per_page=max_messages, visibility_timeout=visibility_timeout)
        return list(pager)

    def delete(self, msg) -> None:
        self.client.delete_message(msg.id, msg.pop_receipt)


def create_job_queue() -> AzureJobQueue | None:
    conn = os.getenv("BLOB_CONNECTION_STRING", "").strip()
    name = os.getenv("JOB_QUEUE_NAME", "").strip()
    if not conn or not name:
        return None
    return AzureJobQueue(conn=conn, queue_name=name)
