"""Plantillas SQL de la base de datos GRANTS (Azure SQL Server)."""

# Convocatorias de subvencion abiertas para un sector concreto.
# Placeholder {SECTOR_GRANTS}: nombre de sector segun la columna Sectors.Name
# (valores normalizados de sectors.py). Inyectado como string escapado.
GRANTS_BY_SECTOR = """SELECT
    TOP 15
    g.Title,
    s.Name
FROM
    Sectors s
    INNER JOIN GrantSectors gs ON s.Id = gs.SectorId
    INNER JOIN Grants g ON gs.GrantId = g.Id
    INNER JOIN GrantLocations gl ON gl.GrantId = g.Id
    INNER JOIN Locations lc ON gl.LocationId = lc.Id
WHERE
    s.Name = {SECTOR_GRANTS}
    AND g.Status IN (1, 2)
    AND g.Deleted = 0
    AND lc.CountryId = 'Es'
GROUP BY
    g.Title,
    s.Name
ORDER BY
    MIN(g.OrderByStatusCategory) ASC,
    MAX(g.CreatedOn) DESC;
"""

# Convocatorias de subvencion abiertas para un sector concreto filtradas por
# region (una de las devueltas por GRANTS_REGIONS / tabla Locations, pais 'Es').
# Placeholders: {SECTOR_GRANTS} y {REGION_GRANTS}, ambos inyectados como strings
# escapados (saneamiento de quotes + comillas en GrantsService.execute_query).
GRANTS_BY_SECTOR_REGION = """SELECT
    TOP 15
    g.Title,
    s.Name
FROM
    Sectors s
    INNER JOIN GrantSectors gs ON s.Id = gs.SectorId
    INNER JOIN Grants g ON gs.GrantId = g.Id
    INNER JOIN GrantLocations gl ON gl.GrantId = g.Id
    INNER JOIN Locations lc ON gl.LocationId = lc.Id
WHERE
    s.Name = {SECTOR_GRANTS}
    AND g.Status IN (1, 2)
    AND g.Deleted = 0
    AND lc.CountryId = 'Es'
    AND lc.Name = {REGION_GRANTS}
GROUP BY
    g.Title,
    s.Name
ORDER BY
    MIN(g.OrderByStatusCategory) ASC,
    MAX(g.CreatedOn) DESC;
"""

# Regiones disponibles en España en la base GRANTS (tabla Locations).
# Pais hardcodeado a 'Es' como literal (no es placeholder parametrizado),
# igual que en GRANTS_BY_SECTOR. Sin placeholders: se ejecuta tal cual.
GRANTS_REGIONS = """SELECT
    DISTINCT lc.Name
FROM
    Locations lc
WHERE
    lc.CountryId = 'Es'
ORDER BY
    lc.Name;
"""
