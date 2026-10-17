"""Elige la función de la tabla más parecida a la consulta.

Por defecto compara n-gramas de caracteres (TF-IDF), que no necesita
descargar modelos. Con AGENTE_EMBEDDINGS=1 y sentence-transformers instalado
usa embeddings multilingües. En los dos casos el puntaje de una función es la
mayor similitud coseno contra sus ejemplos, y por debajo del umbral el agente
pide que se reformule en vez de adivinar.
"""
import os
from dataclasses import dataclass

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

from .funciones import FUNCIONES

UMBRAL = 0.3
MODELO_EMBEDDINGS = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


@dataclass
class Eleccion:
    funcion: str
    similitud: float
    puntajes: dict[str, float]
    metodo: str

    @property
    def segura(self) -> bool:
        return self.similitud >= UMBRAL


class Enrutador:
    def __init__(self, extractor, usar_embeddings: bool | None = None):
        self.extractor = extractor
        self.etiquetas = [f["nombre"] for f in FUNCIONES for _ in f["ejemplos"]]
        plantillas = [extractor.extraer(ej).plantilla for f in FUNCIONES for ej in f["ejemplos"]]
        if usar_embeddings is None:
            usar_embeddings = os.getenv("AGENTE_EMBEDDINGS") == "1"
        self._modelo = None
        if usar_embeddings:
            from sentence_transformers import SentenceTransformer
            self._modelo = SentenceTransformer(MODELO_EMBEDDINGS)
            self.metodo = f"embeddings ({MODELO_EMBEDDINGS.split('/')[-1]})"
            self._ejemplos = self._modelo.encode(plantillas, normalize_embeddings=True)
        else:
            self._tfidf = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4), sublinear_tf=True)
            self._ejemplos = self._tfidf.fit_transform(plantillas)
            self.metodo = "tf-idf de caracteres"

    def _similitudes(self, plantilla: str) -> np.ndarray:
        if self._modelo is not None:
            return self._ejemplos @ self._modelo.encode([plantilla], normalize_embeddings=True)[0]
        # Los vectores TF-IDF ya vienen normalizados: el producto es el coseno.
        return (self._ejemplos @ self._tfidf.transform([plantilla]).T).toarray().ravel()

    def elegir(self, plantilla: str) -> Eleccion:
        sims = self._similitudes(plantilla)
        puntajes: dict[str, float] = {}
        for etiqueta, s in zip(self.etiquetas, sims):
            puntajes[etiqueta] = max(puntajes.get(etiqueta, 0.0), round(float(s), 3))
        funcion = max(puntajes, key=puntajes.get)
        return Eleccion(funcion, puntajes[funcion], dict(sorted(puntajes.items(), key=lambda x: -x[1])), self.metodo)
