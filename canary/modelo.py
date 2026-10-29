"""Um classificador de sentimento minúsculo e as "versões" dele que vamos colocar em canary.

O modelo é de propósito simples (palavras-chave): o foco do projeto não é o modelo,
é COMO uma versão nova dele chega aos usuários sem quebrar produção.

Cada `Versao` pode carregar um defeito, para simular o que acontece num rollout real:
- erro:        fração das chamadas que falham (HTTP 500)
- lentidao:    multiplica a latência
- vies:        fração das previsões que "puxa" para 'positiva' — o modelo continua
               respondendo 200, rápido e sem erro, mas passou a decidir diferente
- cold_start:  quantas chamadas iniciais são lentas (a versão acabou de subir)
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

POSITIVAS = {"ótimo", "excelente", "adorei", "recomendo", "perfeito", "rápido", "bom", "maravilhoso"}
NEGATIVAS = {"péssimo", "horrível", "quebrou", "atrasou", "ruim", "defeito", "decepcionante", "nunca"}

CLASSES = ("positiva", "negativa", "neutra")


def classificar(texto: str) -> str:
    palavras = set(texto.lower().replace(",", " ").replace(".", " ").split())
    pos, neg = len(palavras & POSITIVAS), len(palavras & NEGATIVAS)
    if pos > neg:
        return "positiva"
    if neg > pos:
        return "negativa"
    return "neutra"


@dataclass
class Versao:
    nome: str
    erro: float = 0.0
    lentidao: float = 1.0
    vies: float = 0.0
    cold_start: int = 0
    latencia_base_ms: float = 40.0
    _chamadas: int = field(default=0, repr=False)

    def chamar(self, texto: str, rng: random.Random) -> tuple[int, str | None, float]:
        """Devolve (status HTTP, previsão, latência em ms) — igual a uma Function URL."""
        self._chamadas += 1
        latencia = max(1.0, rng.gauss(self.latencia_base_ms, 6)) * self.lentidao
        if self._chamadas <= self.cold_start:
            latencia += rng.uniform(2500, 5500)  # carregar modelo e dependências
        if rng.random() < self.erro:
            return 500, None, latencia
        previsao = classificar(texto)
        if previsao != "positiva" and rng.random() < self.vies:
            previsao = "positiva"
        return 200, previsao, latencia
