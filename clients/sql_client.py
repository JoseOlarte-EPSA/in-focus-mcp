from __future__ import annotations

import logging

import pandas as pd
import pyodbc

logger = logging.getLogger(__name__)


class SQLClient:
    """
    Clase base para clientes SQL Server. Gestiona la conexion y ejecucion de consultas.
    """

    def __init__(self, connection_string: str):
        """
        Args:
            connection_string (str): Cadena de conexion ODBC completa.
        """
        self.connection_string = connection_string
        self._conn = None

    def __enter__(self):
        """Abre la conexion al entrar en el bloque `with`."""
        self._conn = pyodbc.connect(self.connection_string)
        return self

    def __exit__(self, *args):
        """Cierra la conexion al salir del bloque `with`."""
        if self._conn:
            self._conn.close()
            self._conn = None

    def _fetch(self, conn, query: str) -> pd.DataFrame:
        """Levanta filas con un cursor y arma el DataFrame sin warnings."""
        cur = conn.cursor()
        try:
            cur.execute(query)
            columns = [c[0] for c in cur.description] if cur.description else []
            return pd.DataFrame.from_records(cur.fetchall(), columns=columns)
        finally:
            cur.close()

    def execute_query(self, query: str) -> pd.DataFrame:
        """
        Ejecuta una consulta SQL y devuelve el resultado como DataFrame.

        Reutiliza la conexion activa si existe (modo context manager);
        en caso contrario abre y cierra una conexion temporal.

        Args:
            query (str): Sentencia SQL a ejecutar.

        Returns:
            pd.DataFrame: Resultado de la consulta.
        """
        if self._conn:
            return self._fetch(self._conn, query)
        conn = pyodbc.connect(self.connection_string)
        try:
            return self._fetch(conn, query)
        finally:
            conn.close()
