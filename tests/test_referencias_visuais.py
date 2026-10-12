"""As seis referências internas alimentam a direção de arte sem depender de rede."""

from __future__ import annotations

import sqlite3
from io import BytesIO
from pathlib import Path

from PIL import Image

from suno.dominio import ComposicaoCarrossel, Slide, TipoSlide
from suno.pacote.analise_visual import normalizar_imagem
from suno.pacote.direcao_de_arte import planejar_direcao_de_arte
from suno.pacote.referencias_visuais import (
    REFERENCIAS_INICIAIS,
    RepositorioReferenciasVisuais,
)


def test_biblioteca_nasce_com_uma_referencia_financeira_por_composicao(tmp_path: Path) -> None:
    repositorio = RepositorioReferenciasVisuais(tmp_path / "suno.sqlite3")

    referencias = repositorio.listar(apenas_aprovadas=True)

    assert len(referencias) == 6
    assert {referencia.composicao for referencia in referencias} == set(ComposicaoCarrossel)
    assert all(referencia.tema and referencia.instrucao_de_design for referencia in referencias)
    assert all(referencia.analise.estrutura_do_conteudo for referencia in referencias)


def test_semeadura_e_idempotente_e_preserva_curadoria_local(tmp_path: Path) -> None:
    caminho = tmp_path / "suno.sqlite3"
    repositorio = RepositorioReferenciasVisuais(caminho)
    repositorio.garantir_sementes()
    with sqlite3.connect(caminho) as conexao:
        conexao.execute(
            "UPDATE referencias_visuais SET aprovada = 0 WHERE identificador = ?",
            (REFERENCIAS_INICIAIS[0].identificador,),
        )
    repositorio.garantir_sementes()

    referencias = repositorio.listar()

    assert len(referencias) == 6
    alterada = next(
        item for item in referencias if item.identificador == REFERENCIAS_INICIAIS[0].identificador
    )
    assert alterada.aprovada is False


def test_plano_registra_qual_referencia_aprovada_orientou_o_layout() -> None:
    slide = Slide(
        tipo=TipoSlide.HOOK,
        titulo="O que mudou nos juros?",
        corpo="Veja o cenário antes de rever sua carteira.",
    )

    escolha = planejar_direcao_de_arte(
        [slide], referencias_aprovadas=REFERENCIAS_INICIAIS
    )[0]

    assert escolha.composicao is ComposicaoCarrossel.EDITORIAL
    assert escolha.referencia_visual == "suno-editorial-cenario-de-juros"
    assert any("referência aprovada" in motivo for motivo in escolha.motivos)


def test_importacao_manual_nasce_reprovada_e_pode_ser_aprovada(tmp_path: Path) -> None:
    repositorio = RepositorioReferenciasVisuais(tmp_path / "suno.sqlite3")

    importada = repositorio.adicionar(
        titulo="Crédito privado sem atalhos",
        tema="renda fixa",
        composicao=ComposicaoCarrossel.COMPARATIVO,
        descricao="Compara risco, liquidez e prazo em dois painéis equivalentes.",
        instrucao_de_design="Use os mesmos critérios nos dois lados e não indique vencedor.",
        origem="https://exemplo.test/referencia-autorizada",
    )

    assert importada.aprovada is False
    assert len(repositorio.listar(apenas_aprovadas=True)) == 6
    aprovada = repositorio.definir_aprovacao(importada.identificador, True)
    assert aprovada.aprovada is True
    assert len(repositorio.listar(apenas_aprovadas=True)) == 7


def test_migracao_expansiva_preserva_banco_da_fase_anterior(tmp_path: Path) -> None:
    caminho = tmp_path / "suno.sqlite3"
    with sqlite3.connect(caminho) as conexao:
        conexao.execute(
            """
            CREATE TABLE referencias_visuais (
                identificador TEXT PRIMARY KEY, titulo TEXT NOT NULL, tema TEXT NOT NULL,
                composicao TEXT NOT NULL, descricao TEXT NOT NULL,
                instrucao_de_design TEXT NOT NULL, analise_json TEXT NOT NULL,
                aprovada INTEGER NOT NULL, origem TEXT NOT NULL, criada_em TEXT NOT NULL
            )
            """
        )
    repositorio = RepositorioReferenciasVisuais(caminho)

    referencias = repositorio.listar()

    assert len(referencias) == 6
    assert all(not item.imagem_disponivel for item in referencias)
    assert all(item.estado_analise.value == "nao_solicitada" for item in referencias)


def test_normalizacao_remove_formato_original_e_limita_dimensao(tmp_path: Path) -> None:
    memoria = BytesIO()
    Image.new("RGB", (2400, 1200), "#ff0000").save(memoria, format="JPEG")

    destino = normalizar_imagem(memoria.getvalue(), tmp_path / "referencia.png")

    with Image.open(destino) as imagem:
        assert imagem.format == "PNG"
        assert max(imagem.size) == 1600
