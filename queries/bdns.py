# Plantillas SQL contra el esquema `bdns` del warehouse Fabric
# (LH_Operations_30_Gold). Portadas desde PoC---MCP adaptadas al
# endpoint SQL existente.

DETALLE_DE_AYUDAS = """SELECT 
  fbnds.BeneficiaryNif AS NIF
  ,fbnds.BeneficiaryName AS Account
  ,gr_grants.AnnouncementDescription AS AnnouncementDescription
  ,gr_grants.Organism AS "Organism"
  ,SUM(CASE WHEN dinst.Instrument = 'PRÉSTAMO' THEN fbnds.TotalAmountConcession ELSE 0 END) AS TotalPrestamo
  ,SUM(CASE WHEN dinst.Instrument = 'SUBVENCIÓN y ENTREGA DINERARIA SIN CONTRAPRESTACIÓN' THEN fbnds.TotalAmountConcession ELSE 0 END) AS TotalSubvencion
FROM 
  bdns.FactBdnsGs fbnds
INNER JOIN 
  bdns.DimGrantsSearcher gr_grants ON gr_grants.Id = fbnds.IdGrantsSearcher
LEFT JOIN
  bdns.DimInstrument dinst ON dinst.Id = fbnds.IdInstrument
WHERE 
  fbnds.BeneficiaryNif = {ACCOUNT_NIF}
GROUP BY
  fbnds.BeneficiaryNif
  ,fbnds.BeneficiaryName
  ,gr_grants.AnnouncementDescription
  ,gr_grants.Organism
;"""
