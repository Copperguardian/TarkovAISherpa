from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document
import requests

CHROMA_DIR = "./chroma_db"

# Todos los tipos disponibles en items(type: x) de la API de Tarkov
ITEM_TYPES = [
    "ammo", "ammoBox", "armor", "armorPlate", "backpack",
    "barter", "container", "glasses", "grenade", "gun",
    "headphones", "helmet", "injectors", "keys", "markedOnly",
    "meds", "mods", "pistolGrip", "poster", "preset",
    "rig", "specialSlot", "suppressor", "wearable"
]


"""
📡 Obtener items de un tipo desde la API de Tarkov
"""
def obtener_items(item_type: str):
    url = "https://api.tarkov.dev/graphql"

    query = """
    {
      items(type: %s) {
        basePrice
        category {
          name
        }
        description
        name
        shortName
        normalizedName
        minLevelForFlea
        lastLowPrice
        types
        buyFor {
          currency
          price
          vendor {
            name
          }
        }
        sellFor {
          currency
          price
          vendor {
            name
          }
        }
        receivedFromTasks {
          name
        }
        usedInTasks {
          name
        }
      }
    }
    """ % item_type

    response = requests.post(url, json={"query": query})

    if response.status_code != 200:
        raise Exception(f"Error {response.status_code} al consultar tipo '{item_type}'")

    data = response.json()

    if "errors" in data:
        print(f"⚠️  Errores en la query para '{item_type}': {data['errors']}")
        return []

    return data.get("data", {}).get("items", [])


"""
📄 Convertir items JSON → Documents de LangChain
"""
def convertir_a_documentos(items, item_type: str):
    documentos = []

    for item in items:
        texto = []

        texto.append(f"Item: {item.get('name', '')}")
        texto.append(f"Short Name: {item.get('shortName', '')}")
        texto.append(f"Type: {item_type}")
        texto.append(f"Category: {item.get('category', {}).get('name', '')}")
        texto.append(f"Description: {item.get('description', '')}")
        texto.append(f"Base Price: {item.get('basePrice', 'N/A')}")
        texto.append(f"Flea Market Level: {item.get('minLevelForFlea', 'N/A')}")
        texto.append(f"Last Low Price: {item.get('lastLowPrice', 'N/A')}")

        # Precios de compra
        for buy in item.get("buyFor", []):
            vendor = buy.get("vendor", {}).get("name", "Unknown")
            texto.append(f"Buy from {vendor}: {buy.get('price', '?')} {buy.get('currency', '')}")

        # Precios de venta
        for sell in item.get("sellFor", []):
            vendor = sell.get("vendor", {}).get("name", "Unknown")
            texto.append(f"Sell to {vendor}: {sell.get('price', '?')} {sell.get('currency', '')}")

        # Tareas relacionadas
        for task in item.get("receivedFromTasks", []):
            texto.append(f"Received from task: {task.get('name', '')}")
        for task in item.get("usedInTasks", []):
            texto.append(f"Used in task: {task.get('name', '')}")

        contenido = "\n".join(texto)

        documentos.append(
            Document(
                page_content=contenido,
                metadata={
                    "item_name": item.get("name", ""),
                    "item_type": item_type,
                    "category": item.get("category", {}).get("name", ""),
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
🧠 Crear embeddings (reutiliza el mismo modelo que tasks)
"""
def crear_embeddings():
    return OllamaEmbeddings(
        model="mxbai-embed-large",
        base_url="http://localhost:11434",
    )


"""
🗄️ Crear / cargar vectorstore para un tipo de item
"""
def crear_vectorstore(embeddings, collection_name: str, chunks=None):
    vectorstore = Chroma(
        persist_directory=CHROMA_DIR,
        embedding_function=embeddings,
        collection_name=collection_name
    )

    num_docs = vectorstore._collection.count()

    if num_docs == 0 and chunks:
        print(f"  💾 Guardando {len(chunks)} chunks en '{collection_name}'...")
        vectorstore.add_documents(chunks)
    else:
        print(f"  ℹ️  '{collection_name}' ya tiene {num_docs} documentos, se omite.")

    return vectorstore


"""
🚀 Main: Crear una colección por cada tipo de item
"""
def main():
    embeddings = crear_embeddings()
    print("🧠 Embeddings listos\n")

    for item_type in ITEM_TYPES:
        collection_name = f"tarkov_items_{item_type}"
        print(f"📡 Procesando tipo: {item_type} → colección: {collection_name}")

        try:
            items = obtener_items(item_type)
            print(f"  📦 Items obtenidos: {len(items)}")

            if not items:
                print(f"  ⏭️  Sin datos para '{item_type}', saltando...")
                continue

            documentos = convertir_a_documentos(items, item_type)
            print(f"  📄 Documentos creados: {len(documentos)}")

            chunks = partir_documentos(documentos)
            print(f"  ✂️  Chunks generados: {len(chunks)}")

            crear_vectorstore(embeddings, collection_name, chunks)
            print(f"  ✅ Colección '{collection_name}' lista\n")

        except Exception as e:
            print(f"  ❌ Error procesando '{item_type}': {e}\n")
            continue

    print("🎉 Todas las colecciones de items han sido procesadas.")


if __name__ == "__main__":
    main()