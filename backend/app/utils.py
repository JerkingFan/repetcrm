import json


def to_json_list(items: list[str]) -> str:
    return json.dumps([i.strip() for i in items if i.strip()], ensure_ascii=False)


def from_json_list(raw: str | None) -> list[str]:
    if not raw:
        return []
    try:
        data = json.loads(raw)
        if isinstance(data, list):
            return [str(x).strip() for x in data if str(x).strip()]
    except json.JSONDecodeError:
        pass
    return [x.strip() for x in raw.split(",") if x.strip()]
