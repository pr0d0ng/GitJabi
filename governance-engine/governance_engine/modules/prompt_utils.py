
from typing import Optional

def dict_to_prompt_yaml(
        data: dict, indent=0, ignored_cols: Optional[list[str]]=None) -> str:
    """
    JSON의 특수문자를 제거하고 들여쓰기로 구조를 표현하여 토큰을 절약합니다.
    """
    lines = []
    for key, value in data.items():
        if ignored_cols and key in ignored_cols:
            continue
        prefix = "  " * indent
        if isinstance(value, dict):
            lines.append(f"{prefix}{key}:")
            lines.append(dict_to_prompt_yaml(value, indent + 1))
        elif isinstance(value, list):
            lines.append(f"{prefix}{key}: {', '.join(map(str, value))}")
        else:
            lines.append(f"{prefix}{key}: {repr(value)}")
    return "\n".join(lines)



    
    
