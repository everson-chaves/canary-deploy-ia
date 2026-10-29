"""O "alias ponderado": decide, a cada requisição, qual versão atende.

É o mesmo papel do alias `producao` do AWS Lambda com `AdditionalVersionWeights`:
a versão estável fica com (1 - peso) do tráfego e a candidata com `peso`.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from canary.modelo import Versao


@dataclass
class Resposta:
    versao: str
    status: int
    previsao: str | None
    latencia_ms: float


class AliasPonderado:
    def __init__(self, estavel: Versao, candidata: Versao, peso: float, rng: random.Random):
        if not 0 <= peso <= 1:
            raise ValueError("peso precisa estar entre 0 e 1")
        self.estavel, self.candidata, self.peso, self.rng = estavel, candidata, peso, rng

    def chamar(self, texto: str) -> Resposta:
        versao = self.candidata if self.rng.random() < self.peso else self.estavel
        status, previsao, latencia = versao.chamar(texto, self.rng)
        return Resposta(versao.nome, status, previsao, latencia)
