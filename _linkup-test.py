import os
from linkup import LinkupClient

# 1. Inicializar el cliente (puedes usar variables de entorno o pasar la key directo)
# os.environ["LINKUP_API_KEY"] = "tu_api_key_aqui"
client = LinkupClient(api_key="LINKUP_API_KEY")

print("--- 🔎 EJEMPLO 1: BÚSQUEDA WEB PARA IA ---")
# Realizamos una consulta compleja esperando una respuesta ya estructurada y citada
search_response = client.search(
    query="***query por parametro***",
    depth="standard",                
    output_type="sourcedAnswer"    # Devuelve el texto redactado con fuentes bibliográficas
)
print(search_response)
