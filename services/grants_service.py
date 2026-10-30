from __future__ import annotations

from typing import Any

from clients.grants_client import GRANTSClient
from queries.grants import GRANTS_BY_SECTOR, GRANTS_BY_SECTOR_REGION, GRANTS_REGIONS


class GrantsService:
    """Ejecuta consultas SQL en tiempo real sobre la base de datos GRANTS.

    Version recortada del SQLRealtimeService del PoC: solo conserva la
    consulta de convocatorias abiertas por sector (sin dependencia BDNS).
    """

    def __init__(self, grants_client: GRANTSClient | None = None) -> None:
        self.grants_client = grants_client or GRANTSClient()

        self.catalog: dict[str, dict[str, Any]] = {
            "convocatorias_abiertas": {
                "template": GRANTS_BY_SECTOR,
                "columns_map": {
                    "TÍTULO": "Title",
                    "SECTOR": "Name",
                },
                "client_type": "grants",
            },
            "convocatorias_abiertas_region": {
                "template": GRANTS_BY_SECTOR_REGION,
                "columns_map": {
                    "TÍTULO": "Title",
                    "SECTOR": "Name",
                },
                "client_type": "grants",
            },
            "regiones": {
                "template": GRANTS_REGIONS,
                "columns_map": {
                    "REGIÓN": "Name",
                },
                "client_type": "grants",
            },
        }

    def execute_query(self, query_name: str, **kwargs: str) -> list[dict]:
        entry = self.catalog[query_name]
        template: str = entry["template"]
        columns_map: dict = entry["columns_map"]
        client_type: str = entry.get("client_type", "grants")

        # Sanitizar valores
        sanitized = {}
        for key, value in kwargs.items():
            if isinstance(value, str):
                escaped = value.replace("'", "''")
                sanitized[key] = f"'{escaped}'"
            else:
                sanitized[key] = value

        sql = template.format(**sanitized)

        # Seleccionar el cliente según el tipo de consulta
        client = self.grants_client if client_type == "grants" else None

        with client as db_client:
            df = db_client.execute_query(sql)

        # Renombrar columnas según el mapeo
        if columns_map:
            reverse_map = {v: k for k, v in columns_map.items()}
            df.rename(columns=reverse_map, inplace=True)

        return df.to_dict(orient="records")

    def get_convocatorias_abiertas(
        self, SECTOR_GRANTS: str, REGION_GRANTS: str | None = None
    ) -> list[dict]:
        if not REGION_GRANTS:
            return self.execute_query("convocatorias_abiertas", SECTOR_GRANTS=SECTOR_GRANTS)
        return self.execute_query(
            "convocatorias_abiertas_region",
            SECTOR_GRANTS=SECTOR_GRANTS,
            REGION_GRANTS=REGION_GRANTS,
        )

    def get_regions(self) -> list[dict]:
        return self.execute_query("regiones")
