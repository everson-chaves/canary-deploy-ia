import random

import pytest

from canary.analise import Metricas, decidir
from canary.modelo import Versao, classificar
from canary.roteador import AliasPonderado
from demo import rodar

DIST = {"positiva": 0.4, "negativa": 0.35, "neutra": 0.25}


def metricas(versao="v", erro=0.0, p95=50.0, dist=None, req=100):
    return Metricas(versao, req, erro, p95, dist or dict(DIST))


@pytest.mark.parametrize(
    "texto, esperado",
    [("Adorei, é ótimo", "positiva"), ("Quebrou, péssimo", "negativa"), ("Chegou no prazo", "neutra")],
)
def test_classificador(texto, esperado):
    assert classificar(texto) == esperado


def test_promove_quando_tudo_igual():
    assert decidir(metricas(), metricas()).promover


def test_rollback_por_erro():
    decisao = decidir(metricas(), metricas(erro=0.05))
    assert not decisao.promover and "erro" in decisao.motivos[0]


def test_erro_pequeno_mas_acima_da_estavel_tambem_reprova():
    assert not decidir(metricas(erro=0.0), metricas(erro=0.015)).promover


def test_rollback_por_latencia():
    assert not decidir(metricas(p95=50), metricas(p95=80)).promover


def test_rollback_silencioso_por_distribuicao():
    """0% de erro e mesma latência, mas o modelo passou a decidir diferente."""
    drift = {"positiva": 0.6, "negativa": 0.25, "neutra": 0.15}
    decisao = decidir(metricas(), metricas(dist=drift))
    assert not decisao.promover and "positiva" in decisao.motivos[0]


def test_peso_do_alias_respeitado():
    rng = random.Random(0)
    alias = AliasPonderado(Versao("v1"), Versao("v2"), 0.2, rng)
    respostas = [alias.chamar("ótimo") for _ in range(5000)]
    fracao = sum(r.versao == "v2" for r in respostas) / len(respostas)
    assert 0.18 < fracao < 0.22


def test_peso_invalido():
    with pytest.raises(ValueError):
        AliasPonderado(Versao("v1"), Versao("v2"), 1.5, random.Random(0))


@pytest.mark.parametrize(
    "cenario, requisicoes, promove",
    [
        ("saudavel", 1000, True),
        ("erro", 1000, False),
        ("lenta", 1000, False),
        ("drift", 1000, False),
        ("cold_start", 300, False),  # falso rollback: amostra pequena
        ("cold_start", 1000, True),
    ],
)
def test_cenarios_ponta_a_ponta(cenario, requisicoes, promove):
    promoveu, _ = rodar(cenario, requisicoes, 0.1, seed=42)
    assert promoveu is promove
