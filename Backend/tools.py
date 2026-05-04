import requests
from langchain.tools import tool

# CREACIÓN DE HERRAMIENTAS PERSONALIZADAS (Ejemplo de herramienta de mapas)
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

    url = "https://api.tarkov.dev/graphql"
    print(category)
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

