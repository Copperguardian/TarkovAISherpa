from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document
import requests

CHROMA_DIR = "./chroma_db"
COLLECTION_NAME = "tarkov_tasks"


"""
📡 Obtener datos desde la API de Tarkov
"""
def obtener_tareas():
    url = "https://api.tarkov.dev/graphql"

    query = """
    {
      tasks {
        name
        objectives {
        id
        optional
        type
        description
        maps {
            name
        }
        }
        trader {
        name
        }
        finishRewards {
        items {
            count
            item {
            name
            }
            quantity
        }
        craftUnlock {
            level
            station {
            levels {
                level
            }
            }
        }
        achievement {
            name
            normalizedRarity
        }
        }
        startRewards {
        skillLevelReward {
            name
            level
            skill {
            name
            }
        }
        }
        taskRequirements {
        status
        }
    }
    }
    """

    response = requests.post(url, json={"query": query})

    if response.status_code != 200:
        raise Exception(f"Error {response.status_code}")

    return response.json()["data"]["tasks"]


"""
📄 Convertir JSON → Documents
"""
def convertir_a_documentos(tasks):
    documentos = []

    for task in tasks:
        texto = []

        texto.append(f"Task: {task.get('name', '')}")
        texto.append(f"Trader: {task.get('trader', {}).get('name', '')}")

        # Objectives
        for obj in task.get("objectives", []):
            texto.append(f"Objective: {obj.get('description', '')}")
            maps = [m.get("name") for m in obj.get("maps", [])]
            if maps:
                texto.append(f"Maps: {', '.join(maps)}")

        # Rewards
        for item in task.get("finishRewards", {}).get("items", []):
            texto.append(f"Reward: {item.get('item', {}).get('name')} x{item.get('count')}")

        contenido = "\n".join(texto)

        documentos.append(
            Document(
                page_content=contenido,
                metadata={"task_name": task.get("name", "")}
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

    if num_docs == 0:
        print("Guardando tareas en Chroma...")
        vectorstore.add_documents(chunks)
    else:
        print(f"Ya existen {num_docs} documentos en la colección")

    return vectorstore


def main():
    print("📡 Obteniendo tareas desde la API...")
    tasks = obtener_tareas()
    print(f"Tareas obtenidas: {len(tasks)}")

    documentos = convertir_a_documentos(tasks)
    print(f"Documentos creados: {len(documentos)}")

    chunks = partir_documentos(documentos)
    print(f"Chunks generados: {len(chunks)}")

    embeddings = crear_embeddings()
    print("Embeddings listos")

    crear_vectorstore(embeddings, chunks)

    print("✅ RAG de tareas creado correctamente")


if __name__ == "__main__":
    main()