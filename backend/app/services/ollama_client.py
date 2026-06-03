import httpx

from app.config import settings
from app.services.html_utils import ensure_html_fragment


class OllamaError(Exception):
    pass


async def check_ollama_health() -> dict:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(settings.ollama_tags_url)
            r.raise_for_status()
            data = r.json()
            models = [m.get("name", "").split(":")[0] for m in data.get("models", [])]
            target = settings.ollama_model.split(":")[0]
            return {
                "online": True,
                "models": models,
                "model_ready": target in models or any(target in m for m in models),
                "configured_model": settings.ollama_model,
            }
    except Exception as e:
        return {
            "online": False,
            "models": [],
            "model_ready": False,
            "configured_model": settings.ollama_model,
            "error": str(e),
        }


async def generate_with_ollama(prompt: str) -> str:
    """Chat API — стабильнее для instruct-моделей."""
    payload = {
        "model": settings.ollama_model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "options": {"temperature": 0.7, "num_predict": 2048},
    }
    try:
        async with httpx.AsyncClient(timeout=settings.ollama_timeout_sec) as client:
            response = await client.post(settings.ollama_chat_url, json=payload)
            if response.status_code == 404:
                return await _generate_legacy(client, prompt)
            response.raise_for_status()
            data = response.json()
    except httpx.ConnectError as e:
        raise OllamaError(
            "Ollama не запущена. Установите с https://ollama.com и выполните: "
            f"ollama pull {settings.ollama_model}"
        ) from e
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            detail = f"Модель '{settings.ollama_model}' не найдена. Выполните: ollama pull {settings.ollama_model}"
            raise OllamaError(detail) from e
        raise OllamaError(f"Ollama HTTP {e.response.status_code}: {e.response.text[:200]}") from e
    except httpx.HTTPError as e:
        raise OllamaError(f"Ошибка Ollama: {e}") from e

    raw = data.get("message", {}).get("content") or data.get("response", "")
    if not raw:
        raise OllamaError("Пустой ответ от Ollama")
    return ensure_html_fragment(raw)


async def _generate_legacy(client: httpx.AsyncClient, prompt: str) -> str:
    payload = {
        "model": settings.ollama_model,
        "prompt": prompt,
        "stream": False,
    }
    response = await client.post(settings.ollama_generate_url, json=payload)
    response.raise_for_status()
    data = response.json()
    raw = data.get("response", "")
    if not raw:
        raise OllamaError("Пустой ответ от Ollama")
    return ensure_html_fragment(raw)
