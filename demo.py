"""Roda um canary de ponta a ponta e decide sozinho: PROMOVER ou ROLLBACK.

    python demo.py                         # roda todos os cenários
    python demo.py --cenario drift         # só um
    python demo.py --cenario cold_start --requisicoes 1000

Com --esperado (usado no CI), o processo sai com 0 se a decisão foi a esperada.
"""

from __future__ import annotations

import argparse
import os
import random
import sys

from canary.analise import decidir, medir, tabela
from canary.dados import amostrar
from canary.modelo import Versao
from canary.roteador import AliasPonderado

CENARIOS = {
    "saudavel": ("Versão nova saudável", dict()),
    "erro": ("Versão nova falha em 20% das chamadas", dict(erro=0.20)),
    "lenta": ("Versão nova 2× mais lenta", dict(lentidao=2.0)),
    "drift": ("Versão nova 'mudou de opinião': 0% de erro, mas puxa 40% das previsões para positiva", dict(vies=0.40)),
    "cold_start": ("Versão nova saudável, mas as 3 primeiras chamadas são frias (cold start)", dict(cold_start=3)),
}


def rodar(cenario: str, requisicoes: int, peso: float, seed: int) -> tuple[bool, str]:
    descricao, defeitos = CENARIOS[cenario]
    rng = random.Random(seed)
    alias = AliasPonderado(Versao("v1-estavel"), Versao("v2-canary", **defeitos), peso, rng)
    respostas = [alias.chamar(t) for t in amostrar(requisicoes, rng)]

    estavel, candidata = medir(respostas, "v1-estavel"), medir(respostas, "v2-canary")
    decisao = decidir(estavel, candidata)

    veredito = "✅ PROMOVER — canary saudável" if decisao.promover else "❌ ROLLBACK — " + "; ".join(decisao.motivos)
    relatorio = (
        f"### Cenário `{cenario}`: {descricao}\n\n"
        f"{requisicoes} requisições, {peso:.0%} para o canary\n\n"
        f"{tabela(estavel, candidata)}\n\n**{veredito}**\n"
    )
    return decisao.promover, relatorio


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--cenario", choices=[*CENARIOS, "todos"], default="todos")
    parser.add_argument("--requisicoes", type=int, default=1000)
    parser.add_argument("--peso", type=float, default=0.1)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--esperado", choices=["promover", "rollback"])
    args = parser.parse_args()

    cenarios = list(CENARIOS) if args.cenario == "todos" else [args.cenario]
    resultados = []
    for cenario in cenarios:
        promoveu, relatorio = rodar(cenario, args.requisicoes, args.peso, args.seed)
        print(relatorio)
        resultados.append(promoveu)
        if resumo := os.environ.get("GITHUB_STEP_SUMMARY"):
            with open(resumo, "a", encoding="utf-8") as f:
                f.write(relatorio + "\n")

    if args.esperado:
        esperado = args.esperado == "promover"
        ok = all(r == esperado for r in resultados)
        print(f"Decisão {'igual' if ok else 'DIFERENTE'} da esperada ({args.esperado}).")
        return 0 if ok else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
