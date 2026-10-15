from __future__ import annotations

from typing import Any

from clients.fabric_client import FabricClient
from queries.bdns import DETALLE_DE_AYUDAS


class WarehouseService:
    """Ejecuta consultas SQL en tiempo real sobre el warehouse Fabric
    (LH_Operations_30_Gold), esquema `bdns`.

    Mismo patron catalog-driven que GrantsService, pero con un unico cliente
    (FabricClient) ya que todas sus plantillas apuntan al mismo warehouse.
    """

    def __init__(self, fabric_client: FabricClient | None = None) -> None:
        self.fabric_client = fabric_client or FabricClient()

        self.catalog: dict[str, dict[str, Any]] = {
            "detalle_ayudas": {
                "template": DETALLE_DE_AYUDAS,
                "columns_map": {
                    "NIF": "NIF",
                    "BENEFICIARIO": "Account",
                    "ANUNCIO": "AnnouncementDescription",
                    "ORGANISMO": "Organism",
                    "FONDOS_A_PRESTAMO": "TotalPrestamo",
                    "FONDOS_A_SUBVENCIÓN": "TotalSubvencion",
                },
            },
        }

    def execute_query(self, query_name: str, **kwargs: str) -> list[dict]:
        entry = self.catalog[query_name]
        template: str = entry["template"]
        columns_map: dict = entry["columns_map"]

        # Sanitizar valores
        sanitized = {}
        for key, value in kwargs.items():
            if isinstance(value, str):
                escaped = value.replace("'", "''")
                sanitized[key] = f"'{escaped}'"
            else:
                sanitized[key] = value

        sql = template.format(**sanitized)

        with self.fabric_client as db_client:
            df = db_client.execute_query(sql)

        # Renombrar columnas según el mapeo
        if columns_map:
            reverse_map = {v: k for k, v in columns_map.items()}
            df.rename(columns=reverse_map, inplace=True)

        return df.to_dict(orient="records")

    def get_detalle_ayudas(self, ACCOUNT_NIF: str) -> list[dict]:
        return self.execute_query("detalle_ayudas", ACCOUNT_NIF=ACCOUNT_NIF)
