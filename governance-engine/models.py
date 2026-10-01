from pydantic import BaseModel
from typing import Dict, Any

class CheckRunRequest(BaseModel):
    pr_event: Dict[str, Any]
    code_diff: str

    