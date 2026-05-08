from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document
import requests

CHROMA_DIR = "./chroma_db"
COLLECTION_NAME = "tarkov_hideout"


"""
📡 Obtener datos del hideout desde la API de Tarkov
"""
def obtener_hideout():
    url = "https://api.tarkov.dev/graphql"

    query = """
    query MyQuery {
      hideoutStations {
        name
        levels {
          constructionTime
          bonuses {
            name
            skillName
            value
            type
            production
          }
          itemRequirements {
            count
            item {
              name
            }
            quantity
          }
          level
          skillRequirements {
            level
            name
          }
          stationLevelRequirements {
            level
            station {
              name
            }
          }
          traderRequirements {
            value
            trader {
              name
            }
          }
          crafts {
            requiredItems {
              quantity
              item {
                name
              }
            }
            duration
            rewardItems {
              quantity
              item {
                name
              }
            }
          }
        }
      }
    }
    """

    response = requests.post(url, json={"query": query})

    if response.status_code != 200:
        raise Exception(f"Error {response.status_code}")

    data = response.json()

    if "errors" in data:
        print(f"⚠️  Errores en la query: {data['errors']}")
        return []

    return data.get("data", {}).get("hideoutStations", [])


"""
📄 Convertir estaciones del hideout JSON → Documents de LangChain
   Se crea un documento por cada nivel de cada estación.
"""
def convertir_a_documentos(stations):
    documentos = []

    for station in stations:
        station_name = station.get("name", "")

        for lvl in station.get("levels", []):
            texto = []
            level_num = lvl.get("level", "?")

            texto.append(f"Hideout Station: {station_name}")
            texto.append(f"Level: {level_num}")

            # Tiempo de construcción
            construction_time = lvl.get("constructionTime", 0)
            horas = construction_time // 3600
            minutos = (construction_time % 3600) // 60
            texto.append(f"Construction Time: {horas}h {minutos}m")

            # Bonuses
            bonuses = lvl.get("bonuses", [])
            if bonuses:
                texto.append("Bonuses:")
                for bonus in bonuses:
                    bonus_name = bonus.get("name", "")
                    bonus_type = bonus.get("type", "")
                    bonus_value = bonus.get("value", "")
                    skill_name = bonus.get("skillName", "")
                    line = f"  - {bonus_name} ({bonus_type}): {bonus_value}"
                    if skill_name:
                        line += f" [Skill: {skill_name}]"
                    texto.append(line)

            # Items necesarios para construir
            item_reqs = lvl.get("itemRequirements", [])
            if item_reqs:
                texto.append("Required Items:")
                for req in item_reqs:
                    item_name = req.get("item", {}).get("name", "Unknown")
                    count = req.get("count", req.get("quantity", "?"))
                    texto.append(f"  - {item_name} x{count}")

            # Requisitos de habilidad
            skill_reqs = lvl.get("skillRequirements", [])
            if skill_reqs:
                texto.append("Skill Requirements:")
                for req in skill_reqs:
                    texto.append(f"  - {req.get('name', '')} level {req.get('level', '?')}")

            # Requisitos de otras estaciones
            station_reqs = lvl.get("stationLevelRequirements", [])
            if station_reqs:
                texto.append("Station Requirements:")
                for req in station_reqs:
                    req_station = req.get("station", {}).get("name", "Unknown")
                    texto.append(f"  - {req_station} level {req.get('level', '?')}")

            # Requisitos de traders
            trader_reqs = lvl.get("traderRequirements", [])
            if trader_reqs:
                texto.append("Trader Requirements:")
                for req in trader_reqs:
                    trader_name = req.get("trader", {}).get("name", "Unknown")
                    texto.append(f"  - {trader_name} level {req.get('value', '?')}")

            # Crafts disponibles en este nivel
            crafts = lvl.get("crafts", [])
            if crafts:
                texto.append(f"Crafts ({len(crafts)} available):")
                for craft in crafts:
                    # Reward items
                    rewards = craft.get("rewardItems", [])
                    reward_names = [f"{r.get('item', {}).get('name', '?')} x{r.get('quantity', '?')}" for r in rewards]

                    # Required items
                    required = craft.get("requiredItems", [])
                    req_names = [f"{r.get('item', {}).get('name', '?')} x{r.get('quantity', '?')}" for r in required]

                    duration = craft.get("duration", 0)
                    craft_hours = duration // 3600
                    craft_mins = (duration % 3600) // 60

                    texto.append(f"  Craft: {', '.join(reward_names)}")
                    texto.append(f"    Requires: {', '.join(req_names)}")
                    texto.append(f"    Duration: {craft_hours}h {craft_mins}m")

            contenido = "\n".join(texto)

            documentos.append(
                Document(
                    page_content=contenido,
                    metadata={
                        "station_name": station_name,
                        "level": level_num,
                    }
                )
            )

    return documentos


"""
✂️ Partir documentos en chunks
"""
def partir_documentos(documentos):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=512,
        chunk_overlap=60
    )
    return splitter.split_documents(documentos)


"""
🧠 Crear embeddings
"""
def crear_embeddings():
    return OllamaEmbeddings(
        model="mxbai-embed-large",
        base_url="http://localhost:11434",
    )


"""
🗄️ Crear / cargar vectorstore
"""
def crear_vectorstore(embeddings, chunks=None):
    vectorstore = Chroma(
        persist_directory=CHROMA_DIR,
        embedding_function=embeddings,
        collection_name=COLLECTION_NAME
    )

    num_docs = vectorstore._collection.count()

    if num_docs == 0 and chunks:
        print(f"💾 Guardando {len(chunks)} chunks en '{COLLECTION_NAME}'...")
        vectorstore.add_documents(chunks)
    else:
        print(f"ℹ️  '{COLLECTION_NAME}' ya tiene {num_docs} documentos, se omite.")

    return vectorstore


def main():
    print("📡 Obteniendo estaciones del hideout desde la API...")
    stations = obtener_hideout()
    print(f"Estaciones obtenidas: {len(stations)}")

    documentos = convertir_a_documentos(stations)
    print(f"Documentos creados: {len(documentos)} (uno por cada nivel de cada estación)")

    chunks = partir_documentos(documentos)
    print(f"Chunks generados: {len(chunks)}")

    embeddings = crear_embeddings()
    print("🧠 Embeddings listos")

    crear_vectorstore(embeddings, chunks)

    print("✅ RAG del hideout creado correctamente")


if __name__ == "__main__":
    main()
