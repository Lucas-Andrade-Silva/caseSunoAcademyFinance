"""O pacote de imagens: biblioteca, Commons (transporte simulado), validação e resolvedor.

Tudo offline: o Commons é um ``httpx.MockTransport`` e o juiz de visão é o ``ProvedorFalso``.
"""

from __future__ import annotations

import io
import json
from pathlib import Path

import httpx
import pytest
from PIL import Image

from suno.dominio import ErroProvedor, PapelLLM
from suno.imagens import (
    BibliotecaDeImagens,
    ClienteCommons,
    FonteDeImagemIndisponivel,
    ImagemInexistente,
    ImagemResolvida,
    bloco_de_creditos,
    resolver_imagem,
    validar_relevancia,
)
from suno.imagens.commons import limpar_autor, licenca_permitida
from suno.imagens.texto import termos
from suno.imagens.validacao import ROTULO, ImagemIlegivel
from suno.provedores import ProvedorFalso

RAIZ = Path(__file__).resolve().parent.parent
PASTA_SEMEADA = RAIZ / "data" / "imagens"

APROVA = {"relevante": True, "motivo": "mostra o assunto", "inadequada": False}
REPROVA = {"relevante": False, "motivo": "é de outro assunto", "inadequada": False}
INADEQUADA = {"relevante": True, "motivo": "pessoa privada", "inadequada": True}


# ---------------------------------------------------------------------------
# Auxiliares
# ---------------------------------------------------------------------------


def jpeg(largura: int = 1200, altura: int = 800, cor: tuple[int, int, int] = (30, 90, 160)) -> bytes:
    saida = io.BytesIO()
    Image.new("RGB", (largura, altura), cor).save(saida, format="JPEG")
    return saida.getvalue()


def pagina(
    indice: int,
    nome: str,
    *,
    licenca: str = "CC BY 2.0",
    largura: int = 1600,
    artista: str = "<a href='//commons.wikimedia.org/wiki/User:Ana'>Ana Souza</a>",
    extra: dict | None = None,
    miniatura: bool = True,
) -> dict:
    meta = {
        "LicenseShortName": {"value": licenca},
        "Artist": {"value": artista},
    } | (extra or {})
    info: dict = {
        "width": largura,
        "height": 1000,
        "mime": "image/jpeg",
        "descriptionurl": f"https://commons.wikimedia.org/wiki/File:{nome}",
        "extmetadata": meta,
    }
    if miniatura:
        info["thumburl"] = f"https://upload.wikimedia.org/thumb/{nome}/1200px-{nome}"
    return {"title": f"File:{nome}", "index": indice, "imageinfo": [info]}


def resposta_mediawiki(*paginas: dict) -> dict:
    return {"query": {"pages": list(paginas)}}


class Commons:
    """Um Commons de mentira em cima de ``httpx.MockTransport``; conta as chamadas."""

    def __init__(self, paginas: list[dict], *, imagens: dict[str, bytes] | None = None) -> None:
        self.paginas = paginas
        self.imagens = imagens or {}
        self.chamadas: list[httpx.Request] = []

    def __call__(self, requisicao: httpx.Request) -> httpx.Response:
        self.chamadas.append(requisicao)
        if requisicao.url.host == "commons.wikimedia.org":
            return httpx.Response(200, json=resposta_mediawiki(*self.paginas))
        nome = requisicao.url.path.rsplit("/", 1)[-1].removeprefix("1200px-")
        return httpx.Response(200, content=self.imagens.get(nome, jpeg()))

    def cliente(self) -> httpx.Client:
        return httpx.Client(transport=httpx.MockTransport(self), headers={"User-Agent": "teste"})

    def baixados(self) -> list[str]:
        return [c.url.path for c in self.chamadas if c.url.host != "commons.wikimedia.org"]


def cliente_com(manipulador) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(manipulador))


@pytest.fixture
def biblioteca(tmp_path: Path) -> BibliotecaDeImagens:
    return BibliotecaDeImagens(tmp_path / "imagens")


def adicionar(biblioteca: BibliotecaDeImagens, identificador: str, tags: list[str], **campos):
    base = {
        "identificador": identificador,
        "tags": tags,
        "titulo": f"Foto {identificador}.jpg",
        "autor": "Ana Souza",
        "licenca": "CC BY 2.0",
        "url_origem": f"https://commons.wikimedia.org/wiki/File:{identificador}.jpg",
        "aprovada": True,
        "validada_por": "humano",
    }
    return biblioteca.adicionar(jpeg(), **(base | campos))


# ---------------------------------------------------------------------------
# Normalização e biblioteca
# ---------------------------------------------------------------------------


def test_termos_normalizam_acento_caixa_stopword_e_plural():
    assert termos("As AÇÕES da Bolsa de São Paulo!") == ["acoe", "bolsa", "sao", "paulo"]
    assert termos("de da o a") == []


def test_busca_ignora_acento_e_caixa_e_ordena_por_pontuacao(biblioteca):
    adicionar(biblioteca, "geral", ["mercado"])
    adicionar(biblioteca, "bolsa", ["bolsa", "b3", "pregão", "ações"])
    adicionar(biblioteca, "bcb", ["banco central", "selic", "juros"])
    achadas = biblioteca.buscar("PREGAO na Bolsa: ações e mercado")
    assert [i.arquivo.stem for i in achadas] == ["bolsa", "geral"]
    assert all(i.origem == "biblioteca" and i.validada_por == "humano" for i in achadas)
    assert achadas[0].consulta == "PREGAO na Bolsa: ações e mercado"
    assert (achadas[0].largura, achadas[0].altura) == (1200, 800)


def test_busca_empata_na_ordem_do_indice_e_titulo_tambem_pontua(biblioteca):
    adicionar(biblioteca, "primeira", ["energia"], titulo="Torre de transmissão.jpg")
    adicionar(biblioteca, "segunda", ["energia"], titulo="Linhas.jpg")
    adicionar(biblioteca, "so-titulo", ["outra"], titulo="Energia solar no telhado.jpg")
    achadas = biblioteca.buscar("energia")
    assert [i.arquivo.stem for i in achadas] == ["primeira", "segunda", "so-titulo"]


def test_busca_sem_termo_em_comum_ou_consulta_vazia_nao_devolve_nada(biblioteca):
    adicionar(biblioteca, "bolsa", ["bolsa"])
    assert biblioteca.buscar("criptomoeda") == []
    assert biblioteca.buscar("   de a o ") == []


def test_so_aprovada_sai_e_rejeitada_nunca(biblioteca):
    adicionar(biblioteca, "pendente", ["selic"], aprovada=False, validada_por=None)
    adicionar(biblioteca, "recusada", ["selic"])
    biblioteca.rejeitar("recusada")
    assert biblioteca.buscar("selic") == []
    assert [i.arquivo.stem for i in biblioteca.buscar("selic", apenas_aprovadas=False)] == ["pendente"]
    biblioteca.aprovar("pendente")
    assert [i.arquivo.stem for i in biblioteca.buscar("selic")] == ["pendente"]
    assert biblioteca.buscar("selic")[0].validada_por == "humano"


def test_indice_persiste_sem_deixar_temporarios_e_id_repetido_e_erro(biblioteca):
    adicionar(biblioteca, "uma", ["a1"])
    outra = BibliotecaDeImagens(biblioteca.pasta)
    assert [e.id for e in outra.listar()] == ["uma"]
    assert not list(biblioteca.pasta.glob("*.tmp"))
    assert json.loads(biblioteca.caminho_do_indice.read_text(encoding="utf-8"))[0]["id"] == "uma"
    with pytest.raises(ValueError):
        adicionar(biblioteca, "uma", ["a1"])
    with pytest.raises(ImagemInexistente):
        biblioteca.aprovar("nao-existe")
    with pytest.raises(ImagemInexistente):
        biblioteca.rejeitar("nao-existe")


def test_entrada_com_arquivo_sumido_nao_e_devolvida(biblioteca):
    adicionar(biblioteca, "some", ["selic"])
    (biblioteca.pasta / "some.jpg").unlink()
    assert biblioteca.buscar("selic") == []


def test_biblioteca_vazia_lista_vazio(tmp_path):
    biblioteca = BibliotecaDeImagens(tmp_path / "nada")
    assert biblioteca.listar() == []
    assert biblioteca.buscar("selic") == []


# ---------------------------------------------------------------------------
# Licença, autor e Commons
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "licenca",
    ["CC BY 2.0", "CC BY 4.0", "CC BY-SA 3.0", "CC BY-SA 4.0", "CC0", "CC0 1.0", "Public domain", "PD", "PD-old-70", "cc by 2.0"],
)
def test_licencas_livres_sao_aceitas(licenca):
    assert licenca_permitida(licenca)


@pytest.mark.parametrize(
    "licenca",
    ["CC BY-NC 2.0", "CC BY-NC-SA 4.0", "CC BY-ND 2.0", "CC BY-NC-ND 3.0", "All rights reserved", "Fair use", "GFDL", "", "CC BY"],
)
def test_licencas_com_restricao_sao_recusadas(licenca):
    assert not licenca_permitida(licenca)


def test_autor_sai_sem_html_estilo_nem_duplicado():
    assert limpar_autor("<a href='//x'>Ana <b>Souza</b></a>") == "Ana Souza"
    assert limpar_autor("Rafael &amp; Cia <style>.a{color:red}</style>") == "Rafael & Cia"
    assert limpar_autor("Ana Souza  .mw-parser-output .messagebox{margin:4px}Wikidata has entry Ana") == "Ana Souza"
    assert limpar_autor("<span>Unknown author</span><span>Unknown author</span>") == "Autor desconhecido"
    assert limpar_autor("") == "Autor desconhecido"


def test_commons_filtra_licenca_largura_restricao_e_ordena():
    commons = Commons(
        [
            pagina(3, "boa-tres.jpg", licenca="CC BY-SA 4.0"),
            pagina(1, "nc.jpg", licenca="CC BY-NC 2.0"),
            pagina(2, "pequena.jpg", largura=800),
            pagina(4, "sem-miniatura.jpg", miniatura=False),
            pagina(5, "marca.jpg", extra={"Restrictions": {"value": "trademarked"}}),
            pagina(6, "nao-livre.jpg", extra={"NonFree": {"value": "true"}}),
            pagina(0, "boa-zero.jpg", licenca="CC0", artista="<span>Bia</span>"),
            {"title": "File:sem-info.jpg", "index": 7},
        ]
    )
    candidatos = ClienteCommons(commons.cliente()).buscar("selic")
    assert [c.titulo for c in candidatos] == ["boa-zero.jpg", "boa-tres.jpg"]
    primeiro = candidatos[0]
    assert (primeiro.autor, primeiro.licenca, primeiro.consulta) == ("Bia", "CC0", "selic")
    assert primeiro.url_pagina == "https://commons.wikimedia.org/wiki/File:boa-zero.jpg"
    assert primeiro.url_miniatura.startswith("https://upload.wikimedia.org/")
    consulta = commons.chamadas[0]
    assert consulta.url.params["gsrnamespace"] == "6"
    assert consulta.url.params["generator"] == "search"
    assert consulta.url.params["iiurlwidth"] == "1200"
    assert "selic" in consulta.url.params["gsrsearch"]


def test_commons_aceita_resposta_no_formato_antigo_de_dicionario():
    def manipulador(_):
        pg = pagina(0, "a.jpg")
        return httpx.Response(200, json={"query": {"pages": {"11": pg}}})

    assert [c.titulo for c in ClienteCommons(cliente_com(manipulador)).buscar("x")] == ["a.jpg"]


def test_commons_manda_user_agent_identificavel(monkeypatch):
    vistos: list[str] = []

    def manipulador(requisicao):
        vistos.append(requisicao.headers["user-agent"])
        return httpx.Response(200, json=resposta_mediawiki())

    monkeypatch.setenv("SUNO_CONTATO", "SunoContent/9.9 (teste; contato: a@b.org)")
    from suno.imagens import commons

    transporte = httpx.MockTransport(manipulador)
    monkeypatch.setattr(
        commons,
        "cliente_padrao",
        lambda: httpx.Client(transport=transporte, headers={"User-Agent": commons.agente_de_usuario()}),
    )
    assert ClienteCommons().buscar("x") == []
    assert vistos == ["SunoContent/9.9 (teste; contato: a@b.org)"]


@pytest.mark.parametrize(
    "resposta",
    [
        httpx.Response(500, text="erro"),
        httpx.Response(429, text="devagar"),
        httpx.Response(200, text="<html>não é json</html>"),
        httpx.Response(200, json=["lista"]),
        httpx.Response(200, json={"error": {"code": "badvalue", "info": "parâmetro ruim"}}),
    ],
)
def test_commons_com_erro_levanta_excecao_tipada(resposta):
    with pytest.raises(FonteDeImagemIndisponivel):
        ClienteCommons(cliente_com(lambda _: resposta)).buscar("x")


def test_commons_sem_conexao_levanta_excecao_tipada():
    def cai(requisicao):
        raise httpx.ConnectError("sem rede", request=requisicao)

    with pytest.raises(FonteDeImagemIndisponivel):
        ClienteCommons(cliente_com(cai)).buscar("x")


def test_baixar_miniatura_devolve_bytes_e_erro_vira_excecao_tipada():
    commons = Commons([pagina(0, "a.jpg")], imagens={"a.jpg": b"bytes-da-foto"})
    cliente = ClienteCommons(commons.cliente())
    candidato = cliente.buscar("x")[0]
    assert cliente.baixar_miniatura(candidato) == b"bytes-da-foto"
    quebrado = ClienteCommons(cliente_com(lambda _: httpx.Response(404)))
    with pytest.raises(FonteDeImagemIndisponivel):
        quebrado.baixar_miniatura(candidato)


# ---------------------------------------------------------------------------
# Validação de relevância
# ---------------------------------------------------------------------------


def test_validacao_envia_png_ao_juiz_de_visao_e_devolve_o_parecer():
    provedor = ProvedorFalso({ROTULO: [APROVA]})
    parecer = validar_relevancia(jpeg(), "Selic", "Copom manteve a Selic", provedor)
    assert parecer.relevante and not parecer.inadequada and parecer.aprovada
    pedido = provedor.pedidos[0]
    assert pedido.papel == PapelLLM.JUIZ_VISAO
    imagem = pedido.mensagens[-1].imagem_png
    assert imagem is not None and imagem.startswith(b"\x89PNG")
    assert "Selic" in pedido.mensagens[-1].texto and "Copom manteve" in pedido.mensagens[-1].texto


def test_validacao_reduz_foto_grande():
    provedor = ProvedorFalso({ROTULO: [APROVA]})
    validar_relevancia(jpeg(3000, 2000), "x", "", provedor)
    enviada = Image.open(io.BytesIO(provedor.pedidos[0].mensagens[-1].imagem_png))
    assert max(enviada.size) <= 1024


def test_parecer_inadequado_nao_e_aprovado_mesmo_se_relevante():
    provedor = ProvedorFalso({ROTULO: [INADEQUADA]})
    assert not validar_relevancia(jpeg(), "x", "", provedor).aprovada


def test_validacao_recusa_bytes_que_nao_sao_imagem():
    with pytest.raises(ImagemIlegivel):
        validar_relevancia(b"isto nao e uma imagem", "x", "", ProvedorFalso({ROTULO: [APROVA]}))


# ---------------------------------------------------------------------------
# Resolvedor
# ---------------------------------------------------------------------------


def commons_com(*nomes: str) -> Commons:
    return Commons([pagina(i, nome) for i, nome in enumerate(nomes)])


def test_biblioteca_vence_e_nao_toca_a_rede(biblioteca):
    adicionar(biblioteca, "bcb", ["banco central", "selic"])
    commons = commons_com("a.jpg")
    achada = resolver_imagem(
        "Selic", biblioteca, permitir_rede=True, cliente=commons.cliente(), provedor_visao=ProvedorFalso({ROTULO: [APROVA]})
    )
    assert achada is not None and achada.origem == "biblioteca"
    assert commons.chamadas == []


def test_sem_rede_e_sem_acerto_devolve_none_sem_levantar(biblioteca):
    commons = commons_com("a.jpg")
    assert resolver_imagem("criptomoeda", biblioteca, cliente=commons.cliente()) is None
    assert commons.chamadas == []
    assert biblioteca.listar() == []


def test_rede_com_visao_aprova_grava_e_devolve(biblioteca):
    commons = commons_com("Edificio_BCB.jpg")
    visao = ProvedorFalso({ROTULO: [APROVA]})
    imagem = resolver_imagem(
        "sede do banco central", biblioteca, contexto="Copom", permitir_rede=True, cliente=commons.cliente(), provedor_visao=visao
    )
    assert imagem is not None
    assert (imagem.origem, imagem.validada_por) == ("commons", "visao")
    assert imagem.arquivo.is_file() and imagem.arquivo.parent == biblioteca.pasta
    assert imagem.credito() == (
        "Foto: Ana Souza / CC BY 2.0 / https://commons.wikimedia.org/wiki/File:Edificio_BCB.jpg"
    )
    [entrada] = biblioteca.listar()
    assert entrada.aprovada and entrada.validada_por == "visao" and entrada.consulta == "sede do banco central"
    # A segunda chamada já sai da biblioteca, sem rede.
    de_novo = resolver_imagem("banco central", biblioteca, cliente=cliente_com(lambda _: pytest.fail("rede")))
    assert de_novo is not None and de_novo.origem == "biblioteca" and de_novo.arquivo == imagem.arquivo


def test_reprovada_nao_e_devolvida_e_o_proximo_candidato_e_tentado(biblioteca):
    commons = commons_com("errada.jpg", "inadequada.jpg", "certa.jpg", "sobra.jpg")
    visao = ProvedorFalso({ROTULO: [REPROVA, INADEQUADA, APROVA]})
    imagem = resolver_imagem(
        "selic", biblioteca, permitir_rede=True, cliente=commons.cliente(), provedor_visao=visao
    )
    assert imagem is not None and imagem.titulo == "certa.jpg"
    assert [e.titulo for e in biblioteca.listar()] == ["certa.jpg"]  # as reprovadas nem ficam no disco
    assert len(commons.baixados()) == 3 and len(visao.pedidos) == 3


def test_todas_reprovadas_devolve_none_e_para_em_cinco_candidatos(biblioteca):
    commons = commons_com(*(f"f{i}.jpg" for i in range(8)))
    visao = ProvedorFalso({ROTULO: [REPROVA] * 8})
    assert (
        resolver_imagem("selic", biblioteca, permitir_rede=True, cliente=commons.cliente(), provedor_visao=visao)
        is None
    )
    assert len(visao.pedidos) == 5 and len(commons.baixados()) == 5
    assert biblioteca.listar() == []


def test_sem_provedor_de_visao_a_foto_fica_pendente_e_nao_e_devolvida(biblioteca):
    commons = commons_com("a.jpg", "b.jpg")
    assert resolver_imagem("selic", biblioteca, permitir_rede=True, cliente=commons.cliente()) is None
    [entrada] = biblioteca.listar()
    assert not entrada.aprovada and entrada.validada_por is None and entrada.titulo == "a.jpg"
    assert biblioteca.buscar("selic") == []
    assert len(commons.baixados()) == 1
    # O humano aprova, e a foto passa a valer.
    biblioteca.aprovar(entrada.id)
    achada = resolver_imagem("selic", biblioteca)
    assert achada is not None and achada.validada_por == "humano"


def test_falha_do_juiz_de_visao_deixa_pendente_e_devolve_none(biblioteca):
    commons = commons_com("a.jpg")
    visao = ProvedorFalso({ROTULO: [ErroProvedor("falso", "fora do ar")]})
    assert resolver_imagem("selic", biblioteca, permitir_rede=True, cliente=commons.cliente(), provedor_visao=visao) is None
    [entrada] = biblioteca.listar()
    assert not entrada.aprovada


def test_commons_fora_do_ar_devolve_none_sem_levantar(biblioteca):
    def cai(requisicao):
        raise httpx.ConnectError("sem rede", request=requisicao)

    assert resolver_imagem("selic", biblioteca, permitir_rede=True, cliente=cliente_com(cai)) is None


def test_candidato_com_licenca_nao_livre_nunca_chega_ao_juiz(biblioteca):
    commons = Commons([pagina(0, "nc.jpg", licenca="CC BY-NC 4.0")])
    visao = ProvedorFalso({ROTULO: [APROVA]})
    assert resolver_imagem("selic", biblioteca, permitir_rede=True, cliente=commons.cliente(), provedor_visao=visao) is None
    assert visao.pedidos == [] and commons.baixados() == []


def test_download_corrompido_e_pulado(biblioteca):
    commons = Commons(
        [pagina(0, "quebrada.jpg"), pagina(1, "boa.jpg")], imagens={"quebrada.jpg": b"nao e imagem"}
    )
    visao = ProvedorFalso({ROTULO: [APROVA]})
    imagem = resolver_imagem("selic", biblioteca, permitir_rede=True, cliente=commons.cliente(), provedor_visao=visao)
    assert imagem is not None and imagem.titulo == "boa.jpg"


def test_foto_rejeitada_a_mao_nao_volta_como_candidata(biblioteca):
    commons = commons_com("a.jpg", "b.jpg")
    assert resolver_imagem("selic", biblioteca, permitir_rede=True, cliente=commons.cliente()) is None
    biblioteca.rejeitar(biblioteca.listar()[0].id)
    visao = ProvedorFalso({ROTULO: [APROVA]})
    imagem = resolver_imagem("selic", biblioteca, permitir_rede=True, cliente=commons.cliente(), provedor_visao=visao)
    assert imagem is not None and imagem.titulo == "b.jpg"


def test_foto_ja_no_disco_e_reavaliada_para_o_assunto_novo(biblioteca):
    adicionar(biblioteca, "a", ["bolsa"], titulo="a.jpg", url_origem="https://commons.wikimedia.org/wiki/File:a.jpg")
    commons = commons_com("a.jpg")
    visao = ProvedorFalso({ROTULO: [APROVA]})
    imagem = resolver_imagem("pregão de ações", biblioteca, permitir_rede=True, cliente=commons.cliente(), provedor_visao=visao)
    assert imagem is not None and imagem.arquivo.stem == "a"
    assert commons.baixados() == []  # veio do disco
    assert len(biblioteca.listar()) == 1 and "pregão de ações" in biblioteca.listar()[0].tags


# ---------------------------------------------------------------------------
# Créditos e crédito de cada foto
# ---------------------------------------------------------------------------


def foto(autor: str = "Ana Souza", licenca: str = "CC BY 2.0", url: str = "https://c.org/a") -> ImagemResolvida:
    return ImagemResolvida(
        arquivo=Path("a.jpg"), titulo="a.jpg", autor=autor, licenca=licenca, url_origem=url,
        consulta="x", origem="biblioteca", validada_por="humano", largura=1200, altura=800,
    )


def test_credito_tem_o_formato_pedido_e_dominio_publico_tambem_sai():
    assert foto().credito() == "Foto: Ana Souza / CC BY 2.0 / https://c.org/a"
    assert foto().credito_obrigatorio()
    livre = foto(licenca="CC0")
    assert not livre.credito_obrigatorio()
    assert livre.credito() == "Foto: Ana Souza / CC0 / https://c.org/a"


def test_bloco_de_creditos_sem_repeticao_e_na_ordem_de_entrada():
    a, b = foto(), foto(autor="Bia", url="https://c.org/b")
    assert bloco_de_creditos([]) == ""
    assert bloco_de_creditos([a, b, a]).splitlines() == [a.credito(), b.credito()]


# ---------------------------------------------------------------------------
# A biblioteca semeada em data/imagens/
# ---------------------------------------------------------------------------


def test_indice_semeado_carrega_e_todo_arquivo_existe():
    biblioteca = BibliotecaDeImagens(PASTA_SEMEADA)
    entradas = biblioteca.listar()
    assert {e.id for e in entradas} >= {
        "bcb-sede", "galipolo", "bolsa-sp", "dinheiro", "analise",
        "contas-luz", "fila-combustivel", "mercado-imobiliario", "pregao",
    }
    for e in entradas:
        assert (PASTA_SEMEADA / e.arquivo).is_file(), e.id
        assert e.aprovada and e.validada_por == "humano", e.id
        assert licenca_permitida(e.licenca), e.id
        assert e.url_origem.startswith("https://commons.wikimedia.org/wiki/File:"), e.id
        assert "<" not in e.autor and "{" not in e.autor and e.autor.strip(), e.id
        assert e.tags and e.largura >= 900, e.id


def test_busca_na_biblioteca_semeada_acha_o_assunto_certo():
    biblioteca = BibliotecaDeImagens(PASTA_SEMEADA)
    assert biblioteca.buscar("Copom mantém a Selic")[0].arquivo.stem == "bcb-sede"
    assert biblioteca.buscar("Galípolo, presidente do Banco Central")[0].arquivo.stem == "galipolo"
    assert biblioteca.buscar("conta de luz mais cara")[0].arquivo.stem == "contas-luz"
    assert biblioteca.buscar("greve e fila nos postos de gasolina")[0].arquivo.stem == "fila-combustivel"
    assert biblioteca.buscar("criptomoeda") == []


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def test_cli_listar_buscar_e_aprovar(biblioteca, capsys):
    from suno.cli import main

    adicionar(biblioteca, "pend", ["selic"], aprovada=False, validada_por=None)
    pasta = str(biblioteca.pasta)
    assert main(["imagens", "--pasta", pasta, "buscar", "selic"]) == 1
    assert main(["imagens", "--pasta", pasta, "aprovar", "pend"]) == 0
    capsys.readouterr()
    assert main(["imagens", "--pasta", pasta, "buscar", "selic"]) == 0
    saida = capsys.readouterr().out
    assert "Foto: Ana Souza / CC BY 2.0 /" in saida
    assert main(["imagens", "--pasta", pasta, "aprovar", "fantasma"]) == 1
    assert main(["imagens", "--pasta", pasta, "listar"]) == 0
    assert "pend" in capsys.readouterr().out
