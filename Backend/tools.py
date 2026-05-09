import requests
from langchain.tools import tool
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings
import os
from langchain_core.runnables import RunnableConfig

# Setup for RAG
CHROMA_DIR = "../Rag/chroma_db"
COLLECTION_NAME_TASKS = "tarkov_tasks"

# Todos los tipos de items disponibles (coincide con create_collections.py)
ITEM_TYPES = [
    "ammo", "ammoBox", "armor", "armorPlate", "backpack",
    "barter", "container", "glasses", "grenade", "gun",
    "headphones", "helmet", "injectors", "keys", "markedOnly",
    "meds", "mods", "pistolGrip", "poster", "preset",
    "rig", "specialSlot", "suppressor", "wearable"
]

def get_embeddings():
    return OllamaEmbeddings(
        model="mxbai-embed-large",
        base_url="http://localhost:11434",
    )

def get_vectorstore(collection_name=COLLECTION_NAME_TASKS):
    embeddings = get_embeddings()
    return Chroma(
        persist_directory=CHROMA_DIR,
        embedding_function=embeddings,
        collection_name=collection_name
    )

vectorstore = get_vectorstore()

# CREACIÓN DE HERRAMIENTAS PERSONALIZADAS (Ejemplo de herramienta de mapas)
@tool
def get_multiAmmo(calibers: list = None):
    """
    Consulta la API de Tarkov para obtener todas las balas de uno o varios calibres.
    Argumentos:
        calibers (list): Una lista de strings con los calibres, ej: ["9x19", "86x70"]
    Consulta la API de Tarkov para obtener todas las balas de un calibre. Si el usuario especifica un calibre, filtra por ese tipo. 5.56x45mm -> 556X45. 
    Las entradas está estandarizadas de la siguiente forma: 9x19, 556x45, 762x39, etc. Extrapola según lo que pide el usuario, pero si no puedes identificar el calibre, devuelve la lista completa.
    Las entradas SIEMPRE siguen el formato: [calibre]x[longitud], pero el usuario puede escribirlo de cualquier forma, así que haz tu mejor esfuerzo para identificarlo.
    Las entradas NUNCA llevan punto decimal ni espacios así que extrapola también en ese sentido: 0.45 -> 45, 9 mm -> 9x19, etc.
    El calibre 12 de escopeta es un caso especial, ya que no sigue el formato estándar. Si el usuario menciona "calibre 12", "12 gauge" o simplemente "12" se debe buscar como 12g.
    Lo mismo se aplica para el calibre de escopeta 20, que se debe buscar como 20g.
    El calibre .45 acp se debe buscar como 45acp o 1143x23, ya que es un caso especial que no sigue el formato estándar.
    Las granadas de 40mm se deben buscar como 40x46, ya que también son un caso especial.
    El calibre .338 lapua se debe buscar como 86x70.
    El calibre 50 de Desert Eagle se debe buscar como 127x33.
    El calibre .357 de Revolver se debe buscar como 9x33, ya que es un caso especial que no sigue el formato estándar.
    El calibre .366 tkm se debe buscar como 366, ya que es un caso especial que no sigue el formato estándar.
    El calibre .300 blackout se debe buscar como 762x35, ya que es un caso especial que no sigue el formato estándar.
    El calibre de .308me de fusil de palanca se debe buscar como 784x49, ya que es un caso especial que no sigue el formato estándar.
    El calibre .50BMG se debe buscar como 127x99, ya que es un caso especial que no sigue el formato estándar.
    Si el usuario menciona calibre 762 sin especificar, sal de la herramienta y pregúntale si se refiere a 762x39, 762x51 o 762x54, ya que son los calibres de 7.62 más comunes en el juego.
    """
    url = "https://api.tarkov.dev/graphql"
    print("Se ha ejecutado get_multiAmmo")
    new_query = """
    {
        ammo {
            item {
                description
                name
            }
            ammoType
            accuracyModifier
            armorDamage
            caliber
            damage
            fragmentationChance
            heavyBleedModifier
            initialSpeed
            lightBleedModifier
            penetrationPower
            ricochetChance
            recoilModifier
            tracer
            tracerColor
        }
    }
    """

    headers = {"Content-Type": "application/json"}
    try:
        response = requests.post(url, headers=headers, json={'query': new_query})
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise Exception(f"Query failed: {e}")

    data = response.json()["data"]["ammo"]

    # 🔍 Si no se pasan calibres o la lista está vacía → devuelve todo
    if not calibers:
        return data

    # Normalizamos todos los calibres de entrada a minúsculas para comparar
    calibers_lower = [c.lower() for c in calibers]

    # 🎯 Filtro: Si el calibre de la bala coincide con CUALQUIERA de la lista
    resultado = [
        ammo for ammo in data
        if any(c_input in ammo.get("caliber", "").lower() for c_input in calibers_lower)
    ]

    # ❗ Si no hay coincidencias tras filtrar → devuelve todo (según tu lógica original)
    return resultado if resultado else data

@tool
def get_ammo(caliber: str):
    """
    Consulta la API de Tarkov para obtener todas las balas de un calibre. Si el usuario especifica un calibre, filtra por ese tipo. 5.56x45mm -> 556X45. 
    Las entradas está estandarizadas de la siguiente forma: 9x19, 556x45, 762x39, etc. Extrapola según lo que pide el usuario, pero si no puedes identificar el calibre, devuelve la lista completa.
    Las entradas SIEMPRE siguen el formato: [calibre]x[longitud], pero el usuario puede escribirlo de cualquier forma, así que haz tu mejor esfuerzo para identificarlo.
    Las entradas NUNCA llevan punto decimal ni espacios así que extrapola también en ese sentido: 0.45 -> 45, 9 mm -> 9x19, etc.
    El calibre 12 de escopeta es un caso especial, ya que no sigue el formato estándar. Si el usuario menciona "calibre 12", "12 gauge" o simplemente "12" se debe buscar como 12g.
    Lo mismo se aplica para el calibre de escopeta 20, que se debe buscar como 20g.
    El calibre .45 acp se debe buscar como 45acp o 1143x23, ya que es un caso especial que no sigue el formato estándar.
    Las granadas de 40mm se deben buscar como 40x46, ya que también son un caso especial.
    El calibre .338 lapua se debe buscar como 86x70.
    El calibre 50 de Desert Eagle se debe buscar como 127x33.
    El calibre .357 de Revolver se debe buscar como 9x33, ya que es un caso especial que no sigue el formato estándar.
    El calibre .366 tkm se debe buscar como 366, ya que es un caso especial que no sigue el formato estándar.
    El calibre .300 blackout se debe buscar como 762x35, ya que es un caso especial que no sigue el formato estándar.
    El calibre de .308me de fusil de palanca se debe buscar como 784x49, ya que es un caso especial que no sigue el formato estándar.
    El calibre .50BMG se debe buscar como 127x99, ya que es un caso especial que no sigue el formato estándar.
    Si el usuario menciona calibre 762 sin especificar, sal de la herramienta y pregúntale si se refiere a 762x39, 762x51 o 762x54, ya que son los calibres de 7.62 más comunes en el juego.
    """
    url = "https://api.tarkov.dev/graphql"

    print(caliber)

    new_query = """
    {
        ammo {
            item {
                description
                name
            }
            ammoType
            accuracyModifier
            armorDamage
            caliber
            damage
            fragmentationChance
            heavyBleedModifier
            initialSpeed
            lightBleedModifier
            penetrationPower
            ricochetChance
            recoilModifier
            tracer
            tracerColor
        }
    }
    """

    headers = {"Content-Type": "application/json"}
    response = requests.post(url, headers=headers, json={'query': new_query})

    if response.status_code != 200:
        raise Exception("Query failed to run by returning code of {}. {}".format(response.status_code, new_query))

    data = response.json()["data"]["ammo"]

    # 🔍 Si no hay filtro → devuelve todo
    if not caliber:
        return data

    caliber = caliber.lower()

    # 🎯 Filtro generoso (contains)
    resultado = [
        ammo for ammo in data
        if caliber in ammo.get("caliber", "").lower()
    ]
    print(resultado)

    # ❗ Si no hay coincidencias → devuelve todo
    return resultado if resultado else data


@tool
def get_weapons_by_caliber(caliber: str):
    """
    Consulta la API de Tarkov para obtener todas las armas que usan un calibre en particular. Si el usuario especifica un calibre, filtra por ese tipo. 5.56x45mm -> 556X45. 
    Las entradas está estandarizadas de la siguiente forma: 9x19, 556x45, 762x39, etc. Extrapola según lo que pide el usuario, pero si no puedes identificar el calibre, devuelve la lista completa.
    Las entradas SIEMPRE siguen el formato: [calibre]x[longitud], pero el usuario puede escribirlo de cualquier forma, así que haz tu mejor esfuerzo para identificarlo.
    Las entradas NUNCA llevan punto decimal ni espacios así que extrapola también en ese sentido: 0.45 -> 45, 9 mm -> 9x19, etc.
    El calibre 12 de escopeta es un caso especial, ya que no sigue el formato estándar. Si el usuario menciona "calibre 12", "12 gauge" o simplemente "12" se debe buscar como 12g.
    Lo mismo se aplica para el calibre de escopeta 20, que se debe buscar como 20g.
    El calibre .45 acp se debe buscar como 45acp o 1143x23, ya que es un caso especial que no sigue el formato estándar.
    Las granadas de 40mm se deben buscar como 40x46, ya que también son un caso especial.
    El calibre .338 lapua se debe buscar como 86x70.
    El calibre 50 de Desert Eagle se debe buscar como 127x33.
    El calibre .357 de Revolver se debe buscar como 9x33, ya que es un caso especial que no sigue el formato estándar.
    El calibre .366 tkm se debe buscar como 366, ya que es un caso especial que no sigue el formato estándar.
    El calibre .300 blackout se debe buscar como 762x35, ya que es un caso especial que no sigue el formato estándar.
    El calibre de .308me de fusil de palanca se debe buscar como 784x49, ya que es un caso especial que no sigue el formato estándar.
    El calibre .50BMG se debe buscar como 127x99, ya que es un caso especial que no sigue el formato estándar.
    Si el usuario menciona calibre 762 sin especificar, sal de la herramienta y pregúntale si se refiere a 762x39, 762x51 o 762x54, ya que son los calibres de 7.62 más comunes en el juego.
    """

    url = "https://api.tarkov.dev/graphql"
    print("Se ha ejecutado get_weapons_by_caliber")
    print(caliber)
    
    query = """
    {
      items(type: gun) {
        basePrice
        description
        name
        normalizedName
        shortName
        velocity
        properties {
          ... on ItemPropertiesWeapon {
            caliber
            effectiveDistance
            ergonomics
            fireModes
            fireRate
            recoilVertical
            recoilHorizontal
          }
        }
      }
    }
    """

    headers = {"Content-Type": "application/json"}
    response = requests.post(url, headers=headers, json={'query': query})

    if response.status_code != 200:
        raise Exception(f"Query failed with code {response.status_code}")

    data = response.json()["data"]["items"]

    # 🔍 Sin filtro → todo
    if not caliber:
        return data

    caliber = caliber.lower()

    # 🎯 Filtro generoso sobre properties.caliber
    resultado = [
        weapon for weapon in data
        if caliber in (weapon.get("properties", {}).get("caliber", "").lower())
    ]
    print(resultado)
    # ❗ Sin coincidencias → todo
    return resultado if resultado else data

@tool
def get_weapons_by_name(name: str):
    """
    Consulta la API de Tarkov para obtener todas las armas que coincidan con un nombre o parte de un nombre. El filtro debe ser generoso, es decir, si el usuario escribe "ak", debería devolver armas como "AK-74N", "AKM", "AK-12", etc. 
    El filtro se debe aplicar sobre los campos "name" y "shortName" de cada arma en la base de datos. Si el usuario no especifica ningún nombre, devuelve la lista completa de armas.
    """
    url = "https://api.tarkov.dev/graphql"
    
    print(name)
    
    query = """
    {
      items(type: gun) {
        basePrice
        description
        name
        normalizedName
        shortName
        velocity
        properties {
          ... on ItemPropertiesWeapon {
            caliber
            effectiveDistance
            ergonomics
            fireModes
            fireRate
            recoilVertical
            recoilHorizontal
          }
        }
      }
    }
    """

    headers = {"Content-Type": "application/json"}
    response = requests.post(url, headers=headers, json={'query': query})

    if response.status_code != 200:
        raise Exception(f"Query failed with code {response.status_code}")

    data = response.json()["data"]["items"]

    # 🔍 Sin filtro → todo
    if not name:
        return data

    name = name.lower()

    # 🎯 Filtro generoso sobre name y shortName
    resultado = [
        weapon for weapon in data
        if name in weapon.get("name", "").lower() or name in weapon.get("shortName", "").lower()
    ]
    print(resultado)
    # ❗ Sin coincidencias → todo
    return resultado if resultado else data

@tool
def get_multi_weapons(names: list = None):
    """
    Consulta la API de Tarkov para obtener todas las armas que coincidan con varios nombres o partes de nombres. El filtro debe ser generoso, es decir, si el usuario escribe "ak", debería devolver armas como "AK-74N", "AKM", "AK-12", etc. 
    El filtro se debe aplicar sobre los campos "name" y "shortName" de cada arma en la base de datos. Si el usuario no especifica ningún nombre, devuelve la lista completa de armas.
    
    Args:
        names (list): Lista de strings con los nombres a buscar, ej: ["ak", "m4", "p90"]
    """
    url = "https://api.tarkov.dev/graphql"
    print("Se ha ejecutado get_multi_weapons")
    query = """
    {
      items(type: gun) {
        basePrice
        description
        name
        normalizedName
        shortName
        velocity
        properties {
          ... on ItemPropertiesWeapon {
            caliber
            effectiveDistance
            ergonomics
            fireModes
            fireRate
            recoilVertical
            recoilHorizontal
          }
        }
      }
    }
    """

    headers = {"Content-Type": "application/json"}
    try:
        response = requests.post(url, headers=headers, json={'query': query})
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise Exception(f"Query failed: {e}")

    data = response.json()["data"]["items"]

    # 🔍 Si no se pasan nombres o la lista está vacía → devuelve todo
    if not names:
        return data

    # Normalizamos los términos de búsqueda a minúsculas
    names_lower = [n.lower() for n in names]

    # 🎯 Filtro generoso: comprueba si CUALQUIERA de los términos está en name o shortName
    resultado = [
        weapon for weapon in data
        if any(
            n_input in weapon.get("name", "").lower() or 
            n_input in weapon.get("shortName", "").lower() 
            for n_input in names_lower
        )
    ]

    # ❗ Si no hay coincidencias tras filtrar → devuelve la lista completa
    return resultado if resultado else data

@tool
def get_weapons_by_category(category: str):
    """
    Consulta la API de Tarkov para obtener las armas según la categoría.
    Sé capaz de extrapolar desde lo que el usuario pide a las categorías reales del juego. Por ejemplo, si el usuario menciona "rifles de asalto", "fusiles de asalto" o simplemente "asalto", deberías buscar la categoría "Assault rifle". Si el usuario menciona "ametralladoras ligeras", "lmg" o "machineguns", deberías buscar la categoría "Machinegun". Si el usuario menciona "escopetas", "shotguns" o "escopeta", deberías buscar la categoría "Shotgun". Si el usuario menciona "subfusiles", "metrallletas" o "smg", deberías buscar la categoría "SMG".
   
     Ejemplos de categorías:
    - Assault rifle (se refiere a rifles de asalto en español)
    - Machinegun (se refiere a ametralladoras ligeras en español)
    - Shotgun (se refiere a escopetas en español)
    - SMG (se refiere a subfusiles o metratalletas en español)
    - Sniper rifle (se refiere a rifles de francotirador en español)
    - Marksman rifle (se refiere a rifles de tirador, armas de precisión, en español)
    - Handgun (se refiere a pistolas en español)
    - Revolver (se refiere a revólveres en español, diferencia al lanzagranadas rotativo M32A1 que también es un revolver pero de granadas)
    - Assault carbine (se refiere a carabinas de asalto en español, armas semiautomáticas más cortas y baratas que los rifles de asalto)
    - Grenade launcher (se refiere a lanzagranadas en español)
    Si no hay coincidencias o no se especifica categoría, devuelve la lista completa.
    """
    print("Se ha ejecutado get_weapons_by_category")
    url = "https://api.tarkov.dev/graphql"
    query = """
    {
      items(type: gun) {
        basePrice
        description
        name
        normalizedName
        shortName
        velocity
        properties {
          ... on ItemPropertiesWeapon {
            caliber
            effectiveDistance
            ergonomics
            fireModes
            fireRate
            recoilVertical
            recoilHorizontal
          }
        }
        categories {
          name
        }
      }
    }
    """

    headers = {"Content-Type": "application/json"}
    response = requests.post(url, headers=headers, json={'query': query})

    if response.status_code != 200:
        raise Exception(f"Query failed with code {response.status_code}")

    data = response.json()["data"]["items"]

    # 🔍 Sin filtro → todo
    if not category:
        return data

    category = category.lower()

    # 🎯 Filtro generoso por categorías
    resultado = [
        weapon for weapon in data
        if any(
            category in cat.get("name", "").lower()
            for cat in weapon.get("categories", [])
        )
    ]
    print(resultado)
    # ❗ Sin coincidencias → todo
    return resultado if resultado else data


@tool
def get_armor_materials():
    """
    Consulta la API de Tarkov para obtener todos los materiales de armaduras disponibles en el juego. Esta herramienta es útil para que los jugadores puedan identificar las propiedades de los materiales y así tomar decisiones informadas sobre qué armaduras comprar según sus necesidades y presupuesto.
     Si el usuario menciona un material específico, hablale de ese material en particular.
     Ten en cuenta que materiales como la cerámica o el acero pueden ser peores en términos de protección que materiales más avanzados como el titanio o el polimero, pero suelen ser más baratos. Por otro lado, materiales como el acero pueden ser más pesados y afectar la movilidad del jugador, mientras que materiales como el polimero son más ligeros. Si el usuario pregunta por un material específico, enfócate en las ventajas y desventajas de ese material en particular para ayudarle a decidir si es adecuado para su estilo de juego y presupuesto.
     Materiales como el cristal o aramida son bastante específicos para piezas de armadura en particular como visores para el cristal o armadruas básicas para la aramida así que ten en cuenta que no suelen poder parar calibres altos.
     El mejor material en general suele ser el UHMWPE, que es un tipo de polimero de ultra alta masa molecular, ya que tiene una excelente relación protección-peso y puede ser más resistente que el acero o la cerámica en algunos casos. Sin embargo, también es importante destacar que estas placas pueden ser muy caras o difíciles de conseguir, por lo que no siempre son la mejor opción para todos los jugadores. El titanio también es un material de alta calidad que ofrece una buena protección y es más ligero que el acero, pero suele ser más caro. En general, la elección del material dependerá de las necesidades específicas del jugador, su estilo de juego y su presupuesto.
     
    """
    url = "https://api.tarkov.dev/graphql"
    print("Se ha ejecutado get_armor_materials")
    query = """
    query MyQuery {
      armorMaterials {
        name
        explosionDestructibility
        destructibility
        maxRepairDegradation
        maxRepairKitDegradation
        minRepairDegradation
        minRepairKitDegradation
      }
    }
    """

    headers = {"Content-Type": "application/json"}
    
    try:
        response = requests.post(url, headers=headers, json={'query': query})
        response.raise_for_status()
        
        data = response.json()
        
        # Devolvemos directamente la lista de materiales dentro del JSON
        return data["data"]["armorMaterials"]
        
    except requests.exceptions.RequestException as e:
        raise Exception(f"Error al conectar con la API de Tarkov: {e}")
    except KeyError:
        raise Exception("La estructura de la respuesta de la API ha cambiado o es inesperada.")
    pass

@tool
def search_tasks(query: str):
  """
  Busca tareas/misiones de Tarkov utilizando Generación Aumentada por Recuperación (RAG).
  Proporciona una consulta en lenguaje natural para encontrar tareas relevantes en la base de datos de Tarkov.
  Esta herramienta recupera tareas que coinciden con la consulta basándose en sus descripciones, objetivos y recompensas.

  Args:
  query (str): El nombre de la tarea que estás buscando o una descripción general.

  Returns:
  list: Una lista de descripciones de tareas que coinciden con la consulta.

  Utiliza esta herramienta para ayudar a los jugadores a encontrar tareas específicas en Tarkov, proporcionando información detallada sobre cada tarea recuperada.
  No des más información de la que necesita el usuario para identificar la tarea, pero asegúrate de incluir detalles relevantes como el nombre de la tarea, el trader que la ofrece, los objetivos principales y las recompensas, para que el usuario pueda reconocerla fácilmente.
  Si no se encuentra ninguna tarea que coincida con la consulta, devuelve una lista vacía.
  """
  print("----------------------------------------------------------------------------------------")
  print("Se ha ejecutado search_tasks")
  print("Query: ", query)
  try:
      results = vectorstore.similarity_search(query, k=5)
      return [doc.page_content for doc in results]
  except Exception as e:
      return f"Error searching tasks: {str(e)}"

@tool
def search_items(query: str, item_type: str = None):
  """
  Busca items/objetos de Tarkov utilizando Generación Aumentada por Recuperación (RAG).
  Proporciona una consulta en lenguaje natural para encontrar items relevantes en la base de datos.
  Esta herramienta recupera items que coinciden con la consulta basándose en su nombre, descripción, precios y propiedades.

  Args:
    query (str): Lo que el usuario está buscando. Puede ser el nombre del item, una descripción o una pregunta general.
    item_type (str, optional): Tipo de item para filtrar la búsqueda. Si se conoce el tipo, especificarlo
      acelera la búsqueda y mejora la precisión. Tipos válidos:
      ammo, ammoBox, armor, armorPlate, backpack, barter, container, glasses, grenade, gun,
      headphones, helmet, injectors, keys, markedOnly, meds, mods, pistolGrip, poster, preset,
      rig, specialSlot, suppressor, wearable.
      Si no se especifica, se busca en TODAS las colecciones.

  Returns:
    list: Una lista de descripciones de items que coinciden con la consulta.

  Utiliza esta herramienta para ayudar a los jugadores a encontrar información sobre items específicos de Tarkov,
  incluyendo precios de compra/venta, dónde conseguirlos, nivel necesario para el Flea Market y en qué misiones se usan.
  Si el usuario pregunta por un objeto, armadura, mochila, medicamento, modificación de arma, casco, llaves,
  o cualquier otro item del juego que NO sea un arma ni munición directamente, usa esta herramienta.
  Para preguntas sobre armas usa get_weapons_by_name o get_weapons_by_caliber.
  Para preguntas sobre munición usa get_ammo o get_multiAmmo.
  Para preguntas sobre tareas/misiones usa search_tasks.
  """
  print("----------------------------------------------------------------------------------------")
  print("Se ha ejecutado search_items")
  print("Query: ", query, "Item type: ", item_type)
  try:
      # Si se especifica un tipo válido, buscar solo en esa colección
      if item_type and item_type in ITEM_TYPES:
          collection_name = f"tarkov_items_{item_type}"
          item_vs = get_vectorstore(collection_name)
          results = item_vs.similarity_search_with_relevance_scores(query, k=5)
          return [doc.page_content for doc, score in results]

      # Si no se especifica tipo, buscar en TODAS las colecciones
      all_results = []
      for t in ITEM_TYPES:
          collection_name = f"tarkov_items_{t}"
          try:
              item_vs = get_vectorstore(collection_name)
              # Verificar que la colección tenga documentos
              if item_vs._collection.count() == 0:
                  continue
              results = item_vs.similarity_search_with_relevance_scores(query, k=3)
              all_results.extend(results)
          except Exception:
              continue

      # Ordenar por relevancia (score más alto = más relevante) y devolver top 5
      all_results.sort(key=lambda x: x[1], reverse=True)
      top_results = all_results[:5]
      return [doc.page_content for doc, score in top_results]

  except Exception as e:
      return f"Error searching items: {str(e)}"

@tool
def search_hideout(query: str):
  """
  Busca información sobre las estaciones del hideout de Tarkov utilizando Generación Aumentada por Recuperación (RAG).
  Proporciona una consulta en lenguaje natural para encontrar información relevante sobre el hideout.

  Args:
    query (str): Lo que el usuario quiere saber sobre el hideout. Puede ser el nombre de una estación,
      un craft específico, requisitos de construcción, o una pregunta general sobre el hideout.

  Returns:
    list: Una lista de descripciones de estaciones/niveles del hideout que coinciden con la consulta.

  Utiliza esta herramienta cuando el usuario pregunte sobre:
  - Estaciones del hideout (Workbench, Medstation, Lavatory, Water Collector, Generator, Nutrition Unit,
    Intelligence Center, Scav Case, Bitcoin Farm, Shooting Range, Library, Gym, etc.)
  - Requisitos para construir o mejorar una estación (items necesarios, nivel de trader, habilidades, otras estaciones)
  - Crafts disponibles en una estación (qué se puede fabricar, qué materiales se necesitan, cuánto tarda)
  - Bonuses que otorga una estación al mejorarla
  - Tiempo de construcción de una estación
  - Cualquier pregunta relacionada con el hideout, la base del jugador o fabricación de objetos

  NO uses esta herramienta para buscar items sueltos (usa search_items), armas (usa get_weapons_*),
  munición (usa get_ammo/get_multiAmmo) o misiones (usa search_tasks).
  """
  print("----------------------------------------------------------------------------------------")
  print("Se ha ejecutado search_hideout")
  print("Query: ", query)
  try:
      hideout_vs = get_vectorstore("tarkov_hideout")
      results = hideout_vs.similarity_search(query, k=5)
      return [doc.page_content for doc in results]
  except Exception as e:
      return f"Error searching hideout: {str(e)}"

@tool
def get_map_info(query: str):
    """
    Obtiene información sobre los mapas de Tarkov haciendo una llamada directa a la API de tarkov.dev.
    Devuelve datos sobre enemigos, duración del raid, número de jugadores, llaves de acceso y descripción.
    Si el usuario menciona un mapa específico (Customs, Woods, Interchange, Shoreline, Reserve, Labs,
    Factory, Streets of Tarkov, Lighthouse, Ground Zero, etc.), filtra por ese nombre.
    Si no se especifica mapa, devuelve todos los mapas disponibles.

    Args:
        query (str): El nombre del mapa o una descripción de lo que el usuario busca.

    Returns:
        list: Información completa de los mapas que coincidan con la consulta.
    """
    url = "https://api.tarkov.dev/graphql"

    gql_query = """
    {
        maps {
            enemies
            name
            raidDuration
            players
            accessKeys {
                name
            }
            description
        }
    }
    """

    print("----------------------------------------------------------------------------------------")
    print("Se ha ejecutado get_map_info")
    print("Query: ", query)

    headers = {"Content-Type": "application/json"}
    try:
        response = requests.post(url, headers=headers, json={'query': gql_query})
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        return f"Error al conectar con la API de Tarkov: {e}"

    data = response.json().get("data", {}).get("maps", [])

    # Si no hay query o está vacío, devuelve todos los mapas
    if not query:
        return data

    query_lower = query.lower()

    # Filtro generoso por nombre del mapa
    resultado = [
        mapa for mapa in data
        if query_lower in mapa.get("name", "").lower()
    ]

    # Si no hay coincidencias por nombre, devuelve todos
    return resultado if resultado else data

@tool
def get_user_progress(config: RunnableConfig):
    """
    Obtiene el perfil y progreso actual del usuario en Tarkov (facción, nivel, progreso del hideout y estilo de juego)
    desde la base de datos interna. Usa esta herramienta para dar consejos personalizados basados en quién es el usuario.
    Adapta tu respuesta a la información que tienes sobre el usuario. Por ejemplo, si el usuario es un nivel bajo con progreso limitado en el hideout, no le recomiendes tareas o armas que requieran un nivel alto o un hideout avanzado. Si el usuario es de una facción específica, ten en cuenta la historia y los valores de esa facción al recomendarle estrategias, misiones o equipo. Si el usuario tiene un estilo de juego más orientado al PvP, enfócate en consejos para enfrentamientos contra otros jugadores; si es más PvE, sugiere estrategias para sobrevivir contra Scavs y completar misiones.
    No uses esta herramienta sola cuando el usuario te pregunte por alguna otra cosa, como armas, tareas o mapas. Usa esta herramienta para obtener información sobre el usuario y luego adapta tus respuestas a esa información.
    """
    print("----------------------------------------------------------------------------------------")
    print("Se ha ejecutado get_user_progress")
    profile = config.get("configurable", {}).get("user_profile")
    if not profile:
        return "No hay información de perfil disponible para este usuario."
    
    return {
        "faction": profile.get("faction"),
        "level": profile.get("level"),
        "hideout_progress": profile.get("hideout_progress"),
        "playstyle": profile.get("playstyle")
    }
