"""Quantas requisições um canary precisa para decidir certo?

Repete o canary muitas vezes para cada tamanho de amostra e mede duas coisas:
- falso rollback: a versão era SAUDÁVEL e o canary reprovou mesmo assim
- drift detectado: a versão tinha regressão silenciosa e o canary pegou

    python experimento.py            # imprime a tabela e gera docs/amostra.svg
"""

from __future__ import annotations

import random
from pathlib import Path

from canary.analise import decidir, medir
from canary.dados import amostrar
from canary.modelo import Versao
from canary.roteador import AliasPonderado

TAMANHOS = [100, 200, 300, 500, 1000, 2000, 3000]
REPETICOES = 300
PESO = 0.1


def taxa_rollback(defeitos: dict, n: int) -> float:
    reprovados = 0
    for seed in range(REPETICOES):
        rng = random.Random(seed)
        alias = AliasPonderado(Versao("v1"), Versao("v2", **defeitos), PESO, rng)
        respostas = [alias.chamar(t) for t in amostrar(n, rng)]
        if not decidir(medir(respostas, "v1"), medir(respostas, "v2")).promover:
            reprovados += 1
    return reprovados / REPETICOES


def grafico(falso: list[float], detectado: list[float], destino: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    matplotlib.rcParams["svg.fonttype"] = "none"
    matplotlib.rcParams["font.family"] = "DejaVu Sans"
    import matplotlib.pyplot as plt

    azul, laranja, texto, texto2, grade = "#2a78d6", "#eb6834", "#0b0b0b", "#52514e", "#e6e5e0"
    fig, ax = plt.subplots(figsize=(9, 5.2), dpi=150)
    fig.patch.set_facecolor("#fcfcfb")
    ax.set_facecolor("#fcfcfb")

    for serie, cor, rotulo in [(detectado, laranja, "Regressão silenciosa detectada"),
                               (falso, azul, "Falso rollback (versão era saudável)")]:
        y = [v * 100 for v in serie]
        ax.plot(TAMANHOS, y, color=cor, linewidth=2, marker="o", markersize=6,
                markeredgecolor="#fcfcfb", markeredgewidth=2, label=rotulo, zorder=3)
        ax.annotate(f"{y[-1]:.0f}%", (TAMANHOS[-1], y[-1]), xytext=(8, 0), textcoords="offset points",
                    va="center", color=texto, fontsize=10, fontweight="bold")

    i300 = TAMANHOS.index(300)
    ax.annotate(f"{falso[i300] * 100:.0f}% de falso rollback", (300, falso[i300] * 100), xytext=(-10, -16), ha="right",
                textcoords="offset points", color=texto, fontsize=10, fontweight="bold")
    ax.axvline(300, color=texto2, linewidth=1, linestyle=(0, (3, 3)), zorder=1)
    ax.annotate("300 requisições:\npadrão da aula", (300, 55), xytext=(6, 0), textcoords="offset points",
                color=texto2, fontsize=9, va="center")

    ax.set_xscale("log")
    ax.minorticks_off()
    ax.set_xticks(TAMANHOS)
    ax.set_xticklabels([f"{t:,}".replace(",", ".") for t in TAMANHOS])
    ax.set_xlim(85, 4200)
    ax.set_ylim(-3, 105)
    ax.set_yticks([0, 25, 50, 75, 100])
    ax.set_yticklabels([f"{v}%" for v in [0, 25, 50, 75, 100]])
    ax.set_xlabel(f"Requisições na análise ({PESO:.0%} delas vão para o canary)", color=texto2)
    ax.set_ylabel(f"% de {REPETICOES} canários reprovados", color=texto2)
    ax.grid(axis="y", color=grade, linewidth=1)
    ax.tick_params(colors=texto2, length=0)
    for lado in ["top", "right", "left"]:
        ax.spines[lado].set_visible(False)
    ax.spines["bottom"].set_color(grade)
    fig.suptitle("Com amostra pequena, o canary reprova até versão saudável", x=0.075, ha="left",
                 fontsize=14, fontweight="bold", color=texto)
    ax.set_title("Mesmos critérios (erro ≤ 2%, p95 ≤ 1,5×, distribuição ≤ 15 p.p.), só muda o tamanho da amostra",
                 loc="left", fontsize=9.5, color=texto2, pad=10)
    ax.legend(loc="center right", frameon=False, fontsize=9.5, labelcolor=texto)
    fig.tight_layout()
    destino.parent.mkdir(exist_ok=True)
    fig.savefig(destino, facecolor=fig.get_facecolor(), metadata={"Date": None})
    # fonte de reserva para quem não tem DejaVu Sans instalada (o GitHub mostra o SVG no navegador)
    svg = destino.read_text(encoding="utf-8").replace("'DejaVu Sans'", "'DejaVu Sans', Arial, Helvetica, sans-serif")
    destino.write_text(svg, encoding="utf-8")


def main() -> None:
    falso = [taxa_rollback({}, n) for n in TAMANHOS]
    detectado = [taxa_rollback({"vies": 0.4}, n) for n in TAMANHOS]
    print("| requisições | falso rollback (saudável) | drift detectado |")
    print("|---|---|---|")
    for n, f, d in zip(TAMANHOS, falso, detectado):
        print(f"| {n} | {f:.0%} | {d:.0%} |")
    grafico(falso, detectado, Path(__file__).parent / "docs" / "amostra.svg")
    print("\ngráfico salvo em docs/amostra.svg")


if __name__ == "__main__":
    main()
