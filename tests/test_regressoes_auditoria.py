"""Regressões da auditoria de revisão humana e derivados (17/10/2026), sem rede.

O conteúdo sintético isola as transições de estado. O render de vídeo é interrompido
na entrada do codificador: a prova aqui é o gate H4, não a qualidade do ffmpeg.
"""
from __future__ import annotations

import io
import zipfile
from pathlib import Path
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from suno.api.app import criar_app
from suno.dominio import (
    AncoraTextual, Audiencia, CategoriaDaAta, DecisaoHumana, Destino,
    EstadoDecisao, Execucao, Formato, ImagemSlide, ModoSelecao, MotivoReprovacao,
    PacotePublicacao, SelecaoCuradoria,
)
from suno.gerador.execucao import carregar_execucao, gravar_execucao
from suno.pacote import montar_pacote
from suno.revisao import EdicaoDeTexto, _chaves_essenciais_da_execucao, decidir, revisar_texto
from suno.video import render
from tests.construtores_de_execucao import execucao_de_teste, historico_de_texto
from tests.test_api import _celula_carrossel
from tests.test_video import _celula_roteiro, _historico

AUD = Audiencia.INICIANTE
TEXTO = Formato.TEXTO_ANALITICO
ROTEIRO = Formato.ROTEIRO


def _texto() -> Execucao:
    return execucao_de_teste(historico_de_texto(AUD, Destino.APROVADO))


def _roteiro(destino: Destino = Destino.APROVADO) -> Execucao:
    return execucao_de_teste(_historico(_celula_roteiro(AUD), destino))


def _cliente(pasta: Path) -> TestClient:
    return TestClient(criar_app(pasta, pasta_fontes=pasta / "fontes"))


def _base(execucao: Execucao) -> str:
    return f"/api/execucoes/{execucao.identificador}"


def _pasta_pacote(pasta: Path, execucao: Execucao, formato: Formato = TEXTO) -> Path:
    return pasta / execucao.identificador / "pacote" / f"{AUD.value}-{formato.value}"


def test_veto_humano_vence_aprovacao_automatica(tmp_path: Path):
    execucao = _texto()
    decidir(execucao, AUD, TEXTO, EstadoDecisao.REPROVADA, motivo="Tom inadequado")
    assert not execucao.celula_liberada(AUD, TEXTO)
    gravar_execucao(execucao, tmp_path)
    assert montar_pacote(execucao.identificador, tmp_path) == []


def test_recomendacao_bloqueia_mesmo_decisao_aprovada_em_registro_antigo():
    execucao = execucao_de_teste(historico_de_texto(
        AUD, Destino.REPROVADO_REVISAO_HUMANA, (MotivoReprovacao.RECOMENDACAO,),
    ))
    # Defesa também para dados antigos/importados: não depender só da validação da rota.
    execucao.decisoes = [DecisaoHumana(audiencia=AUD, formato=TEXTO, estado=EstadoDecisao.APROVADA)]
    assert not execucao.celula_liberada(AUD, TEXTO)


def test_revisao_unida_com_ancora_textual_preserva_partes_sem_ancoras():
    execucao = _texto()
    execucao.categoria = CategoriaDaAta.UNIDA
    execucao.selecao = SelecaoCuradoria(modo=ModoSelecao.UNIDA, itens=["ata-1", "ata-2"])
    execucao.ancoras.textuais = [AncoraTextual(
        identificador="a1_afirmacao_central", afirmacao="A empresa abriu uma nova unidade.",
        trecho="A empresa abriu uma nova unidade.",
    )]
    essenciais = _chaves_essenciais_da_execucao(execucao)["chaves_essenciais"]
    assert {"a1_data_do_comunicado", "a2_data_do_comunicado", "a2_numero_principal"} <= essenciais
    historico = revisar_texto(execucao, AUD, TEXTO, EdicaoDeTexto(texto="A empresa abriu uma nova unidade."))
    assert len(historico.tentativas) == 2
    assert MotivoReprovacao.FALHA_DE_EXTRACAO in historico.laudo_final.motivos


@pytest.mark.parametrize("operacao", ["baixar", "aprovar"])
def test_pacote_de_outra_revisao_da_409_mesmo_apos_h4(tmp_path: Path, operacao: str):
    execucao = _texto()
    gravar_execucao(execucao, tmp_path)
    pacote = montar_pacote(execucao.identificador, tmp_path)[0]
    assert pacote.assinatura_conteudo == execucao.assinatura_da_celula(AUD, TEXTO)
    assert pacote.corresponde_a(execucao)
    revisar_texto(execucao, AUD, TEXTO, EdicaoDeTexto(texto="A empresa abriu uma nova unidade."))
    decidir(execucao, AUD, TEXTO, EstadoDecisao.APROVADA, revisor="Revisora")
    assert execucao.celula_liberada(AUD, TEXTO)
    assert not pacote.corresponde_a(execucao)
    gravar_execucao(execucao, tmp_path)
    with _cliente(tmp_path) as cliente:
        url = f"{_base(execucao)}/pacotes/iniciante/texto_analitico/{operacao}"
        resposta = cliente.get(url) if operacao == "baixar" else cliente.post(url)
        assert resposta.status_code == 409
        assert "outra revisão" in resposta.json()["detail"]
        assert cliente.get(f"{_base(execucao)}/pacotes").json() == []


def test_edicao_pela_api_invalida_derivados_e_nao_reutiliza_aprovacao_h5(tmp_path: Path):
    execucao = _texto()
    gravar_execucao(execucao, tmp_path)
    montar_pacote(execucao.identificador, tmp_path)
    pasta = _pasta_pacote(tmp_path, execucao)
    derivados = ["video.mp4", "video.revisao", "plano.json", "plano.md", "atuacao.json"]
    for nome in derivados:
        (pasta / nome).write_text("derivado anterior", encoding="utf-8")
    with _cliente(tmp_path) as cliente:
        pacote_url = f"{_base(execucao)}/pacotes/iniciante/texto_analitico"
        assert cliente.post(f"{pacote_url}/aprovar").status_code == 200
        resposta = cliente.put(f"{_base(execucao)}/celulas/iniciante/texto_analitico/texto", json={"texto": "Compre estas ações agora."})
        assert resposta.status_code == 200
        assert "recomendacao" in resposta.json()["tentativas"][-1]["laudo"]["motivos"]
        assert all(not (pasta / nome).exists() for nome in ["pacote.json", *derivados])
        assert cliente.get(f"{pacote_url}/baixar").status_code == 404
        assert cliente.post(f"{pacote_url}/aprovar").status_code == 404
        assert cliente.get(f"{_base(execucao)}/arquivos/pacote/iniciante-texto_analitico/legenda.txt").status_code == 404


@pytest.mark.parametrize("operacao", ["baixar", "aprovar"])
def test_veto_humano_bloqueia_rotas_do_pacote(tmp_path: Path, operacao: str):
    execucao = _texto()
    gravar_execucao(execucao, tmp_path)
    montar_pacote(execucao.identificador, tmp_path)
    manifesto = _pasta_pacote(tmp_path, execucao) / "pacote.json"
    registro_anterior = manifesto.read_text(encoding="utf-8")
    with _cliente(tmp_path) as cliente:
        resposta = cliente.post(f"{_base(execucao)}/celulas/iniciante/texto_analitico/decisao", json={"estado": "reprovada", "motivo": "Tom inadequado"})
        assert resposta.status_code == 200
        url = f"{_base(execucao)}/pacotes/iniciante/texto_analitico/{operacao}"
        resposta = cliente.get(url) if operacao == "baixar" else cliente.post(url)
        assert resposta.status_code == 404
        # Simula um montador atrasado: mesmo recolocando o registro assinado, o veto vence.
        manifesto.write_text(registro_anterior, encoding="utf-8")
        resposta = cliente.get(url) if operacao == "baixar" else cliente.post(url)
        assert resposta.status_code == 409


@pytest.mark.parametrize("formato,esperados", [
    (TEXTO, {"texto.md", "legenda.txt"}),
    (ROTEIRO, {"plano.json", "plano.md", "legenda.txt"}),
])
def test_zip_do_pacote_leva_conteudo_do_formato(tmp_path: Path, formato: Formato, esperados: set[str]):
    execucao = _texto() if formato is TEXTO else _roteiro()
    gravar_execucao(execucao, tmp_path)
    montar_pacote(execucao.identificador, tmp_path)
    with _cliente(tmp_path) as cliente:
        resposta = cliente.get(f"{_base(execucao)}/pacotes/iniciante/{formato.value}/baixar")
    assert resposta.status_code == 200
    with zipfile.ZipFile(io.BytesIO(resposta.content)) as arquivo:
        assert esperados <= set(arquivo.namelist())
        assert all(arquivo.read(nome) for nome in esperados)


@pytest.mark.parametrize("aprovar", [True, False])
def test_plano_respeita_decisao_h4_e_veto_humano(tmp_path: Path, aprovar: bool):
    execucao = _roteiro(Destino.REPROVADO_REVISAO_HUMANA if aprovar else Destino.APROVADO)
    decidir(execucao, AUD, ROTEIRO, EstadoDecisao.APROVADA if aprovar else EstadoDecisao.REPROVADA, motivo=None if aprovar else "Tom inadequado")
    gravar_execucao(execucao, tmp_path)
    with _cliente(tmp_path) as cliente:
        resposta = cliente.get(f"{_base(execucao)}/celulas/iniciante/roteiro/plano")
    assert resposta.status_code == (200 if aprovar else 409)
    if aprovar:
        assert resposta.json()["plano"] and resposta.json()["markdown"]


@pytest.mark.parametrize("aprovar", [True, False])
def test_video_respeita_decisao_h4_e_veto_antes_do_codificador(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, aprovar: bool):
    execucao = _roteiro(Destino.REPROVADO_REVISAO_HUMANA if aprovar else Destino.APROVADO)
    decidir(execucao, AUD, ROTEIRO, EstadoDecisao.APROVADA if aprovar else EstadoDecisao.REPROVADA, motivo=None if aprovar else "Tom inadequado")
    gravar_execucao(execucao, tmp_path)
    codificador = Mock(side_effect=RuntimeError("codificador alcançado"))
    monkeypatch.setattr(render, "_ffmpeg_exe", codificador)
    if aprovar:
        with pytest.raises(RuntimeError, match="codificador alcançado"):
            render.renderizar_video(execucao.identificador, AUD, tmp_path)
        codificador.assert_called_once()
    else:
        with pytest.raises(ValueError, match="aprovado"):
            render.renderizar_video(execucao.identificador, AUD, tmp_path)
        codificador.assert_not_called()


@pytest.mark.parametrize("mudanca", ["editar", "vetar"])
def test_zip_da_execucao_nao_contorna_bloqueio_dos_derivados(tmp_path: Path, mudanca: str):
    execucao = _texto()
    gravar_execucao(execucao, tmp_path)
    montar_pacote(execucao.identificador, tmp_path)
    with _cliente(tmp_path) as cliente:
        if mudanca == "editar":
            resposta = cliente.put(f"{_base(execucao)}/celulas/iniciante/texto_analitico/texto", json={"texto": "Compre estas ações agora."})
        else:
            resposta = cliente.post(f"{_base(execucao)}/celulas/iniciante/texto_analitico/decisao", json={"estado": "reprovada", "motivo": "Tom inadequado"})
        assert resposta.status_code == 200
        resposta = cliente.get(f"{_base(execucao)}/exportar", params={"formato": "zip"})
    assert resposta.status_code == 200
    with zipfile.ZipFile(io.BytesIO(resposta.content)) as arquivo:
        nomes = arquivo.namelist()
        assert f"{execucao.identificador}/execucao.json" in nomes
        assert not any("/pacote/" in nome for nome in nomes)
    assert not carregar_execucao(execucao.identificador, tmp_path).celula_liberada(AUD, TEXTO)


@pytest.mark.parametrize("estado_video", ["fora_do_manifesto", "revisao_antiga", "atual"])
def test_mp4_so_sai_quando_manifesto_e_revisao_correspondem(tmp_path: Path, estado_video: str):
    execucao = _roteiro()
    gravar_execucao(execucao, tmp_path)
    pacote = montar_pacote(execucao.identificador, tmp_path)[0]
    pasta = _pasta_pacote(tmp_path, execucao, ROTEIRO)
    video = pasta / "video.mp4"
    video.write_bytes(b"video de prova: o teste verifica acesso, nao codecs")
    if estado_video != "fora_do_manifesto":
        pacote.video = video
    video.with_suffix(".revisao").write_text(
        "assinatura-anterior" if estado_video == "revisao_antiga" else pacote.assinatura_conteudo,
        encoding="utf-8",
    )
    (pasta / "pacote.json").write_text(pacote.model_dump_json(), encoding="utf-8")
    permitido = estado_video == "atual"
    with _cliente(tmp_path) as cliente:
        resposta = cliente.get(f"{_base(execucao)}/pacotes/iniciante/roteiro/baixar")
        assert resposta.status_code == 200
        with zipfile.ZipFile(io.BytesIO(resposta.content)) as arquivo:
            assert ("video.mp4" in arquivo.namelist()) is permitido
            assert "plano.json" in arquivo.namelist()
        resposta = cliente.get(f"{_base(execucao)}/exportar", params={"formato": "zip"})
        assert resposta.status_code == 200
        with zipfile.ZipFile(io.BytesIO(resposta.content)) as arquivo:
            assert any(nome.endswith("/video.mp4") for nome in arquivo.namelist()) is permitido
        resposta = cliente.get(f"{_base(execucao)}/arquivos/pacote/iniciante-roteiro/video.mp4")
        assert resposta.status_code == (200 if permitido else 409)


def test_slide_extra_nao_sai_no_zip_nem_por_acesso_direto(tmp_path: Path):
    execucao = execucao_de_teste(_historico(_celula_carrossel(AUD), Destino.APROVADO))
    gravar_execucao(execucao, tmp_path)
    pasta = _pasta_pacote(tmp_path, execucao, Formato.CARROSSEL)
    pasta.mkdir(parents=True)
    for indice in (1, 99):
        for extensao in ("png", "html", "json"):
            (pasta / f"slide-{indice:02d}.{extensao}").write_text(f"quadro {indice}", encoding="utf-8")
    pacote = PacotePublicacao(
        execucao=execucao.identificador, audiencia=AUD, formato=Formato.CARROSSEL,
        assinatura_conteudo=execucao.assinatura_da_celula(AUD, Formato.CARROSSEL),
        legenda="Legenda atual", imagens=[ImagemSlide(
            indice=0, caminho=pasta / "slide-01.png", largura=1080, altura=1350,
        )],
    )
    (pasta / "pacote.json").write_text(pacote.model_dump_json(), encoding="utf-8")
    with _cliente(tmp_path) as cliente:
        resposta = cliente.get(f"{_base(execucao)}/pacotes/iniciante/carrossel/baixar")
        assert resposta.status_code == 200
        with zipfile.ZipFile(io.BytesIO(resposta.content)) as arquivo:
            assert arquivo.namelist() == ["slide-01.png"]
        resposta = cliente.get(f"{_base(execucao)}/exportar", params={"formato": "zip"})
        assert resposta.status_code == 200
        with zipfile.ZipFile(io.BytesIO(resposta.content)) as arquivo:
            assert any(nome.endswith("/slide-01.png") for nome in arquivo.namelist())
            assert not any("slide-99." in nome for nome in arquivo.namelist())
        for extensao in ("png", "html", "json"):
            assert cliente.get(f"{_base(execucao)}/arquivos/pacote/iniciante-carrossel/slide-01.{extensao}").status_code == 200
            assert cliente.get(f"{_base(execucao)}/arquivos/pacote/iniciante-carrossel/slide-99.{extensao}").status_code == 409
        assert cliente.get(f"{_base(execucao)}/pacotes/iniciante/carrossel/99/previa").status_code == 409
