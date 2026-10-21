# IN Focus MCP

Servidor MCP (Model Context Protocol) para consultar convocatorias de subvenciones abiertas por sector sobre la base de datos **GRANTS** (Azure SQL Server).

Proyecto extraído del PoC `PoC---MCP`:

| Herramienta MCP | Descripción |
| --- | --- |
| `obtener_diccionario` | Devuelve el diccionario estático de sectores (`CRM` → `GRANTS`) en JSON. Se usa para normalizar el sector que aporta el usuario antes de consultar. |
| `get_convocatorias_abiertas` | Consulta las convocatorias de subvenciones abiertas (status "Abierta" / "Pre-abierta") para un sector normalizado y país España. Retorna hasta 15 resultados con campos `TÍTULO` y `SECTOR`. |
| `buscar_web` | Realiza una búsqueda web vía **Linkup** y devuelve una respuesta redactada con sus fuentes. Útil para consultas generales no cubiertas por las herramientas internas (noticias del sector, contexto de mercado, datos públicos, empresas…). Requiere `LINKUP_API_KEY`. |

## Estructura

```
IN Focus - MCP/
├── __main__.py            # python __main__.py → arranca uvicorn
├── main.py                # exporta `app` (uvicorn main:app) + guard __main__
├── server.py              # FastMCP: herramientas, rutas HTTP, assembly final
├── config.py              # Settings (dataclass frozen) desde variables de entorno
├── auth.py                # BearerTokenMiddleware (opcional)
├── sectors.py             # SECTORES: diccionario CRM → GRANTS (36 entradas)
├── clients/
│   ├── sql_client.py      # SQLClient: context manager + pd.read_sql
│   └── grants_client.py   # GRANTSClient: cadena ODBC para GRANTS
├── queries/
│   └── grants.py          # Plantilla SQL GRANTS_BY_SECTOR
├── services/
│   ├── grants_service.py    # GrantsService: saneamiento, ejecución, remap de columnas
│   └── linkup_service.py    # LinkupService: cliente de búsqueda web (Linkup) con respuesta + fuentes
├── .env.example             # Plantilla de variables de entorno
└── requirements.txt
```

Flujo GRANTS: herramienta → `GrantsService.get_convocatorias_abiertas` → plantilla SQL sanitizada → `GRANTSClient` (ODBC) → DataFrame → lista de dicts.

Flujo web: herramienta `buscar_web` → `LinkupService.search(query)` → `LinkupClient.search(..., output_type="sourcedAnswer")` → dict `{ query, ok, result }`.

## Requisitos

- Python 3.10+
- **ODBC Driver 18 for SQL Server** instalado en el sistema
  (Windows: instalador de Microsoft o `winget install Microsoft.Msodbcsql.18`).
  Verificar con: `pyodbc.drivers()`

## Instalación

```powershell
cd "IN Focus - MCP"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Configurar `.env`

```powershell
Copy-Item .env.example .env
```

Completa `.env`:

| Variable | Obligatorio | Descripción |
| --- | --- | --- |
| `SERVER_NAME` | No | Nombre mostrado en `/` y `/v1/capabilities`. Defecto: `IN Focus MCP`. |
| `SERVER_VERSION` | No | Versión mostrada en los endpoints públicos. Defecto: `0.1.0`. |
| `HOST` | No | Bind de uvicorn. Defecto: `0.0.0.0`. |
| `PORT` | No | Puerto. Defecto: `8000`. |
| `MCP_PATH` | No | Ruta del endpoint MCP. Defecto: `/mcp`. |
| `MCP_TRANSPORT` | No | Transporte. Defecto: `streamable-http`. |
| `MCP_AUTH_MODE` | No | `none` (defecto) o `bearer`. |
| `MCP_BEARER_TOKEN` | Solo con bearer | Token compartido. `validate()` falla si falta. |
| `GRANTS_SERVER` | Sí | Servidor GRANTS (p.ej. `*.database.windows.net`). |
| `GRANTS_DATABASE` | Sí | Base de datos (p.ej. `Apps_Grants`). |
| `GRANTS_USERNAME` | Sí | Usuario SQL. |
| `GRANTS_PASSWORD` | Sí | Contraseña SQL. |
| `SQL_DRIVER` | No | Driver ODBC. Defecto: `ODBC Driver 18 for SQL Server`. |
| `LINKUP_API_KEY` | Solo para `buscar_web` | API key de Linkup (https://linkup.so). Sin ella, el servidor arranca pero esa herramienta devuelve un error claro. |

Los nombres exactos que lee el código son `GRANTS_SERVER` / `GRANTS_DATABASE` / `GRANTS_USERNAME` / `GRANTS_PASSWORD` (no confundir con nombres alternativos documentados en el PoC original).

## Arranque

```powershell
python __main__.py
```

o de forma equivalente:

```powershell
uvicorn main:app --host 0.0.0.0 --port 8000
```

> Nota: al importar `server.py` se instancia `GrantsService()`, que construye `GRANTSClient()` y lee las variables `GRANTS_*` en caliente. Si faltan, el arranque fallará con `KeyError`; completa el `.env` antes de iniciar.

### Endpoints HTTP

| URL | Método | Auth | Descripción |
| --- | --- | --- | --- |
| `/` | GET | Público | Nombre, versión y URL del MCP. |
| `/health` | GET | Público | Estado del servicio. |
| `/v1/capabilities` | GET | Público | Lista de herramientas disponibles. |
| `/mcp` | POST | Según `MCP_AUTH_MODE` | Endpoint MCP (transporte `streamable-http`, sin estado). |

Con `MCP_AUTH_MODE=bearer`, `/mcp` exige cabecera `Authorization: Bearer <MCP_BEARER_TOKEN>`; las demás rutas permanecen públicas.

### Conexión de un cliente MCP

URL: `http://localhost:8000/mcp`

Ejemplo de configuración tipo (Claude Desktop / cliente compatible):

```json
{
  "mcpServers": {
    "in-focus-grants": {
      "url": "http://localhost:8000/mcp",
      "headers": {
        "Authorization": "Bearer TU_TOKEN"
      }
    }
  }
}
```

(Eliminar `headers` si `MCP_AUTH_MODE=none`.)

## Uso

1. El agente llama a `obtener_diccionario` y obtiene el mapeo `CRM → GRANTS`.
2. Normaliza el sector indicado por el usuario contra la columna `CRM` (match exacto, similitud textual o fallback tal cual).
3. Llama a `get_convocatorias_abiertas(sector_grants=<sector normalizado>)`.
4. Recibe una lista de `{ "TÍTULO": ..., "SECTOR": ... }` (máximo 15, ordenadas por estado y fecha de creación).

## Solución de problemas

| Síntoma | Causa probable / solución |
| --- | --- |
| `KeyError: 'GRANTS_SERVER'` al arrancar | Falta alguna variable `GRANTS_*` en `.env`. Completarlas. |
| `pyodbc.InterfaceError` / "Unable to connect: error in datasource" | Driver ODBC no instalado o nombre distinto → comprobar con `python -c "import pyodbc; print(pyodbc.drivers())"` y ajustar `SQL_DRIVER`. También revisar firewall/red (Azure SQL requiere IP permitida y puerto 1433). |
| `Login failed for user` | Credenciales `GRANTS_USERNAME`/`GRANTS_PASSWORD` incorrectos. |
| Resultado vacío | El sector no existe en `Sectors.Name` o no hay convocatorias abiertas para ese sector en España. Probar con valores del diccionario (p.ej. `Energy`). |
| `MCP_BEARER_TOKEN es obligatorio...` | `MCP_AUTH_MODE=bearer` sin token. Rellenarlo o cambiar el modo a `none`. |
| 401 en `/mcp` | Faltan o erróneas cabeceras `Authorization` cuando el auth es `bearer`. |
| `buscar_web` → error "LINKUP_API_KEY no configurada" | Falta la key de Linkup en `.env`. Añade `LINKUP_API_KEY=<tu-key>` (https://linkup.so) y reinicia. El servidor arranca igual aunque falte; solo esa herramienta devuelve este aviso. |
| `buscar_web` → error de autenticación/401 de Linkup | La key presente es inválida o caducada. Verifica que esté completa y con créditos suficientes en tu cuenta Linkup. |

## Proveniencia

Extraído de `PoC---MCP` (solo lectura): `server.py` (herramientas y assembly), `scripts/realtime_query_service.py` (`SQLRealtimeService` → `GrantsService`), `scripts/clients/sql_client.py`, `scripts/clients/grants_client.py`, `py_queries/APP_GRANTS.py` (`GRANTS_BY_SECTOR`), `scripts/config/dictionary.py` (`SECTORES`), `config.py` (recortado, sin `excel_path`), `auth.py`, `__main__.py`, `main.py`.

Cambios respecto al PoC:

- `GrantsService` no depende de `BDNSClient` (evita requerir variables `BDNS_*`).
- La descripción de `get_convocatorias_abiertas` referencia la **herramienta** `obtener_diccionario` en lugar de un recurso (`resource://...`).
- `obtener_diccionario` devuelve JSON formateado en vez de la representación Python de la lista.
- `load_dotenv` apunta al `.env` de la raíz del proyecto (un nivel menos de anidación).
