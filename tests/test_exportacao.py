"""Exportar uma Saída: JSON, Markdown e ZIP. Tudo em memória e em pasta temporária."""

from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

from suno.dominio import Audiencia, Destino, EstadoDecisao, Formato
from suno.exportacao import FormatoExportacao, exportar
from suno.gerador.execucao import gravar_execucao
from suno.revisao import decidir
from tests.construtores_de_execucao import IDENTIFICADOR, execucao_de_teste, historico_de_texto

TEXTO = Formato.TEXTO_ANALITICO


def _execucao_gravada(pasta: Path):
    execucao = execucao_de_teste(
        historico_de_texto(Audiencia.INICIANTE, Destino.APROVADO),
        historico_de_texto(Audiencia.INTERMEDIARIO, Destino.APROVADO),
        nome="Copom 280 · pauta juros",
    )
    decidir(execucao, Audiencia.INICIANTE, TEXTO, EstadoDecisao.APROVADA, revisor="Ana")
    gravar_execucao(execucao, pasta)
    return execucao


def test_json_traz_o_nome_e_as_decisoes(tmp_path: Path) -> None:
    execucao = _execucao_gravada(tmp_path)

    conteudo, media_type, nome_do_arquivo = exportar(
        execucao, tmp_path / IDENTIFICADOR, FormatoExportacao.JSON
    )

    dados = json.loads(conteudo)
    assert dados["nome"] == "Copom 280 · pauta juros"
    assert dados["decisoes"][0]["estado"] == "aprovada"
    assert media_type == "application/json"
    assert nome_do_arquivo == f"{IDENTIFICADOR}.json"


def test_markdown_junta_as_celulas_com_a_decisao_de_cada_uma(tmp_path: Path) -> None:
    execucao = _execucao_gravada(tmp_path)

    conteudo, media_type, nome_do_arquivo = exportar(
        execucao, tmp_path / IDENTIFICADOR, FormatoExportacao.MARKDOWN
    )

    texto = conteudo.decode("utf-8")
    assert texto.startswith("# Copom 280 · pauta juros")
    assert "## Iniciante · Texto analítico" in texto
    assert "## Intermediário · Texto analítico" in texto
    assert "Decisão: aprovada por Ana" in texto
    assert "Decisão: pendente" in texto
    assert "Texto de teste para iniciante." in texto
    assert media_type == "text/markdown; charset=utf-8"
    assert nome_do_arquivo == f"{IDENTIFICADOR}.md"


def test_zip_leva_o_json_as_celulas_e_o_pacote(tmp_path: Path) -> None:
    execucao = _execucao_gravada(tmp_path)
    pasta_do_pacote = tmp_path / IDENTIFICADOR / "pacote" / "iniciante-texto_analitico"
    pasta_do_pacote.mkdir(parents=True)
    (pasta_do_pacote / "pacote.json").write_text("{}", encoding="utf-8")

    conteudo, media_type, nome_do_arquivo = exportar(
        execucao, tmp_path / IDENTIFICADOR, FormatoExportacao.ZIP
    )

    with zipfile.ZipFile(io.BytesIO(conteudo)) as arquivo:
        nomes = set(arquivo.namelist())
        dados = json.loads(arquivo.read(f"{IDENTIFICADOR}/execucao.json"))
    assert f"{IDENTIFICADOR}/execucao.json" in nomes
    assert f"{IDENTIFICADOR}/celulas/iniciante-texto_analitico.md" in nomes
    assert f"{IDENTIFICADOR}/pacote/iniciante-texto_analitico/pacote.json" in nomes
    assert dados["nome"] == "Copom 280 · pauta juros"
    assert media_type == "application/zip"
    assert nome_do_arquivo == f"{IDENTIFICADOR}.zip"


def test_zip_sem_pasta_de_pacote_exporta_so_o_que_existe(tmp_path: Path) -> None:
    execucao = _execucao_gravada(tmp_path)

    conteudo, _, _ = exportar(execucao, tmp_path / IDENTIFICADOR, FormatoExportacao.ZIP)

    with zipfile.ZipFile(io.BytesIO(conteudo)) as arquivo:
        nomes = arquivo.namelist()
    assert not any("/pacote/" in nome for nome in nomes)
