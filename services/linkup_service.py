from __future__ import annotations

import json
from typing import Any


class LinkupService:
    """Cliente sobre la API de busqueda web de Linkup.

    Envuelve ``linkup.LinkupClient`` y normaliza la respuesta a un JSON
    serializable para devolverlo desde la herramienta MCP. La API key se
    lee del ``.env`` via :mod:`config`.
    """

    def __init__(self, api_key: str) -> None:
        self._api_key = (api_key or "").strip()
        self._client: Any | None = None

    @property
    def configured(self) -> bool:
        return bool(self._api_key)

    def _get_client(self) -> Any:
        if not self.configured:
            raise ValueError(
                "LINKUP_API_KEY no configurada en .env. "
                "Completa esta variable para usar la herramienta de busqueda web."
            )
        if self._client is None:
            from linkup import LinkupClient

            self._client = LinkupClient(api_key=self._api_key)
        return self._client

    def search(self, query: str) -> dict[str, Any]:
        """Ejecuta una busqueda web con fuentes (output_type=sourcedAnswer)."""
        clean_query = (query or "").strip()
        if not clean_query:
            return {
                "query": clean_query,
                "ok": False,
                "error": "La query recibida esta vacia. Indica el texto a buscar.",
            }

        try:
            client = self._get_client()
            result = client.search(
                clean_query,
                depth="standard",
                output_type="sourcedAnswer",
            )
        except ValueError as exc:
            # Faltan credenciales (LINKUP_API_KEY). Error ya descriptivo.
            return self._fail(clean_query, str(exc))
        except ImportError as exc:
            return self._fail(clean_query, f"Paquete 'linkup' no disponible: {exc}")
        except Exception as exc:  # noqa: BLE001 - mapeamos cualquier fallo de la API/SDK
            return self._fail(clean_query, f"{type(exc).__name__}: {exc}")

        return {
            "query": clean_query,
            "ok": True,
            "result": self._normalize(result),
        }

    @staticmethod
    def _fail(query: str, error: str) -> dict[str, Any]:
        return {"query": query, "ok": False, "error": error}

    @staticmethod
    def _normalize(result: Any) -> Any:
        """Convierte el resultado de Linkup a estructuras JSON seguras."""
        # Modelos Pydantic v1/v2.
        if hasattr(result, "model_dump"):
            data = result.model_dump()
        elif hasattr(result, "dict"):
            data = result.dict()
        else:
            data = result
        return json.loads(json.dumps(data, ensure_ascii=False, default=str))
