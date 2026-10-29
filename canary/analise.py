"""A análise do canary: compara candidata x estável e decide PROMOVER ou ROLLBACK.

Critérios (todos precisam passar):
1. taxa de erro da candidata ≤ 2% e no máximo 1 p.p. acima da estável
2. latência p95 da candidata ≤ 1,5 × a da estável
3. distribuição das previsões a no máximo 15 p.p. da estável, em cada classe

O terceiro critério não existe num serviço comum. Num modelo, ele pega a
regressão silenciosa: a versão nova responde 200, rápido, e decide diferente.
"""

from __future__ import annotations

import statistics
from collections import Counter
from dataclasses import dataclass, field

from canary.modelo import CLASSES
from canary.roteador import Resposta

LIMITE_ERRO = 0.02
LIMITE_ERRO_DELTA = 0.01
LIMITE_P95 = 1.5
LIMITE_DISTRIBUICAO = 0.15


@dataclass
class Metricas:
    versao: str
    requisicoes: int
    taxa_erro: float
    p95_ms: float
    distribuicao: dict[str, float]


@dataclass
class Decisao:
    promover: bool
    motivos: list[str] = field(default_factory=list)


def p95(valores: list[float]) -> float:
    if len(valores) < 2:
        return valores[0] if valores else 0.0
    return statistics.quantiles(valores, n=20)[-1]


def medir(respostas: list[Resposta], versao: str) -> Metricas:
    da_versao = [r for r in respostas if r.versao == versao]
    ok = [r for r in da_versao if r.status == 200]
    contagem = Counter(r.previsao for r in ok)
    total_ok = max(len(ok), 1)
    return Metricas(
        versao=versao,
        requisicoes=len(da_versao),
        taxa_erro=1 - len(ok) / max(len(da_versao), 1),
        p95_ms=p95([r.latencia_ms for r in da_versao]),
        distribuicao={c: contagem[c] / total_ok for c in CLASSES},
    )


def decidir(estavel: Metricas, candidata: Metricas) -> Decisao:
    motivos = []
    if candidata.requisicoes == 0:
        return Decisao(False, ["a candidata não recebeu tráfego"])
    if candidata.taxa_erro > LIMITE_ERRO or candidata.taxa_erro > estavel.taxa_erro + LIMITE_ERRO_DELTA:
        motivos.append(f"taxa de erro {candidata.taxa_erro:.1%} (estável {estavel.taxa_erro:.1%})")
    if candidata.p95_ms > LIMITE_P95 * estavel.p95_ms:
        motivos.append(f"p95 {candidata.p95_ms:.0f} ms > 1,5 × {estavel.p95_ms:.0f} ms")
    for classe in CLASSES:
        delta = abs(candidata.distribuicao[classe] - estavel.distribuicao[classe])
        if delta > LIMITE_DISTRIBUICAO:
            motivos.append(f"previsões '{classe}' mudaram {delta:.0%}")
    return Decisao(not motivos, motivos)


def tabela(*metricas: Metricas) -> str:
    linhas = ["| versão | req. | erro | p95 | positiva | negativa | neutra |", "|---|---|---|---|---|---|---|"]
    for m in metricas:
        d = m.distribuicao
        linhas.append(
            f"| {m.versao} | {m.requisicoes} | {m.taxa_erro:.1%} | {m.p95_ms:.0f} ms | "
            f"{d['positiva']:.0%} | {d['negativa']:.0%} | {d['neutra']:.0%} |"
        )
    return "\n".join(linhas)
