"""Os coletores das Origens: cada um sabe listar o que saiu numa janela de dias (barato, só metadados)
e baixar um item dessa lista (caro, um documento por vez).

A busca é em duas etapas porque a janela de 30 dias pode trazer dezenas de documentos, e a CVM
pede 10 s entre downloads: a pessoa vê quantos há, escolhe um período, e só então se baixa
(``suno.origens.atualizacao``). Nada aqui roda no meio de uma execução, e tudo precisa de rede.

Fontes testadas em 2026-10-12 (pesquisa em ``docs/research/viabilidade-tecnica.md``, §1, e ADR 0029):

- Copom, Relatório de Inflação e de Estabilidade Financeira: API não documentada do site do BCB.
- Resoluções do CMN e do BCB: a busca de normas do BCB (``api/search/app/normativos``).
- CVM (Fatos Relevantes, DFP, ITR e Formulários): dados abertos, IPE, com o PDF no RAD.
- Ofícios e comunicados da B3: a página pública de regulação, que lista no HTML e filtra por data.
"""

from __future__ import annotations

import html
import re
import unicodedata
import weakref
import zipfile
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import quote, urljoin

import httpx

from suno.dominio import CategoriaDaAta
from suno.ingestao.bcb import ErroDeIngestao, _user_agent, listar_atas
from suno.ingestao.pdf import eh_pdf, gravar_ao_lado
from suno.origens import cvm as cvm_mod

JANELA_DA_BUSCA_EM_DIAS = 30
LIMITE_DO_DOCUMENTO = 15 * 1024 * 1024
TENTATIVAS = 2
TITULO_MAXIMO = 150

_BASE_BCB = "https://www.bcb.gov.br"
_URL_B3 = "https://www.b3.com.br/pt_br/regulacao/oficios-e-comunicados/"
_MESES = (
    "jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez",
)


@dataclass(frozen=True)
class Candidato:
    """Um documento que a Origem publicou na janela e que ainda não está em disco."""

    origem: str
    identificador: str
    titulo: str
    data: date
    carga: dict[str, str] = field(default_factory=dict, compare=False)


class Coletor(Protocol):
    origem: str
    espera_s: float
    """Pausa entre dois downloads da mesma Origem (``Crawl-Delay`` da CVM: 10 s)."""

    def listar(self, cliente: httpx.Client, desde: date, hoje: date) -> list[Candidato]: ...

    def baixar(self, cliente: httpx.Client, candidato: Candidato, destino: Path) -> None: ...


def cliente_padrao() -> httpx.Client:
    return httpx.Client(headers={"User-Agent": _user_agent()}, timeout=60.0, follow_redirects=True)


def _pegar(cliente: httpx.Client, url: str, **parametros: Any) -> httpx.Response:
    # Os sites oficiais travam de vez em quando (a B3 atrás de Cloudflare, sobretudo): uma segunda
    # tentativa resolve a maioria dos tempos esgotados.
    for tentativa in range(TENTATIVAS):
        try:
            resposta = cliente.get(url, **parametros)
            break
        except (httpx.TimeoutException, httpx.ConnectError) as erro:
            if tentativa == TENTATIVAS - 1:
                raise ErroDeIngestao(f"falha ao falar com {url.split('/')[2]}: {erro}") from erro
        except httpx.HTTPError as erro:
            raise ErroDeIngestao(f"falha ao falar com {url.split('/')[2]}: {erro}") from erro
    if resposta.status_code != 200:
        raise ErroDeIngestao(f"{url.split('/')[2]} respondeu {resposta.status_code}")
    return resposta


def _json(resposta: httpx.Response) -> Any:
    try:
        return resposta.json()
    except ValueError as erro:
        raise ErroDeIngestao(f"resposta que não é JSON: {erro}") from erro


def _data_iso(bruto: str | None) -> date | None:
    try:
        return date.fromisoformat((bruto or "").strip()[:10])
    except ValueError:
        return None


def _mes_e_ano(dia: date) -> str:
    return f"{_MESES[dia.month - 1]}/{dia.year}"


def _lapidar(titulo: str) -> str:
    return re.sub(r"\s+", " ", titulo).strip()[:TITULO_MAXIMO]


def _sem_acento(texto: str) -> str:
    return unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode().lower()


def _identificador(texto: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", _sem_acento(texto)).strip("-")[:80]


def _gravar_pdf(
    destino: Path, identificador: str, conteudo: bytes, metadados: dict[str, Any]
) -> None:
    """Grava PDF, texto e metadados lado a lado; um PDF quebrado não deixa rastro pela metade."""
    if len(conteudo) > LIMITE_DO_DOCUMENTO:
        raise ErroDeIngestao(f"{identificador}: o documento passa de 15 MB")
    if not eh_pdf(conteudo):
        raise ErroDeIngestao(f"{identificador}: o documento não é PDF pelos bytes")
    destino.mkdir(parents=True, exist_ok=True)
    caminho = destino / f"{identificador}.pdf"
    caminho.write_bytes(conteudo)
    try:
        gravar_ao_lado(caminho, {"identificador": identificador, "idioma": "pt", **metadados})
    except Exception as erro:  # noqa: BLE001 - pypdf levanta tipos variados
        for sufixo in (".pdf", ".txt", ".json"):
            caminho.with_suffix(sufixo).unlink(missing_ok=True)
        raise ErroDeIngestao(f"{identificador}: o PDF veio ilegível: {erro}") from erro
    if not caminho.with_suffix(".txt").read_text(encoding="utf-8").strip():
        for sufixo in (".pdf", ".txt", ".json"):
            caminho.with_suffix(sufixo).unlink(missing_ok=True)
        raise ErroDeIngestao(f"{identificador}: o PDF não tem texto (parece escaneado)")


def _gravar_texto(
    destino: Path, identificador: str, texto: str, metadados: dict[str, Any]
) -> None:
    import json

    destino.mkdir(parents=True, exist_ok=True)
    caminho = destino / f"{identificador}.txt"
    caminho.write_text(texto, encoding="utf-8")
    (destino / f"{identificador}.json").write_text(
        json.dumps(
            {"identificador": identificador, "idioma": "pt", "caracteres": len(texto), **metadados},
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# BCB: Copom, Relatório de Inflação, Relatório de Estabilidade Financeira
# ---------------------------------------------------------------------------


class ColetorDoCopom:
    origem = "copom"
    espera_s = 1.0

    def listar(self, cliente: httpx.Client, desde: date, hoje: date) -> list[Candidato]:
        candidatos = []
        for registro in listar_atas(quantidade=15, cliente=cliente):
            dia = registro["data_referencia"]
            if dia is None or dia < desde or registro["reuniao"] is None:
                continue
            candidatos.append(
                Candidato(
                    origem=self.origem,
                    identificador=f"copom-{registro['reuniao']}-{dia.isoformat()}",
                    titulo=_lapidar(registro.get("Titulo", "Ata do Copom")),
                    data=dia,
                    carga={"url": _BASE_BCB + registro["Url"], "reuniao": str(registro["reuniao"])},
                )
            )
        return candidatos

    def baixar(self, cliente: httpx.Client, candidato: Candidato, destino: Path) -> None:
        resposta = _pegar(cliente, candidato.carga["url"])
        _gravar_pdf(
            destino,
            candidato.identificador,
            resposta.content,
            {
                "titulo": candidato.titulo,
                "reuniao": int(candidato.carga["reuniao"]),
                "data_referencia": candidato.data.isoformat(),
                "origem_url": candidato.carga["url"],
            },
        )


class ColetorDosRelatoriosDoBcb:
    """O Relatório de Inflação (trimestral) e o de Estabilidade Financeira (semestral)."""

    origem = "bcb_relatorios"
    espera_s = 1.0
    categoria = CategoriaDaAta.COMUNICADO_RELEVANTE
    PUBLICACOES = (("ri", "Relatório de Inflação"), ("ref", "Relatório de Estabilidade Financeira"))

    def listar(self, cliente: httpx.Client, desde: date, hoje: date) -> list[Candidato]:
        candidatos = []
        for slug, rotulo in self.PUBLICACOES:
            corpo = _json(
                _pegar(
                    cliente,
                    f"{_BASE_BCB}/api/servico/sitebcb/{slug}/ultimas",
                    params={"quantidade": 6, "filtro": ""},
                )
            )
            for registro in corpo.get("conteudo", []):
                dia = _data_iso(registro.get("DataReferencia"))
                url = registro.get("Url") or ""
                if dia is None or dia < desde or not url.lower().endswith(".pdf"):
                    continue
                periodo = (registro.get("LinkPagina") or "").rstrip("/").rsplit("/", 1)[-1]
                periodo = periodo if re.fullmatch(r"\d{6}", periodo) else dia.strftime("%Y%m")
                candidatos.append(
                    Candidato(
                        origem=self.origem,
                        identificador=f"bcb-{slug}-{periodo}",
                        titulo=_lapidar(f"{rotulo} · {_mes_e_ano(dia)}"),
                        data=dia,
                        carga={"url": _BASE_BCB + url},
                    )
                )
        return candidatos

    def baixar(self, cliente: httpx.Client, candidato: Candidato, destino: Path) -> None:
        resposta = _pegar(cliente, candidato.carga["url"])
        _gravar_pdf(
            destino,
            candidato.identificador,
            resposta.content,
            {
                "titulo": candidato.titulo,
                "data_referencia": candidato.data.isoformat(),
                "origem_url": candidato.carga["url"],
                "categoria": self.categoria.value,
                "origem": self.origem,
            },
        )


# ---------------------------------------------------------------------------
# BCB: Resoluções do CMN e do BCB
# ---------------------------------------------------------------------------


class _TextoDoHtml(HTMLParser):
    """Tira as marcas de um texto normativo e mantém um parágrafo por linha."""

    BLOCOS = {"p", "div", "br", "li", "tr", "h1", "h2", "h3", "h4", "table"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.partes: list[str] = []

    def handle_starttag(self, tag: str, atributos: Any) -> None:
        if tag in self.BLOCOS:
            self.partes.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in self.BLOCOS:
            self.partes.append("\n")

    def handle_data(self, dados: str) -> None:
        self.partes.append(dados)


def texto_do_html(bruto: str) -> str:
    leitor = _TextoDoHtml()
    leitor.feed(bruto)
    linhas = [re.sub(r"[ \t ​]+", " ", linha).strip() for linha in "".join(leitor.partes).split("\n")]
    return "\n".join(linha for linha in linhas if linha)


class ColetorDasResolucoes:
    origem = "bcb_resolucoes"
    espera_s = 1.0
    categoria = CategoriaDaAta.COMUNICADO_RELEVANTE
    URL_BUSCA = f"{_BASE_BCB}/api/search/app/normativos/buscanormativos"
    URL_TEXTO = f"{_BASE_BCB}/api/conteudo/app/normativos/exibeversao"
    LINHAS_POR_PAGINA = 100
    MAXIMO_DE_PAGINAS = 8

    def listar(self, cliente: httpx.Client, desde: date, hoje: date) -> list[Candidato]:
        candidatos: dict[str, Candidato] = {}
        for pagina in range(self.MAXIMO_DE_PAGINAS):
            corpo = _json(
                _pegar(
                    cliente,
                    self.URL_BUSCA,
                    params={
                        "querytext": "ContentType:normativo AND contentSource:normativos AND RevogadoOWSBOOL:0",
                        "rowlimit": self.LINHAS_POR_PAGINA,
                        "startrow": pagina * self.LINHAS_POR_PAGINA,
                        "sortlist": "Data1OWSDATE:descending",
                        "refinementfilters": "Data:range(datetime(min),datetime(max))",
                    },
                )
            )
            linhas = corpo.get("Rows") or []
            if not linhas:
                break
            for linha in linhas:
                dia = _data_iso(linha.get("data"))
                if dia is None or dia < desde:
                    continue
                especie = (linha.get("TipodoNormativoOWSCHCS") or "").strip()
                if not especie.startswith("Resolu"):
                    continue
                numero = int(float(linha.get("NumeroOWSNMBR") or 0))
                identificador = f"bcb-{_identificador(especie)}-{numero}"
                ementa = texto_do_html(linha.get("AssuntoNormativoOWSMTXT") or "")
                titulo = _lapidar(f"{html.unescape(linha.get('title', especie))} · {ementa}")
                candidatos[identificador] = Candidato(
                    origem=self.origem,
                    identificador=identificador,
                    titulo=titulo,
                    data=dia,
                    carga={
                        "item": str(linha.get("listItemId", "")),
                        "especie": especie,
                        "numero": str(numero),
                        "ementa": ementa,
                        "nome": html.unescape(linha.get("title", especie)),
                    },
                )
            datas = [d for d in (_data_iso(l.get("data")) for l in linhas) if d]
            if datas and min(datas) < desde:
                break
        return list(candidatos.values())

    def baixar(self, cliente: httpx.Client, candidato: Candidato, destino: Path) -> None:
        carga = candidato.carga
        corpo = _json(
            _pegar(cliente, self.URL_TEXTO, params={"p1": carga["item"], "p2": 1, "p3": "Vigente"})
        )
        versoes = corpo.get("conteudo") or []
        texto = texto_do_html(versoes[0].get("Texto") or "") if versoes else ""
        if not texto:
            raise ErroDeIngestao(f"{candidato.identificador}: o BCB não devolveu o texto")
        pagina = (
            f"{_BASE_BCB}/estabilidadefinanceira/exibenormativo"
            f"?tipo={quote(carga['especie'])}&numero={carga['numero']}"
        )
        cabecalho = f"{carga['nome']}\n\n{carga['ementa']}\n\n" if carga["ementa"] else f"{carga['nome']}\n\n"
        _gravar_texto(
            destino,
            candidato.identificador,
            cabecalho + texto,
            {
                "titulo": candidato.titulo,
                "data_referencia": candidato.data.isoformat(),
                "origem_url": pagina,
                "categoria": self.categoria.value,
                "origem": self.origem,
            },
        )


# ---------------------------------------------------------------------------
# CVM: Fatos Relevantes e DFP, ITR e Formulários (dados abertos, IPE)
# ---------------------------------------------------------------------------


def _eh_fato_relevante(linha: dict[str, str]) -> bool:
    return (linha.get("Categoria") or "").strip() == cvm_mod.CATEGORIA_NO_CSV


def _eh_demonstracao_ou_formulario(linha: dict[str, str]) -> bool:
    """DFP (demonstrações anuais), ITR (intermediárias) e os formulários cadastrais e de referência."""
    categoria = _sem_acento(linha.get("Categoria") or "")
    tipo = _sem_acento(linha.get("Tipo") or "")
    if categoria.startswith("formulario"):
        return True
    return categoria.startswith("dados economico") and (
        tipo.startswith("demonstracoes financeiras anuais")
        or tipo.startswith("demonstracoes financeiras intermediarias")
        or tipo.startswith("demonstracoes financeiras padronizadas")
    )


_ZIPS_DA_CVM: weakref.WeakKeyDictionary[httpx.Client, dict[int, bytes]] = weakref.WeakKeyDictionary()
"""O zip do IPE de cada ano, por cliente: as duas Origens da CVM leem o mesmo arquivo (1,7 MB) e a
consulta o baixa uma vez só. Some junto com o cliente."""


class ColetorDaCvm:
    espera_s = cvm_mod.ESPERA_ENTRE_REQUISICOES_S

    def __init__(
        self,
        origem: str,
        categoria: CategoriaDaAta,
        aceitar: Callable[[dict[str, str]], bool],
    ) -> None:
        self.origem = origem
        self.categoria = categoria
        self._aceitar = aceitar

    def _linhas(self, cliente: httpx.Client, desde: date, hoje: date) -> list[dict[str, str]]:
        linhas: list[dict[str, str]] = []
        for ano in sorted({hoje.year, desde.year}, reverse=True):
            guardados = _ZIPS_DA_CVM.setdefault(cliente, {})
            if ano not in guardados:
                try:
                    resposta = _pegar(cliente, cvm_mod.URL_DO_ZIP.format(ano=ano))
                except ErroDeIngestao as erro:
                    if "404" in str(erro):
                        continue
                    raise
                guardados[ano] = resposta.content
            try:
                linhas += cvm_mod._linhas_do_zip(guardados[ano], self._aceitar)
            except (zipfile.BadZipFile, UnicodeDecodeError) as erro:
                raise ErroDeIngestao(f"o zip de {ano} da CVM veio quebrado: {erro}") from erro
        return linhas

    def listar(self, cliente: httpx.Client, desde: date, hoje: date) -> list[Candidato]:
        candidatos = []
        for linha in self._linhas(cliente, desde, hoje):
            dia = cvm_mod._data_da_linha(linha, hoje)
            if dia < desde:
                continue
            empresa = (linha.get("Nome_Companhia") or "").strip() or "Companhia aberta"
            assunto = (
                (linha.get("Assunto") or "").strip()
                or (linha.get("Tipo") or "").strip()
                or (linha.get("Categoria") or "").strip()
            )
            candidatos.append(
                Candidato(
                    origem=self.origem,
                    identificador=f"cvm-{linha['Protocolo_Entrega'].strip()}",
                    titulo=_lapidar(f"{empresa} · {assunto}"),
                    data=dia,
                    carga={"url": linha["Link_Download"].strip()},
                )
            )
        return candidatos

    def baixar(self, cliente: httpx.Client, candidato: Candidato, destino: Path) -> None:
        resposta = _pegar(cliente, candidato.carga["url"])
        _gravar_pdf(
            destino,
            candidato.identificador,
            resposta.content,
            {
                "titulo": candidato.titulo,
                "data_referencia": candidato.data.isoformat(),
                "origem_url": candidato.carga["url"],
                "categoria": self.categoria.value,
                "origem": self.origem,
            },
        )


# ---------------------------------------------------------------------------
# B3: Ofícios circulares e comunicados externos
# ---------------------------------------------------------------------------

_BLOCO_DA_B3 = re.compile(r'<li class="accordion-navigation">(.*?)</li>\s*(?=<li class="accordion-navigation">|</ul>)', re.S)
_CAMPO_DA_B3 = {
    "data": re.compile(r'least-content">\s*(\d\d)/(\d\d)/(\d\d)\s*<'),
    "codigo": re.compile(r'class="primary-text">\s*(.*?)\s*</p>', re.S),
    "assunto": re.compile(r'class="secondary-text assunto-oficio">\s*(.*?)\s*</p>', re.S),
    "resumo": re.compile(r'class="resumo-oficio">\s*(.*?)\s*</p>', re.S),
    "link": re.compile(r'<a[^>]*href="([^"]+)"[^>]*>\s*Download do Documento', re.S),
}


def _data_da_b3(dia: str, mes: str, ano: str) -> date:
    return date(2000 + int(ano), int(mes), int(dia))


class ColetorDaB3:
    origem = "b3_oficios"
    espera_s = 1.0
    categoria = CategoriaDaAta.COMUNICADO_RELEVANTE
    MAXIMO_DE_PAGINAS = 10

    def listar(self, cliente: httpx.Client, desde: date, hoje: date) -> list[Candidato]:
        candidatos: dict[str, Candidato] = {}
        for pagina in range(1, self.MAXIMO_DE_PAGINAS + 1):
            resposta = _pegar(
                cliente,
                _URL_B3,
                params={
                    "pagination": pagina,
                    "dataIni": desde.strftime("%d/%m/%Y"),
                    "dataFim": hoje.strftime("%d/%m/%Y"),
                },
            )
            blocos = _BLOCO_DA_B3.findall(resposta.text)
            if not blocos:
                break
            novos = 0
            for bloco in blocos:
                achados = {nome: padrao.search(bloco) for nome, padrao in _CAMPO_DA_B3.items()}
                if not (achados["data"] and achados["codigo"] and achados["link"]):
                    continue
                dia = _data_da_b3(*achados["data"].groups())
                codigo = html.unescape(re.sub(r"\s+", " ", achados["codigo"].group(1))).strip()
                assunto = html.unescape(achados["assunto"].group(1)).strip() if achados["assunto"] else ""
                resumo = html.unescape(achados["resumo"].group(1)).strip() if achados["resumo"] else ""
                identificador = f"b3-{_identificador(codigo)}"
                if identificador in candidatos or dia < desde:
                    continue
                novos += 1
                candidatos[identificador] = Candidato(
                    origem=self.origem,
                    identificador=identificador,
                    titulo=_lapidar(f"{codigo} · {assunto}"),
                    data=dia,
                    carga={"url": urljoin(_URL_B3, achados["link"].group(1)), "resumo": resumo},
                )
            if novos == 0:
                break
        return list(candidatos.values())

    def baixar(self, cliente: httpx.Client, candidato: Candidato, destino: Path) -> None:
        url = quote(candidato.carga["url"], safe=":/%?=&")
        resposta = _pegar(cliente, url)
        _gravar_pdf(
            destino,
            candidato.identificador,
            resposta.content,
            {
                "titulo": candidato.titulo,
                "data_referencia": candidato.data.isoformat(),
                "origem_url": candidato.carga["url"],
                "categoria": self.categoria.value,
                "origem": self.origem,
            },
        )


def coletores_padrao() -> dict[str, Coletor]:
    """Um coletor por Origem que busca na rede. ``importados`` e ``releases_b3`` não têm."""
    coletores: list[Coletor] = [
        ColetorDoCopom(),
        ColetorDaCvm("cvm_fatos_relevantes", CategoriaDaAta.COMUNICADO_RELEVANTE, _eh_fato_relevante),
        ColetorDaCvm("cvm_demonstracoes", CategoriaDaAta.RELEASE, _eh_demonstracao_ou_formulario),
        ColetorDosRelatoriosDoBcb(),
        ColetorDasResolucoes(),
        ColetorDaB3(),
    ]
    return {coletor.origem: coletor for coletor in coletores}


__all__ = [
    "Candidato",
    "Coletor",
    "JANELA_DA_BUSCA_EM_DIAS",
    "cliente_padrao",
    "coletores_padrao",
]
