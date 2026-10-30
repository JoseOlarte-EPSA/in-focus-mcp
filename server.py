from __future__ import annotations

import json
from typing import Any

from fastmcp import FastMCP
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from auth import BearerTokenMiddleware
from config import load_settings
from sectors import SECTORES
from services.grants_service import GrantsService
from services.linkup_service import LinkupService
from services.warehouse_service import WarehouseService


settings = load_settings()

SERVICE = GrantsService()
WAREHOUSE_SERVICE = WarehouseService()
LINKUP_SERVICE = LinkupService(settings.linkup_api_key)

# ── Rutas HTTP personalizadas ─────────────────────────────────────────────────


mcp = FastMCP(name=settings.app_name, version=settings.server_version)


def _capabilities() -> dict[str, Any]:
    return {
        "app": settings.app_name,
        "version": settings.server_version,
        "mcp_path": settings.mcp_path,
        "transport": settings.transport,
        "auth_mode": settings.auth_mode,
        "tools": [
            "obtener_diccionario",
            "get_convocatorias_abiertas",
            "get_regions",
            "get_ayudas_percibidas_bdns",
            "buscar_web",
        ],
    }


@mcp.custom_route("/", methods=["GET"], include_in_schema=False)
async def root(_request: Request) -> JSONResponse:
    return JSONResponse({
        "name": settings.app_name,
        "version": settings.server_version,
        "mcp_url": settings.mcp_path,
        "health_url": "/health",
    })


@mcp.custom_route("/health", methods=["GET"], include_in_schema=False)
async def health(_request: Request) -> JSONResponse:
    return JSONResponse({
        "status": "ok",
        "app": settings.app_name,
        "auth_mode": settings.auth_mode,
        "mcp_path": settings.mcp_path,
    })


@mcp.custom_route("/v1/capabilities", methods=["GET"], include_in_schema=False)
async def capabilities_route(_request: Request) -> JSONResponse:
    return JSONResponse(_capabilities())


# ── Herramientas MCP ──────────────────────────────────────────────────────────

@mcp.tool
def obtener_diccionario() -> str:
    """Devuelve el diccionario de sectores FI y sectores GRANTS."""
    return json.dumps(SECTORES, ensure_ascii=False, indent=2)


@mcp.tool(
    description="""
    Devuelve las convocatorias de subvenciones abiertas para el sector indicado,
    opcionalmente restringidas a una region concreta (Espana).

    ⚠️ IMPORTANTE — NORMALIZACIÓN DEL SECTOR (obligatoria antes de llamar al metodo):

    1. El parámetro `sector_grants` recibido del usuario PUEDE estar en inglés, español o cualquier idioma,
       y puede ser una descripción coloquial, abreviada o no reconocida exactamente.

    2. Para normalizar el sector, DEBES realizar los siguientes pasos:

       a) Obtén el diccionario de sectores invocando la herramienta: obtener_diccionario
          Este diccionario tiene dos columnas: CRM (nombre original del sector) y GRANTS (nombre normalizado).

       b) Busca un MATCH EXACTO comparando el input contra la columna CRM:
          - Si encuentra match → usa el valor correspondiente de la columna GRANTS como parámetro final.

       c) Si NO hay match exacto, busca el nombre CRM MÁS SEMEJANTE/ASEMEJADO al input del usuario:
          - Considera similitud textual, traducciones aproximadas, variaciones de mayúsculas/minúsculas,
            caracteres especiales, o nombres alternativos del mismo sector.
          - Usa el valor GRANTS asociado al CRM más parecido.

       d) Como fallback FINAL, si no hay semejanza clara posible → usa el valor `sector_grants` tal cual llegó.

    3. Con el sector NORMALIZADO resultante, ejecuta la consulta SQL de convocatorias abiertas.

    ⚠️ IMPORTANTE — REGLAS DE LA REGION (aplican solo si se quiere filtrar por region):

    4. El parametro `region_grants` es OPCIONAL. Si no se aporta, la busqueda cubre Espana completa
       (comportamiento por defecto).

    5. La region DEBE ser exactamente uno de los nombres devueltos por la herramienta `get_regions`
       (valores de la columna Name de la tabla Locations, pais Espana). No inventes variantes,
       abreviaturas, sinonimos ni grafias alternativas. Para conocer los valores validos invoca la
       herramienta: get_regions

    6. ANTES de llamar con una region, CONFIRMA CON EL USUARIO con cual se hara la busqueda:
       - Si el usuario menciona una zona geografica (comunidad autonoma, area, etc.), compara su
         referencia contra la lista de `get_regions` y confirma explicitamente el nombre exacto a usar.
       - Si hay varias regiones candidatas similares o existe ambiguedad, pregunta al usuario.
       - Si el nombre mencionado NO esta en la lista, avisa y ofrece las alternativas validas mas
         cercanas (no llames con un nombre inventado: la consulta devolveria una lista vacia).

Por cada convocatoria retorna:
- SECTOR: Sector al que aplica la convocatoria.
- TÍTULO: Título o nombre de la convocatoria de subvención.

Args:
    sector_grants: Nombre del sector ingresado por el usuario (puede estar en inglés, español,
                   abreviado, o no reconocido). Ejemplos válidos: "Aeroespacial", "aerospace",
                   "Aeronautical - Space", "Espacio", "Energy", etc.
    region_grants: Region opcional (None = busqueda sobre Espana completa). Debe coincidir
                   EXACTAMENTE con uno de los nombres devueltos por `get_regions` (ej.:
                   "Andalucia", "Castilla y Leon", "Comunidad de Madrid", "Galicia"). Antes de
                   usarla, confirmala con el usuario (ver reglas de la region).

Returns:
    Lista de convocatorias abiertas que coinciden con el sector normalizado y, si se indica,
    con la region.

Use este recurso cuando el usuario/comercial/gestor de cuenta quiera consultar las convocatorias
en las que una cuenta puede encajar según su sector y, opcionalmente, su region. SIEMPRE normaliza
el sector mediante el diccionario antes de ejecutar la consulta, y usa como region unicamente
valores de la lista de `get_regions`, confirmados con el usuario.
"""
)
def get_convocatorias_abiertas(
    sector_grants: str, region_grants: str | None = None
) -> list[dict]:
    return SERVICE.get_convocatorias_abiertas(sector_grants, region_grants)


@mcp.tool(
    description="""
    Obtiene el listado de regiones disponibles en la base de datos GRANTS para Espana.

    Utilice esta herramienta cuando el usuario pregunte que regiones/zonas/areas geograficas
    soporta la base GRANTS, o para conocer los valores validos antes de filtrar o
    contextualizar convocatorias por region.

    Returns:
        Lista de dict con una unica clave por registro:
        - REGION: Nombre de la region disponible en la tabla Locations (pais Espana),
          sin duplicados y ordenada alfabeticamente.
    """
)
def get_regions() -> list[dict]:
    return SERVICE.get_regions()


@mcp.tool(
    description="""
    Obtiene el listado completo y detallado de las ayudas o subvenciones percibidas por una cuenta específica según su NIF (histórico completo disponible en BDNS).

    Args:
        nif (str): NIF fiscal de la cuenta.

    Returns:
        Lista de dict con claves:
        - NIF: Código fiscal del beneficiario
        - BENEFICIARIO: Nombre del beneficiario
        - ANUNCIO: Descripción de la convocatoria/subvención
        - ORGANISMO: Organismo concedente
        - FONDOS_A_PRESTAMO: Importe en préstamos
        - FONDOS_A_SUBVENCIÓN: Importe en subvenciones
    """
)
def get_ayudas_percibidas_bdns(nif: str) -> list[dict]:
    return WAREHOUSE_SERVICE.get_detalle_ayudas(nif.strip().upper())


@mcp.tool(
    description="""
    Realiza una busqueda web y devuelve una respuesta redactada con sus fuentes (Linkup).

    Use esta herramienta para consultas generales de informacion que no esten cubiertas por las
    herramientas internas de convocatorias, ayudas percibidas o el diccionario de sectores
    (p.ej. noticias del sector, contexto de mercado, datos publicos, empresas, etc.).

    Args:
        query (str): Texto a buscar. Puede ser en espanol o ingles, en forma de frase natural
                     o de pregunta. Ej.: "principales fabricantes de componentes aeronauticos en Europa".

    Returns:
        dict con claves:
        - query: la consulta enviada.
        - ok: True si la busqueda se ejecuto correctamente; False en caso contrario.
        - result: (solo si ok=True) respuesta redactada con su lista de fuentes.
        - error: (solo si ok=False) descripcion legible del problema.
    """
)
def buscar_web(query: str) -> dict[str, Any]:
    return LINKUP_SERVICE.search(query)


# ── App con middleware opcional ───────────────────────────────────────────────

middleware = []
if settings.auth_enabled:
    middleware.append(
        Middleware(
            BearerTokenMiddleware,
            bearer_token=settings.bearer_token,
            protected_prefixes=(settings.mcp_path,),
        )
    )

app = mcp.http_app(
    path=settings.mcp_path,
    transport=settings.transport,
    middleware=middleware,
    json_response=True,
    stateless_http=True,
)
