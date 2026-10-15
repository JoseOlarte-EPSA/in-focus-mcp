from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

import pyodbc

from clients import FabricClient

REQUIRED_ENV = (
    "FABRIC_SQL_ENDPOINT",
    "FABRIC_DATABASE",
    "FABRIC_TENANT_ID",
    "FABRIC_CLIENT_ID",
    "FABRIC_CLIENT_SECRET",
)


def check_aad_token(tenant_id: str, client_id: str, secret: str) -> bool:
    """Verifica que la aplicacion registrada emita un token para el ambito de bases de datos."""
    url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    data = urllib.parse.urlencode(
        {
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": secret,
            "scope": "https://database.windows.net/.default",
        }
    ).encode()
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read())
            if "access_token" in body:
                print("Token AAD OK: la aplicacion registrada y el secret son validos.")
                return True
    except urllib.error.HTTPError as exc:
        try:
            err = json.loads(exc.read().decode())
            detail = f"{exc.code} {err.get('error')}: {err.get('error_description')}"
        except Exception:
            detail = str(exc)
        print(f"ERROR: Azure AD rechazo las credenciales. {detail}")
        return False
    except Exception as exc:
        print(f"ERROR: no se pudo contactar Azure AD ({exc}). Revisa conectividad.")
        return False
    return False


def hint_from_error(msg: str) -> str:
    m = msg.lower()
    if "login failed" in m:
        return (
            "Credenciales validas en Azure AD pero sin acceso al warehouse. Verifica: "
            "(1) que el service principal se agrego en el workspace de Fabric "
            "con rol Viewers o Contributors; (2) que en el portal de administracion "
            "de Fabric este habilitada la opcion 'Service principals can use Fabric APIs'; "
            "(3) que el warehouse tenga el endpoint SQL activo."
        )
    if "certificate" in m:
        return (
            "No coincide el certificado del servidor. Revisa FABRIC_SQL_ENDPOINT: "
            "debe ser el hostname exacto del tipo *.datawarehouse.fabric.microsoft.com."
        )
    if "not found" in m or "08001" in m or "im002" in m:
        return "Instala ODBC Driver 18 for SQL Server (version 18.1 o superior para service principal)."
    if "service principal" in m or "activator" in m:
        return (
            "Activa en el portal de administracion de Fabric la opcion "
            "'Service principals can use Fabric APIs'."
        )
    return "Revisa los valores del .env y el estado del SQL endpoint en Fabric."


def main() -> int:
    try:
        client = FabricClient()
    except KeyError as exc:
        print(f"Falta la variable de entorno {exc.args[0]}. Completala en .env antes de probar.")
        return 1

    # Descarta credenciales invalidas antes de apuntar al endpoint de Fabric.
    check_aad_token(
        os.environ["FABRIC_TENANT_ID"],
        os.environ["FABRIC_CLIENT_ID"],
        os.environ["FABRIC_CLIENT_SECRET"],
    )

    try:
        with client as c:
            ok = c.execute_query("SELECT 1 AS ok")
            print("Conexion OK:", ok.to_dict("records"))
            tables = c.execute_query(
                "SELECT TOP 10 TABLE_NAME FROM INFORMATION_SCHEMA.TABLES ORDER BY TABLE_NAME"
            )
            print("Tablas visibles:", ", ".join(tables["TABLE_NAME"].tolist()) or "(ninguna)")
        return 0
    except pyodbc.Error as exc:
        print(f"ERROR DE CONEXION: {exc}")
        print("Posible causa:", hint_from_error(str(exc)))
        return 1


if __name__ == "__main__":
    sys.exit(main())
