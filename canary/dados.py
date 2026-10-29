"""Avaliações de produtos geradas a partir de modelos de frase (sem dados reais de ninguém)."""

from __future__ import annotations

import itertools
import random

PRODUTOS = ["o fone", "a cadeira", "o notebook", "a mochila", "o liquidificador", "a entrega", "o curso"]

MODELOS = {
    "positiva": [
        "Adorei {p}, chegou rápido e é ótimo.",
        "{P} é excelente, recomendo.",
        "Perfeito, {p} superou o que eu esperava.",
        "Muito bom, {p} vale cada centavo.",
        "{P} é maravilhoso, comprei de novo.",
    ],
    "negativa": [
        "{P} quebrou na primeira semana, péssimo.",
        "Horrível, {p} atrasou e veio com defeito.",
        "{P} é ruim, não compraria de novo.",
        "Decepcionante, {p} nunca funcionou direito.",
    ],
    "neutra": [
        "{P} chegou dentro do prazo.",
        "Comprei {p} para presente.",
        "{P} é igual ao da foto.",
    ],
}


def avaliacoes() -> list[tuple[str, str]]:
    """Lista de (texto, classe esperada)."""
    linhas = []
    for (classe, modelos), produto in itertools.product(MODELOS.items(), PRODUTOS):
        for modelo in modelos:
            linhas.append((modelo.format(p=produto, P=produto.capitalize()), classe))
    return linhas


def amostrar(n: int, rng: random.Random) -> list[str]:
    textos = [t for t, _ in avaliacoes()]
    return [rng.choice(textos) for _ in range(n)]
