"""Normalización de texto compartida por el catálogo, el enrutador y las entidades."""
import re
import unicodedata

PALABRAS_VACIAS = {
    "a", "al", "algo", "algun", "alguna", "alguno", "cual", "cuales", "como", "con", "de", "del",
    "el", "en", "es", "esta", "estan", "hay", "la", "las", "lo", "los", "me", "mi", "mis", "o",
    "para", "por", "que", "quien", "quienes", "se", "si", "su", "sus", "tiene", "tienen", "tu",
    "un", "una", "unas", "uno", "unos", "y", "ya", "mas", "muy", "este", "esta", "esto", "ese",
}

NUMEROS = {
    "un": 1, "uno": 1, "una": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5,
    "seis": 6, "siete": 7, "ocho": 8, "nueve": 9, "diez": 10,
}


def normalizar(texto: str) -> str:
    """Minúsculas y sin tildes: 'Audífonos' -> 'audifonos'."""
    sin_tildes = unicodedata.normalize("NFKD", texto or "")
    sin_tildes = "".join(c for c in sin_tildes if not unicodedata.combining(c))
    return sin_tildes.lower()


def palabras(texto: str) -> list[str]:
    return re.findall(r"[a-z0-9]+(?:[-.][a-z0-9]+)*", normalizar(texto))


def singular(palabra: str) -> str:
    """Quita la 's' final: 'cables' -> 'cable', 'audifonos' -> 'audifono'.

    Alcanza para buscar por subcadena; los plurales en '-es' se resuelven con
    `formas`, que prueba también sin 'es' ('routeres' no, 'redes' -> 'red')."""
    if len(palabra) > 3 and palabra.endswith("s") and not palabra[-2].isdigit():
        return palabra[:-1]
    return palabra


def formas(palabra: str) -> list[str]:
    """Candidatas para buscar en un vocabulario: tal cual, sin 's' y sin 'es'."""
    candidatas = [palabra, singular(palabra)]
    if len(palabra) > 4 and palabra.endswith("es"):
        candidatas.append(palabra[:-2])
    return list(dict.fromkeys(candidatas))
