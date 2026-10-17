"""A Demo ignora serviços externos; uma gravação interrompida preserva o estado oficial."""

from pathlib import Path

import pytest

from suno.dominio import Audiencia, Destino, Execucao, Formato
from suno.gerador.execucao import carregar_execucao, executar, gravar_execucao
from tests.construtores_de_execucao import execucao_de_teste


def test_demo_nao_instancia_verificadores_com_ambiente_ligado(
    tmp_path: Path, caminho_ata_txt: Path, monkeypatch: pytest.MonkeyPatch
):
    for variavel in ("SUNO_JEV", "SUNO_FIDELIDADE"):
        monkeypatch.setenv(variavel, "1")
    for variavel in ("JEV_API_KEY", "GROQ_API_KEY", "GEMINI_API_KEY"):
        monkeypatch.setenv(variavel, "chave-ficticia-de-teste")

    def proibido(*args, **kwargs):
        pytest.fail("a Demo tentou preparar uma camada de avaliação externa")

    monkeypatch.setattr("suno.gerador.execucao._qualidade_de_ambiente", proibido)
    monkeypatch.setattr("suno.gerador.execucao._fidelidade_de_ambiente", proibido)

    execucao = executar(
        caminho_ata_txt,
        "falso",
        tmp_path,
        pedido=[(Audiencia.INICIANTE, Formato.TEXTO_ANALITICO)],
    )

    assert execucao.provedor_gerador == "falso"
    assert execucao.celulas[0].destino_final is Destino.APROVADO
    assert carregar_execucao(execucao.identificador, tmp_path) == execucao


@pytest.mark.parametrize("erro", [OSError, PermissionError])
def test_falha_na_substituicao_preserva_json_anterior_e_remove_temporario(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, erro: type[OSError]
):
    anterior = execucao_de_teste(nome="Nome anterior")
    arquivo = gravar_execucao(anterior, tmp_path)
    bytes_anteriores = arquivo.read_bytes()
    nova = anterior.model_copy(update={"nome": "Nome novo"})
    temporarios: list[Path] = []

    def falhar_substituicao(origem, destino):
        temporario = Path(origem)
        temporarios.append(temporario)
        assert Path(destino) == arquivo
        assert temporario.parent == arquivo.parent
        assert Execucao.model_validate_json(temporario.read_text(encoding="utf-8")) == nova
        assert arquivo.read_bytes() == bytes_anteriores
        raise erro("falha de disco simulada")

    monkeypatch.setattr("suno.gerador.execucao.os.replace", falhar_substituicao)

    with pytest.raises(erro, match="falha de disco simulada"):
        gravar_execucao(nova, tmp_path)

    assert temporarios
    assert arquivo.read_bytes() == bytes_anteriores
    assert carregar_execucao(anterior.identificador, tmp_path) == anterior
    assert all(not temporario.exists() for temporario in temporarios)
    assert not list(arquivo.parent.glob("*.tmp"))
