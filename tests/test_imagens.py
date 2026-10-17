"""O pacote de imagens: biblioteca, busca na web (transporte simulado), validação e resolvedor.

Tudo offline: o buscador é um ``httpx.MockTransport`` e o juiz de visão é o ``ProvedorFalso``.
"""

from __future__ import annotations

import html
import io
import json
from pathlib import Path

import httpx
import pytest
from PIL import Image

from suno.dominio import ErroProvedor, PapelLLM
from suno.imagens import (
    BibliotecaDeImagens,
    ClienteWeb,
    FonteDeImagemIndisponivel,
    ImagemInexistente,
    ImagemResolvida,
    bloco_de_creditos,
    resolver_imagem,
    validar_relevancia,
)
from suno.imagens.texto import termos
from suno.imagens.validacao import ROTULO, ImagemIlegivel
from suno.imagens.web import SEM_LICENCA, ClienteSerper, buscador_padrao
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


def resultado(nome: str, *, dominio: str = "noticias.com.br", titulo: str | None = None, imagem: str | None = None) -> dict:
    return {
        "murl": imagem or f"https://{dominio}/fotos/{nome}",
        "purl": f"https://{dominio}/materia/{nome}",
        "turl": f"https://ts1.mm.bing.net/th?id={nome}",
        "t": titulo or f"Selic em {nome}",
    }


def html_de_resultados(*resultados: dict) -> str:
    """A página do Bing Imagens: cada resultado traz um JSON no atributo ``m`` com HTML escapado."""
    itens = "".join(f'<a class="iusc" m="{html.escape(json.dumps(r), quote=True)}"></a>' for r in resultados)
    return f'<html><body><div id="b_content">{itens}</div></body></html>'


class Buscador:
    """Um Bing de mentira em cima de ``httpx.MockTransport``; conta as chamadas."""

    def __init__(self, resultados: list[dict], *, imagens: dict[str, bytes] | None = None) -> None:
        self.resultados = resultados
        self.imagens = imagens or {}
        self.chamadas: list[httpx.Request] = []

    def __call__(self, requisicao: httpx.Request) -> httpx.Response:
        self.chamadas.append(requisicao)
        if requisicao.url.host == "www.bing.com":
            return httpx.Response(200, content=html_de_resultados(*self.resultados).encode("utf-8"))
        nome = requisicao.url.path.rsplit("/", 1)[-1]
        return httpx.Response(200, content=self.imagens.get(nome, jpeg()))

    def cliente(self) -> httpx.Client:
        return httpx.Client(transport=httpx.MockTransport(self), headers={"User-Agent": "teste"})

    def baixados(self) -> list[str]:
        return [c.url.path for c in self.chamadas if c.url.host != "www.bing.com"]


def cliente_com(manipulador) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(manipulador))


@pytest.fixture(autouse=True)
def sem_pausa_entre_tentativas(monkeypatch):
    monkeypatch.setattr("suno.imagens.web.time.sleep", lambda _: None)
    monkeypatch.delenv("SERPER_API_KEY", raising=False)


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
        "url_origem": f"https://noticias.com.br/materia/{identificador}.jpg",
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
# Busca de imagens na web
# ---------------------------------------------------------------------------


def test_busca_devolve_candidatos_na_ordem_com_dominio_como_autor_e_sem_licenca():
    buscador = Buscador([resultado("a.jpg", dominio="www.b3.com.br"), resultado("b.jpg", dominio="infomoney.com.br")])
    candidatos = ClienteWeb(buscador.cliente()).buscar("sede da B3")
    assert [c.url_imagem.rsplit("/", 1)[-1] for c in candidatos] == ["a.jpg", "b.jpg"]
    primeiro = candidatos[0]
    assert (primeiro.autor, primeiro.licenca, primeiro.consulta) == ("b3.com.br", SEM_LICENCA, "sede da B3")
    assert primeiro.url_pagina == "https://www.b3.com.br/materia/a.jpg"
    assert primeiro.titulo == "Selic em a.jpg"
    pedido = buscador.chamadas[0]
    assert pedido.url.params["q"] == "sede da B3"
    assert "imagesize-large" in pedido.url.params["qft"]


def test_busca_descarta_repetidas_sem_url_valida_e_banco_de_imagem_pago():
    buscador = Buscador(
        [
            resultado("a.jpg"),
            resultado("a.jpg"),
            resultado("b.jpg", imagem="data:image/png;base64,AAAA"),
            resultado("c.jpg", dominio="www.istockphoto.com"),
            resultado("d.jpg", dominio="br.shutterstock.com"),
            resultado("e.jpg", dominio="noticias.com.br", imagem="https://media.gettyimages.com/x/e.jpg"),
            resultado("f.jpg"),
        ]
    )
    candidatos = ClienteWeb(buscador.cliente()).buscar("x")
    assert [c.url_imagem.rsplit("/", 1)[-1] for c in candidatos] == ["a.jpg", "f.jpg"]


def test_busca_respeita_o_limite_e_entende_titulo_com_acento():
    buscador = Buscador([resultado(f"{i}.jpg", titulo="  Bolsa   às 10h  ") for i in range(10)])
    candidatos = ClienteWeb(buscador.cliente()).buscar("x", limite=3)
    assert len(candidatos) == 3 and candidatos[0].titulo == "Bolsa às 10h"


def test_busca_tenta_de_novo_quando_o_bing_serve_o_html_degradado():
    cheia = html_de_resultados(*(resultado(f"{i}.jpg") for i in range(8)))
    degradada = html_de_resultados(resultado("sozinha.jpg"))
    respostas = iter([degradada, degradada, cheia])
    cliente = httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(200, text=next(respostas))))
    assert len(ClienteWeb(cliente).buscar("x")) == 8


def test_busca_desiste_depois_das_tentativas_e_devolve_o_que_achou():
    chamadas: list[int] = []

    def manipulador(_):
        chamadas.append(1)
        return httpx.Response(200, text=html_de_resultados(resultado("sozinha.jpg")))

    assert len(ClienteWeb(cliente_com(manipulador)).buscar("x")) == 1
    assert len(chamadas) == 4


def test_busca_ignora_metadado_quebrado():
    pagina = (
        '<div id="b_content"><a m="isto nao e json"></a><a m="[1, 2]"></a>'
        f'<a m="{html.escape(json.dumps(resultado("ok.jpg")), quote=True)}"></a></div>'
    )
    cliente = httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(200, text=pagina)))
    assert [c.titulo for c in ClienteWeb(cliente).buscar("x")] == ["Selic em ok.jpg"]


@pytest.mark.parametrize(
    "resposta",
    [
        httpx.Response(500, text="erro"),
        httpx.Response(429, text="devagar"),
        httpx.Response(200, text="{\"isto\": \"é json, não a página\"}"),
    ],
)
def test_busca_com_erro_levanta_excecao_tipada(resposta):
    with pytest.raises(FonteDeImagemIndisponivel):
        ClienteWeb(cliente_com(lambda _: resposta)).buscar("x")


def test_busca_sem_conexao_levanta_excecao_tipada():
    def cai(requisicao):
        raise httpx.ConnectError("sem rede", request=requisicao)

    with pytest.raises(FonteDeImagemIndisponivel):
        ClienteWeb(cliente_com(cai)).buscar("x")


def test_baixar_devolve_bytes_e_erro_ou_arquivo_vazio_vira_excecao_tipada():
    buscador = Buscador([resultado("a.jpg")], imagens={"a.jpg": b"bytes-da-foto"})
    web = ClienteWeb(buscador.cliente())
    candidato = web.buscar("x")[0]
    assert web.baixar(candidato) == b"bytes-da-foto"
    assert buscador.chamadas[-1].headers["referer"] == candidato.url_pagina
    with pytest.raises(FonteDeImagemIndisponivel):
        ClienteWeb(cliente_com(lambda _: httpx.Response(403))).baixar(candidato)
    with pytest.raises(FonteDeImagemIndisponivel):
        ClienteWeb(cliente_com(lambda _: httpx.Response(200, content=b""))).baixar(candidato)


def test_url_de_origem_com_acento_nao_quebra_o_cabecalho_referer_nem_o_download():
    buscador = Buscador([resultado("a.jpg")])
    web = ClienteWeb(buscador.cliente())
    candidato = web.buscar("x")[0].model_copy(update={"url_pagina": "https://site.com.br/proclamação-da-república"})
    assert web.baixar(candidato)
    assert buscador.chamadas[-1].headers["referer"] == "https://site.com.br/proclama%C3%A7%C3%A3o-da-rep%C3%BAblica"


# ---------------------------------------------------------------------------
# Serper (Google Imagens)
# ---------------------------------------------------------------------------


def imagem_do_serper(nome: str, *, largura: int = 1600, dominio: str = "noticias.com.br") -> dict:
    return {
        "title": f"Selic em {nome}",
        "imageUrl": f"https://{dominio}/fotos/{nome}",
        "imageWidth": largura,
        "imageHeight": 900,
        "link": f"https://{dominio}/materia/{nome}",
        "domain": dominio,
    }


def serper_com(itens: list[dict], vistos: list | None = None, status: int = 200) -> httpx.Client:
    def manipulador(requisicao: httpx.Request) -> httpx.Response:
        if requisicao.url.host == "google.serper.dev":
            if vistos is not None:
                vistos.append(requisicao)
            return httpx.Response(status, json={"images": itens})
        return httpx.Response(200, content=jpeg())

    return cliente_com(manipulador)


def test_serper_manda_a_chave_a_consulta_em_portugues_e_devolve_candidatos():
    vistos: list[httpx.Request] = []
    cliente = serper_com([imagem_do_serper("a.jpg"), imagem_do_serper("b.jpg", largura=500), imagem_do_serper("a.jpg")], vistos)
    candidatos = ClienteSerper("segredo", cliente).buscar("sede da B3")
    assert [c.url_imagem.rsplit("/", 1)[-1] for c in candidatos] == ["a.jpg"]  # a pequena e a repetida saem
    assert candidatos[0].autor == "noticias.com.br" and candidatos[0].licenca == SEM_LICENCA
    pedido = vistos[0]
    assert pedido.headers["x-api-key"] == "segredo"
    corpo = json.loads(pedido.content)
    assert corpo["q"] == "sede da B3" and corpo["gl"] == "br" and corpo["hl"] == "pt-br"


def test_serper_pede_so_fotos_e_cai_para_a_busca_sem_filtro_quando_vierem_poucas():
    vistos: list[httpx.Request] = []
    cliente = serper_com([imagem_do_serper("a.jpg")], vistos)
    ClienteSerper("k", cliente).buscar("CDI renda fixa investimento")
    assert [json.loads(r.content).get("tbs") for r in vistos] == ["itp:photo", None]

    cheio: list[httpx.Request] = []
    abundante = serper_com([imagem_do_serper(f"{i}.jpg") for i in range(5)], cheio)
    assert len(ClienteSerper("k", abundante).buscar("CDI")) == 5
    assert len(cheio) == 1, "com fotos suficientes não gasta a segunda consulta"


def test_serper_nao_filtra_por_foto_na_busca_de_logo():
    vistos: list[httpx.Request] = []
    ClienteSerper("k", serper_com([imagem_do_serper("a.png")], vistos)).buscar("Nubank banco digital logo")
    assert all("tbs" not in json.loads(r.content) for r in vistos)


def test_serper_descarta_banco_de_imagem_pago():
    cliente = serper_com([imagem_do_serper("a.jpg", dominio="www.shutterstock.com"), imagem_do_serper("b.jpg")])
    assert [c.titulo for c in ClienteSerper("k", cliente).buscar("x")] == ["Selic em b.jpg"]


@pytest.mark.parametrize("status", [401, 403, 429, 500])
def test_serper_com_erro_levanta_excecao_tipada(status):
    with pytest.raises(FonteDeImagemIndisponivel):
        ClienteSerper("k", serper_com([], status=status)).buscar("x")


def test_buscador_padrao_usa_serper_so_com_chave(monkeypatch):
    assert type(buscador_padrao()) is ClienteWeb
    monkeypatch.setenv("SERPER_API_KEY", "  chave  ")
    assert isinstance(buscador_padrao(), ClienteSerper)


def test_resolvedor_usa_o_serper_quando_ha_chave(monkeypatch, biblioteca):
    monkeypatch.setenv("SERPER_API_KEY", "k")
    cliente = serper_com([imagem_do_serper("logo-b3.png", dominio="logospng.org")])
    imagem = resolver_imagem("logo da B3", biblioteca, permitir_rede=True, cliente=cliente)
    assert imagem is not None and (imagem.origem, imagem.validada_por) == ("web", "texto")
    assert imagem.autor == "logospng.org"


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


def web_com(*nomes: str) -> Buscador:
    return Buscador([resultado(nome) for nome in nomes])


def test_biblioteca_vence_e_nao_toca_a_rede(biblioteca):
    adicionar(biblioteca, "bcb", ["banco central", "selic"])
    web = web_com("a.jpg")
    achada = resolver_imagem(
        "Selic", biblioteca, permitir_rede=True, cliente=web.cliente(), provedor_visao=ProvedorFalso({ROTULO: [APROVA]})
    )
    assert achada is not None and achada.origem == "biblioteca"
    assert web.chamadas == []


def test_foto_da_biblioteca_so_vale_se_citar_o_assunto_e_nao_so_dividir_uma_palavra(biblioteca):
    adicionar(biblioteca, "caixa", ["caixa economica federal"], titulo="Sede da Caixa Econômica Federal")
    adicionar(biblioteca, "nubank", ["logo nubank", "banco digital"], titulo="Cartão Nubank")
    # "federal" e "logo" são termos em comum, mas o assunto é outro.
    assert resolver_imagem("Federal Reserve", biblioteca) is None
    assert resolver_imagem("logo do Banco Central", biblioteca) is None
    assert resolver_imagem("Banco Inter", biblioteca) is None
    # Título de matéria que cita o assunto não basta: a foto de ouro não é da China.
    adicionar(biblioteca, "ouro", ["ouro"], titulo="Apesar das tensões entre EUA e China, ouro sobe")
    assert resolver_imagem("China", biblioteca) is None
    # O assunto certo continua saindo da biblioteca.
    assert resolver_imagem("Caixa Econômica Federal", biblioteca).arquivo.stem == "caixa"
    assert resolver_imagem("logo Nubank", biblioteca).arquivo.stem == "nubank"


def test_sem_rede_e_sem_acerto_devolve_none_sem_levantar(biblioteca):
    web = web_com("a.jpg")
    assert resolver_imagem("criptomoeda", biblioteca, cliente=web.cliente()) is None
    assert web.chamadas == []
    assert biblioteca.listar() == []


def test_rede_com_visao_aprova_grava_e_devolve(biblioteca):
    web = Buscador([resultado("Edificio_BCB.jpg", titulo="Prédio em Brasília")])
    visao = ProvedorFalso({ROTULO: [APROVA]})
    imagem = resolver_imagem(
        "sede do banco central", biblioteca, contexto="Copom", permitir_rede=True, cliente=web.cliente(), provedor_visao=visao
    )
    assert imagem is not None
    assert (imagem.origem, imagem.validada_por) == ("web", "visao")
    assert imagem.arquivo.is_file() and imagem.arquivo.parent == biblioteca.pasta
    assert imagem.credito() == (
        f"Foto: noticias.com.br / {SEM_LICENCA} / https://noticias.com.br/materia/Edificio_BCB.jpg"
    )
    [entrada] = biblioteca.listar()
    assert entrada.aprovada and entrada.validada_por == "visao" and entrada.consulta == "sede do banco central"
    # A segunda chamada já sai da biblioteca, sem rede.
    de_novo = resolver_imagem("banco central", biblioteca, cliente=cliente_com(lambda _: pytest.fail("rede")))
    assert de_novo is not None and de_novo.origem == "biblioteca" and de_novo.arquivo == imagem.arquivo


def test_resultado_que_cita_o_assunto_e_aprovado_pelo_texto_sem_chamar_o_juiz(biblioteca):
    web = Buscador([resultado("logo-b3-bolsa.png", dominio="logospng.org", titulo="Logo B3 Brasil Bolsa de Valores")])
    visao = ProvedorFalso({ROTULO: []})
    imagem = resolver_imagem("logo da B3", biblioteca, permitir_rede=True, cliente=web.cliente(), provedor_visao=visao)
    assert imagem is not None and (imagem.origem, imagem.validada_por) == ("web", "texto")
    assert visao.pedidos == []
    # ...e também sem nenhum provedor de visão configurado.
    outra = BibliotecaDeImagens(biblioteca.pasta.parent / "outra")
    sem_juiz = resolver_imagem("logo da B3", outra, permitir_rede=True, cliente=web.cliente())
    assert sem_juiz is not None and sem_juiz.validada_por == "texto"


def test_a_busca_usa_a_consulta_do_catalogo_e_logo_vai_primeiro_se_o_slide_pediu(biblioteca):
    web = Buscador([])
    resolver_imagem("logo Nubank", biblioteca, permitir_rede=True, cliente=web.cliente())
    pesquisas = [c.url.params["q"] for c in web.chamadas if c.url.host == "www.bing.com"]
    assert pesquisas[0].startswith("Nubank banco digital logo")
    assert "-vitamina" in pesquisas[0]


def test_homonimo_da_lista_de_proibidas_nunca_e_baixado_nem_julgado(biblioteca):
    web = Buscador([resultado("vitamina-b3-2.jpeg", dominio="nutries.com.br", titulo="Vitamina B3: para que serve")])
    visao = ProvedorFalso({ROTULO: [APROVA]})
    assert resolver_imagem("B3", biblioteca, permitir_rede=True, cliente=web.cliente(), provedor_visao=visao) is None
    assert web.baixados() == [] and visao.pedidos == []


def test_resultado_sem_nenhum_indicio_no_texto_nem_gasta_o_juiz(biblioteca):
    web = Buscador([resultado("a.jpg", titulo="Tintas esmalte 18 litros"), resultado("b.jpg", titulo="Séries de TV")])
    visao = ProvedorFalso({ROTULO: [APROVA]})
    assert resolver_imagem("Petrobras", biblioteca, permitir_rede=True, cliente=web.cliente(), provedor_visao=visao) is None
    assert visao.pedidos == [] and web.baixados() == []


def test_banner_e_descartado_pela_proporcao(biblioteca):
    web = Buscador([resultado("faixa.jpg", titulo="Logo B3 bolsa de valores")], imagens={"faixa.jpg": jpeg(2000, 400)})
    assert resolver_imagem("B3", biblioteca, permitir_rede=True, cliente=web.cliente()) is None
    assert biblioteca.listar() == []


def test_reprovada_nao_e_devolvida_e_o_proximo_candidato_e_tentado(biblioteca):
    web = web_com("errada.jpg", "inadequada.jpg", "certa.jpg", "sobra.jpg")
    visao = ProvedorFalso({ROTULO: [REPROVA, INADEQUADA, APROVA]})
    imagem = resolver_imagem(
        "selic", biblioteca, permitir_rede=True, cliente=web.cliente(), provedor_visao=visao
    )
    assert imagem is not None and imagem.titulo == "Selic em certa.jpg"
    assert [e.titulo for e in biblioteca.listar()] == ["Selic em certa.jpg"]  # as reprovadas nem ficam no disco
    assert len(web.baixados()) == 3 and len(visao.pedidos) == 3


def test_todas_reprovadas_devolve_none_e_para_em_tres_duvidas(biblioteca):
    web = web_com(*(f"f{i}.jpg" for i in range(8)))
    visao = ProvedorFalso({ROTULO: [REPROVA] * 8})
    assert (
        resolver_imagem("selic", biblioteca, permitir_rede=True, cliente=web.cliente(), provedor_visao=visao)
        is None
    )
    assert len(visao.pedidos) == 3 and len(web.baixados()) == 3
    assert biblioteca.listar() == []


def test_sem_provedor_de_visao_a_foto_fica_pendente_e_nao_e_devolvida(biblioteca):
    web = web_com("a.jpg", "b.jpg")
    assert resolver_imagem("selic", biblioteca, permitir_rede=True, cliente=web.cliente()) is None
    [entrada] = biblioteca.listar()
    assert not entrada.aprovada and entrada.validada_por is None and entrada.titulo == "Selic em a.jpg"
    assert biblioteca.buscar("selic") == []
    assert len(web.baixados()) == 1
    # O humano aprova, e a foto passa a valer.
    biblioteca.aprovar(entrada.id)
    achada = resolver_imagem("selic", biblioteca)
    assert achada is not None and achada.validada_por == "humano"


def test_falha_do_juiz_de_visao_deixa_pendente_e_devolve_none(biblioteca):
    web = web_com("a.jpg")
    visao = ProvedorFalso({ROTULO: [ErroProvedor("falso", "fora do ar")]})
    assert resolver_imagem("selic", biblioteca, permitir_rede=True, cliente=web.cliente(), provedor_visao=visao) is None
    [entrada] = biblioteca.listar()
    assert not entrada.aprovada


def test_busca_fora_do_ar_devolve_none_sem_levantar(biblioteca):
    def cai(requisicao):
        raise httpx.ConnectError("sem rede", request=requisicao)

    assert resolver_imagem("selic", biblioteca, permitir_rede=True, cliente=cliente_com(cai)) is None


def test_banco_de_imagem_pago_nunca_chega_ao_juiz(biblioteca):
    web = Buscador([resultado("a.jpg", dominio="www.istockphoto.com")])
    visao = ProvedorFalso({ROTULO: [APROVA]})
    assert resolver_imagem("selic", biblioteca, permitir_rede=True, cliente=web.cliente(), provedor_visao=visao) is None
    assert visao.pedidos == [] and web.baixados() == []


def test_imagem_pequena_e_descartada_sem_gastar_chamada_de_visao(biblioteca):
    web = Buscador(
        [resultado("pequena.jpg"), resultado("boa.jpg")], imagens={"pequena.jpg": jpeg(600, 400)}
    )
    visao = ProvedorFalso({ROTULO: [APROVA]})
    imagem = resolver_imagem("selic", biblioteca, permitir_rede=True, cliente=web.cliente(), provedor_visao=visao)
    assert imagem is not None and imagem.titulo == "Selic em boa.jpg"
    assert len(visao.pedidos) == 1


def test_download_bloqueado_nao_conta_no_limite_de_duvidas(biblioteca):
    web = Buscador([resultado(f"f{i}.jpg") for i in range(9)])
    original = web.__call__

    def manipulador(requisicao):
        if requisicao.url.host != "www.bing.com" and requisicao.url.path.endswith(("f0.jpg", "f1.jpg", "f2.jpg")):
            return httpx.Response(403)
        return original(requisicao)

    visao = ProvedorFalso({ROTULO: [REPROVA] * 9})
    cliente = cliente_com(manipulador)
    assert resolver_imagem("selic", biblioteca, permitir_rede=True, cliente=cliente, provedor_visao=visao) is None
    assert len(visao.pedidos) == 3  # os três bloqueados não gastaram visão


def test_download_corrompido_e_pulado(biblioteca):
    web = Buscador([resultado("quebrada.jpg"), resultado("boa.jpg")], imagens={"quebrada.jpg": b"nao e imagem"})
    visao = ProvedorFalso({ROTULO: [APROVA]})
    imagem = resolver_imagem("selic", biblioteca, permitir_rede=True, cliente=web.cliente(), provedor_visao=visao)
    assert imagem is not None and imagem.titulo == "Selic em boa.jpg"


def test_foto_rejeitada_a_mao_nao_volta_como_candidata(biblioteca):
    web = web_com("a.jpg", "b.jpg")
    assert resolver_imagem("selic", biblioteca, permitir_rede=True, cliente=web.cliente()) is None
    biblioteca.rejeitar(biblioteca.listar()[0].id)
    visao = ProvedorFalso({ROTULO: [APROVA]})
    imagem = resolver_imagem("selic", biblioteca, permitir_rede=True, cliente=web.cliente(), provedor_visao=visao)
    assert imagem is not None and imagem.titulo == "Selic em b.jpg"


def test_foto_ja_no_disco_e_reavaliada_para_o_assunto_novo(biblioteca):
    adicionar(biblioteca, "a", ["bolsa"], titulo="a.jpg", url_origem="https://noticias.com.br/materia/a.jpg")
    web = Buscador([resultado("a.jpg", titulo="Pregão na bolsa")])
    visao = ProvedorFalso({ROTULO: [APROVA]})
    imagem = resolver_imagem("pregão de ações", biblioteca, permitir_rede=True, cliente=web.cliente(), provedor_visao=visao)
    assert imagem is not None and imagem.arquivo.stem == "a"
    assert web.baixados() == []  # veio do disco
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
    # IDs do índice versionado: a biblioteca também recebe fotos locais validadas
    # por texto/visão, que não prometem a curadoria humana destas nove sementes.
    sementes = {
        "bcb-sede", "galipolo", "bolsa-sp", "dinheiro", "analise",
        "contas-luz", "fila-combustivel", "mercado-imobiliario", "pregao",
    }
    entradas = {e.id: e for e in biblioteca.listar()}
    assert entradas.keys() >= sementes
    for identificador in sorted(sementes):
        e = entradas[identificador]
        assert (PASTA_SEMEADA / e.arquivo).is_file(), e.id
        assert e.aprovada and e.validada_por == "humano", e.id
        assert e.licenca.strip() and e.url_origem.startswith("https://"), e.id
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
