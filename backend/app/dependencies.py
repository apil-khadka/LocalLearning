import math

import httpx

from app.config import Settings


class DependencyUnavailable(Exception):
    """An external local service could not complete the requested operation."""


class LocalServices:
    def __init__(self, settings: Settings, client: httpx.AsyncClient):
        self.settings, self.client = settings, client

    async def request(self, method: str, url: str, **kwargs):
        if not url.startswith(("http://", "https://")):
            raise DependencyUnavailable("A required local service is not configured.")
        try:
            response = await self.client.request(method, url, **kwargs)
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise DependencyUnavailable("A required local service is unavailable.") from exc

    async def models(self) -> set[str]:
        data = await self.request("GET", self.settings.ollama_base_url + "/api/tags")
        try:
            return {model["name"] for model in data["models"]}
        except (KeyError, TypeError) as exc:
            raise DependencyUnavailable("The model service returned invalid data.") from exc

    async def embed(self, texts: list[str]) -> list[list[float]]:
        data = await self.request(
            "POST",
            self.settings.ollama_base_url + "/api/embed",
            json={"model": self.settings.embed_model, "input": texts, "truncate": False},
            timeout=self.settings.model_timeout_seconds,
        )
        vectors = data.get("embeddings") if isinstance(data, dict) else None
        if (
            not isinstance(vectors, list)
            or len(vectors) != len(texts)
            or not vectors
            or not isinstance(vectors[0], list)
            or not vectors[0]
            or any(
                not isinstance(v, list)
                or len(v) != len(vectors[0])
                or not all(isinstance(n, int | float) and math.isfinite(n) for n in v)
                or not any(v)
                for v in vectors
            )
        ):
            raise DependencyUnavailable("The embedding service returned invalid vectors.")
        return vectors

    async def chat(self, messages: list[dict]) -> str:
        data = await self.request(
            "POST",
            self.settings.ollama_base_url + "/api/chat",
            json={
                "model": self.settings.ollama_model,
                "messages": messages,
                "stream": False,
                "options": {"temperature": 0.3, "num_predict": 600},
            },
            timeout=self.settings.model_timeout_seconds,
        )
        try:
            answer = data["message"]["content"]
            if not isinstance(answer, str) or not answer.strip():
                raise ValueError("empty reply")
            return answer
        except (KeyError, TypeError, ValueError) as exc:
            raise DependencyUnavailable("The model did not return a readable answer.") from exc

    async def qdrant(self, method: str, path: str, **kwargs):
        return await self.request(
            method,
            self.settings.qdrant_url + path,
            headers={"api-key": self.settings.qdrant_api_key.get_secret_value()},
            **kwargs,
        )

    @property
    def collection_path(self):
        return "/collections/" + self.settings.qdrant_collection

    async def ensure_collection(self, size: int):
        collections = await self.qdrant("GET", "/collections")
        try:
            names = {item["name"] for item in collections["result"]["collections"]}
            if self.settings.qdrant_collection not in names:
                await self.qdrant(
                    "PUT",
                    self.collection_path,
                    json={"vectors": {"size": size, "distance": "Cosine"}},
                )
            else:
                info = await self.qdrant("GET", self.collection_path)
                vectors = info["result"]["config"]["params"]["vectors"]
                if vectors["size"] != size or vectors["distance"] != "Cosine":
                    raise DependencyUnavailable(
                        "Embedding dimensions changed. Use a new dh_ collection and reindex."
                    )
        except (KeyError, TypeError) as exc:
            raise DependencyUnavailable(
                "The vector service returned invalid collection data."
            ) from exc

    async def probe_web(self, public_url: str, probe_url: str) -> dict:
        if not public_url:
            return {"status": "unconfigured", "url": None}
        try:
            response = await self.client.get(
                probe_url or public_url,
                timeout=self.settings.dependency_timeout_seconds,
                follow_redirects=True,
            )
            response.raise_for_status()
            return {"status": "reachable", "url": public_url}
        except httpx.HTTPError:
            return {"status": "unavailable", "url": None}
