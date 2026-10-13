"""Os coletores das Origens e o job "Atualizar fontes" em duas etapas (consultar, depois baixar).

Tudo offline: os coletores recebem um `httpx.Client` com `MockTransport`, e o atualizador recebe
coletores falsos. O que se trava: a janela de 30 dias, o corte de 2 documentos para pedir o
período, o teto por download e o que fica em disco.
"""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

import httpx
import pytest

from suno.dominio import CategoriaDaAta
from suno.ingestao.bcb import ErroDeIngestao
from suno.origens.atualizacao import (
    LIMITE_SEM_FILTRO,
    MAXIMO_POR_DOWNLOAD,
    Atualizador,
    PedidoDeDownloadRecusado,
)
from suno.origens.coleta import (
    Candidato,
    ColetorDaB3,
    ColetorDaCvm,
    ColetorDasResolucoes,
    ColetorDosRelatoriosDoBcb,
    _eh_demonstracao_ou_formulario,
    texto_do_html,
)

HOJE = date(2026, 10, 12)
DESDE = HOJE - timedelta(days=30)


def _cliente(responder) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(responder))


# ---------------------------------------------------------------------------
# B3: ofícios e comunicados
# ---------------------------------------------------------------------------


def _item_da_b3(dia: str, codigo: str, assunto: str, arquivo: str) -> str:
    return f"""
    <li class="accordion-navigation">
      <a href="#panel0a"><div class="content">
        <div class="least-content">{dia}</div>
        <p class="primary-text">{codigo}</p>
        <p class="secondary-text assunto-oficio">{assunto}</p></div></a>
      <div id="panel0a" class="content">
        <p class="resumo-oficio">Resumo de {codigo}.</p>
        <ul><li><a title="x" href="/data/files/{arquivo}">Download do Documento</a></li></ul>
      </div>
    </li>"""


def test_b3_lista_a_pagina_ate_acabar_e_filtra_pela_janela():
    paginas = {
        "1": _item_da_b3("09/10/26", "013-2026-VPE-Comunicado Externo", "Proventos de fundos", "a/x y.pdf")
        + _item_da_b3("08/10/26", "063-2026-VPC-Ofício Circular", "Tesouro Direto", "b/z.pdf"),
        "2": _item_da_b3("01/09/26", "999-2026-VPC-Ofício Circular", "Fora da janela", "c/w.pdf"),
    }

    def responder(pedido: httpx.Request) -> httpx.Response:
        assert pedido.url.params["dataIni"] == "12/09/2026"
        assert pedido.url.params["dataFim"] == "12/10/2026"
        corpo = f"<ul class='accordion list'>{paginas.get(pedido.url.params['pagination'], '')}</ul>"
        return httpx.Response(200, text=corpo)

    achados = ColetorDaB3().listar(_cliente(responder), DESDE, HOJE)

    assert [c.identificador for c in achados] == [
        "b3-013-2026-vpe-comunicado-externo",
        "b3-063-2026-vpc-oficio-circular",
    ]
    assert achados[0].data == date(2026, 10, 9)
    assert achados[0].titulo.startswith("013-2026-VPE-Comunicado Externo · Proventos")
    assert achados[0].carga["url"] == "https://www.b3.com.br/data/files/a/x y.pdf"


def test_b3_baixa_o_pdf_e_recusa_o_que_nao_e_pdf(tmp_path: Path):
    candidato = Candidato(
        "b3_oficios", "b3-1", "Titulo", HOJE, {"url": "https://www.b3.com.br/data/files/a/x y.pdf"}
    )
    pedidos: list[str] = []

    def responder(pedido: httpx.Request) -> httpx.Response:
        pedidos.append(str(pedido.url))
        return httpx.Response(200, content=b"<html>nao e pdf</html>")

    with pytest.raises(ErroDeIngestao, match="não é PDF"):
        ColetorDaB3().baixar(_cliente(responder), candidato, tmp_path)

    assert pedidos == ["https://www.b3.com.br/data/files/a/x%20y.pdf"]
    assert list(tmp_path.iterdir()) == []


# ---------------------------------------------------------------------------
# BCB: Relatórios e Resoluções
# ---------------------------------------------------------------------------


def test_relatorios_do_bcb_usam_as_duas_publicacoes_e_a_janela():
    def responder(pedido: httpx.Request) -> httpx.Response:
        slug = pedido.url.path.split("/")[-2]
        registros = {
            "ri": [{"DataReferencia": "2026-09-25T03:00:00Z", "Url": "/content/ri/ri202609p.pdf", "LinkPagina": "/publicacoes/ri/202609"}],
            "ref": [{"DataReferencia": "2026-05-31T03:00:00Z", "Url": "/content/ref/ref202605.pdf", "LinkPagina": "/publicacoes/ref/202605"}],
        }[slug]
        return httpx.Response(200, json={"conteudo": registros})

    achados = ColetorDosRelatoriosDoBcb().listar(_cliente(responder), DESDE, HOJE)

    assert [c.identificador for c in achados] == ["bcb-ri-202609"]
    assert achados[0].titulo == "Relatório de Inflação · set/2026"
    assert achados[0].carga["url"] == "https://www.bcb.gov.br/content/ri/ri202609p.pdf"


def _linha_normativo(especie: str, numero: int, dia: str, item: str = "1") -> dict:
    return {
        "title": f"{especie} N° {numero}",
        "TipodoNormativoOWSCHCS": especie,
        "NumeroOWSNMBR": f"{numero}.000000000000",
        "data": f"{dia}T12:00:00Z",
        "listItemId": item,
        "AssuntoNormativoOWSMTXT": "<div>Altera a <b>Resolução</b> anterior.</div>",
    }


def test_resolucoes_ignoram_comunicados_e_param_ao_passar_da_janela():
    paginas = {
        "0": [
            _linha_normativo("Comunicado", 46105, "2026-10-09"),
            _linha_normativo("Resolução BCB", 599, "2026-10-08", "53026"),
            _linha_normativo("Resolução CMN", 5300, "2026-10-01", "53000"),
        ],
        "100": [_linha_normativo("Resolução BCB", 100, "2026-08-01")],
    }

    def responder(pedido: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"Rows": paginas.get(pedido.url.params["startrow"], [])})

    achados = ColetorDasResolucoes().listar(_cliente(responder), DESDE, HOJE)

    assert [c.identificador for c in achados] == ["bcb-resolucao-bcb-599", "bcb-resolucao-cmn-5300"]
    assert achados[0].titulo == "Resolução BCB N° 599 · Altera a Resolução anterior."
    assert achados[0].carga["item"] == "53026"


def test_resolucao_baixada_vira_texto_com_metadados(tmp_path: Path):
    candidato = Candidato(
        "bcb_resolucoes",
        "bcb-resolucao-bcb-599",
        "Resolução BCB N° 599 · Ementa",
        date(2026, 10, 8),
        {"item": "53026", "especie": "Resolução BCB", "numero": "599", "ementa": "Ementa.", "nome": "Resolução BCB N° 599"},
    )

    def responder(pedido: httpx.Request) -> httpx.Response:
        assert pedido.url.params["p1"] == "53026"
        return httpx.Response(
            200, json={"conteudo": [{"Texto": "<p>Art. 1º Fica alterado o prazo para 30 dias.</p><p>Art. 2º Vigência.</p>"}]}
        )

    ColetorDasResolucoes().baixar(_cliente(responder), candidato, tmp_path)

    texto = (tmp_path / "bcb-resolucao-bcb-599.txt").read_text(encoding="utf-8")
    assert texto.startswith("Resolução BCB N° 599\n\nEmenta.\n\nArt. 1º")
    meta = json.loads((tmp_path / "bcb-resolucao-bcb-599.json").read_text(encoding="utf-8"))
    assert meta["data_referencia"] == "2026-10-08"
    assert meta["origem"] == "bcb_resolucoes"
    assert meta["categoria"] == CategoriaDaAta.COMUNICADO_RELEVANTE.value


def test_resolucao_sem_texto_do_bcb_falha_sem_deixar_arquivo(tmp_path: Path):
    candidato = Candidato(
        "bcb_resolucoes", "x", "t", HOJE,
        {"item": "1", "especie": "Resolução BCB", "numero": "1", "ementa": "", "nome": "n"},
    )
    cliente = _cliente(lambda pedido: httpx.Response(200, json={"conteudo": []}))

    with pytest.raises(ErroDeIngestao, match="não devolveu o texto"):
        ColetorDasResolucoes().baixar(cliente, candidato, tmp_path)

    assert list(tmp_path.iterdir()) == []


def test_texto_do_html_separa_paragrafos_e_tira_espacos_estranhos():
    assert texto_do_html("<div><p>Um  dois</p><p>Três<br>quatro</p></div>") == "Um dois\nTrês\nquatro"


# ---------------------------------------------------------------------------
# CVM: DFP, ITR e Formulários
# ---------------------------------------------------------------------------


def test_cvm_demonstracoes_aceita_dfp_itr_e_formularios_e_so_eles():
    def linha(categoria: str, tipo: str = "") -> dict[str, str]:
        return {"Categoria": categoria, "Tipo": tipo}

    assert _eh_demonstracao_ou_formulario(linha("Dados Econômico-Financeiros", "Demonstrações Financeiras Anuais Completas"))
    assert _eh_demonstracao_ou_formulario(linha("Dados Econômico-Financeiros", "Demonstrações Financeiras Intermediárias"))
    assert _eh_demonstracao_ou_formulario(linha("Formulário de Informações Trimestrais - ITR"))
    assert _eh_demonstracao_ou_formulario(linha("Formulário de Referência"))
    assert not _eh_demonstracao_ou_formulario(linha("Dados Econômico-Financeiros", "Laudo de Avaliação"))
    assert not _eh_demonstracao_ou_formulario(linha("Fato Relevante"))


def test_cvm_coletor_usa_o_zip_do_ano_e_respeita_a_janela():
    import io
    import zipfile

    cabecalho = (
        "CNPJ_Companhia;Nome_Companhia;Codigo_CVM;Data_Referencia;Categoria;Tipo;Especie;Assunto;"
        "Data_Entrega;Tipo_Apresentacao;Protocolo_Entrega;Versao;Link_Download"
    )
    linhas = [
        "0;Cia A;1;2026-06-30;Dados Econômico-Financeiros;Demonstrações Financeiras Intermediárias;;;2026-10-08;AP;P1;1;https://rad/1",
        "0;Cia B;2;2026-06-30;Dados Econômico-Financeiros;Demonstrações Financeiras Intermediárias;;;2026-08-01;AP;P2;1;https://rad/2",
        "0;Cia C;3;2026-06-30;Fato Relevante;;;Algo;2026-10-09;AP;P3;1;https://rad/3",
    ]
    memoria = io.BytesIO()
    with zipfile.ZipFile(memoria, "w") as arquivo:
        arquivo.writestr("ipe_cia_aberta_2026.csv", "\n".join([cabecalho, *linhas]).encode("latin-1"))
    pedidos: list[str] = []

    def responder(pedido: httpx.Request) -> httpx.Response:
        pedidos.append(str(pedido.url))
        return httpx.Response(200, content=memoria.getvalue())

    coletor = ColetorDaCvm("cvm_demonstracoes", CategoriaDaAta.RELEASE, _eh_demonstracao_ou_formulario)
    achados = coletor.listar(_cliente(responder), DESDE, HOJE)

    assert [c.identificador for c in achados] == ["cvm-P1"]
    assert achados[0].titulo == "Cia A · Demonstrações Financeiras Intermediárias"
    assert len(pedidos) == 1


# ---------------------------------------------------------------------------
# O atualizador em duas etapas
# ---------------------------------------------------------------------------


class ColetorFalso:
    espera_s = 0.0

    def __init__(self, origem: str, datas: list[date], falha: str | None = None) -> None:
        self.origem = origem
        self._datas = datas
        self._falha = falha
        self.baixados: list[str] = []

    def listar(self, cliente, desde, hoje):
        if self._falha:
            raise ErroDeIngestao(self._falha)
        return [
            Candidato(self.origem, f"{self.origem}-{i}", f"Documento {i}", dia)
            for i, dia in enumerate(self._datas)
        ]

    def baixar(self, cliente, candidato, destino: Path) -> None:
        destino.mkdir(parents=True, exist_ok=True)
        (destino / f"{candidato.identificador}.txt").write_text("texto", encoding="utf-8")
        self.baixados.append(candidato.identificador)


class ClienteFalso:
    def close(self) -> None:  # pragma: no cover - nada a fechar
        pass


def _atualizador(tmp_path: Path, coletores: list[ColetorFalso], ligadas: list[str] | None = None) -> Atualizador:
    pasta = tmp_path / "fontes"
    pasta.mkdir(exist_ok=True)
    ativas = {c.origem: True for c in coletores} if ligadas is None else {o: True for o in ligadas}
    (pasta / "preferencias.json").write_text(json.dumps({"ativas": ativas}), encoding="utf-8")
    return Atualizador(
        tmp_path / "atas",
        pasta,
        coletores={c.origem: c for c in coletores},
        fabrica_de_cliente=ClienteFalso,
        dormir=lambda segundos: None,
        hoje=lambda: HOJE,
    )


def test_ate_dois_documentos_baixa_sem_perguntar(tmp_path: Path):
    coletor = ColetorFalso("b3_oficios", [HOJE, HOJE - timedelta(days=3)])
    atualizador = _atualizador(tmp_path, [coletor])

    atualizador.iniciar()
    assert atualizador.aguardar(10)

    estado = atualizador.estado()
    assert LIMITE_SEM_FILTRO == 2
    assert estado.estado == "ok"
    assert estado.novos == 2
    assert (tmp_path / "fontes" / "b3_oficios" / "b3_oficios-0.txt").exists()
    assert "Ofícios e comunicados da B3: 2 novos" in estado.mensagem


def test_mais_de_dois_documentos_esperam_o_periodo_e_nada_e_baixado(tmp_path: Path):
    datas = [HOJE - timedelta(days=d) for d in (1, 5, 10, 20)]
    coletor = ColetorFalso("b3_oficios", datas)
    atualizador = _atualizador(tmp_path, [coletor])

    atualizador.iniciar()
    assert atualizador.aguardar(10)

    estado = atualizador.estado()
    assert estado.estado == "aguardando_filtro"
    assert estado.desde == DESDE and estado.ate == HOJE
    assert [d.data for d in estado.disponiveis] == datas
    assert coletor.baixados == []


def test_baixar_so_o_periodo_escolhido(tmp_path: Path):
    datas = [HOJE - timedelta(days=d) for d in (1, 5, 10, 20)]
    coletor = ColetorFalso("b3_oficios", datas)
    atualizador = _atualizador(tmp_path, [coletor])
    atualizador.iniciar()
    assert atualizador.aguardar(10)

    atualizador.baixar(HOJE - timedelta(days=10), HOJE - timedelta(days=1))
    assert atualizador.aguardar(10)

    estado = atualizador.estado()
    assert estado.estado == "ok"
    assert estado.novos == 3
    assert sorted(coletor.baixados) == ["b3_oficios-0", "b3_oficios-1", "b3_oficios-2"]


def test_periodo_vazio_ou_invertido_ou_sem_consulta_e_recusado(tmp_path: Path):
    atualizador = _atualizador(tmp_path, [ColetorFalso("b3_oficios", [HOJE - timedelta(days=d) for d in (1, 2, 3)])])

    with pytest.raises(PedidoDeDownloadRecusado, match="não há consulta"):
        atualizador.baixar(DESDE, HOJE)

    atualizador.iniciar()
    assert atualizador.aguardar(10)
    with pytest.raises(PedidoDeDownloadRecusado, match="vem depois"):
        atualizador.baixar(HOJE, DESDE)
    with pytest.raises(PedidoDeDownloadRecusado, match="nenhum documento"):
        atualizador.baixar(HOJE - timedelta(days=29), HOJE - timedelta(days=28))
    assert atualizador.estado().estado == "aguardando_filtro"


def test_ha_um_teto_de_documentos_por_download(tmp_path: Path):
    coletor = ColetorFalso("b3_oficios", [HOJE] * (MAXIMO_POR_DOWNLOAD + 1))
    atualizador = _atualizador(tmp_path, [coletor])
    atualizador.iniciar()
    assert atualizador.aguardar(10)

    with pytest.raises(PedidoDeDownloadRecusado, match="no máximo"):
        atualizador.baixar(DESDE, HOJE)


def test_cancelar_descarta_a_consulta(tmp_path: Path):
    atualizador = _atualizador(tmp_path, [ColetorFalso("b3_oficios", [HOJE] * 3)])
    atualizador.iniciar()
    assert atualizador.aguardar(10)

    assert atualizador.cancelar().estado == "ocioso"
    with pytest.raises(PedidoDeDownloadRecusado):
        atualizador.baixar(DESDE, HOJE)


def test_o_que_ja_esta_em_disco_nao_conta_de_novo(tmp_path: Path):
    coletor = ColetorFalso("b3_oficios", [HOJE, HOJE - timedelta(days=1), HOJE - timedelta(days=2)])
    atualizador = _atualizador(tmp_path, [coletor])
    pasta = tmp_path / "fontes" / "b3_oficios"
    pasta.mkdir(parents=True)
    (pasta / "b3_oficios-0.txt").write_text("já está", encoding="utf-8")
    (pasta / "b3_oficios-1.pdf").write_bytes(b"%PDF-1.4")

    atualizador.iniciar()
    assert atualizador.aguardar(10)

    assert atualizador.estado().estado == "ok"
    assert coletor.baixados == ["b3_oficios-2"]


def test_origem_desligada_nao_e_consultada(tmp_path: Path):
    ligada = ColetorFalso("b3_oficios", [HOJE])
    desligada = ColetorFalso("bcb_resolucoes", [HOJE])
    atualizador = _atualizador(tmp_path, [ligada, desligada], ligadas=["b3_oficios"])
    (tmp_path / "fontes" / "preferencias.json").write_text(
        json.dumps({"ativas": {"b3_oficios": True, "bcb_resolucoes": False}}), encoding="utf-8"
    )

    atualizador.iniciar()
    assert atualizador.aguardar(10)

    assert ligada.baixados == ["b3_oficios-0"]
    assert desligada.baixados == []


def test_uma_origem_que_falha_nao_impede_a_outra(tmp_path: Path):
    quebrada = ColetorFalso("bcb_resolucoes", [], falha="BCB fora do ar")
    boa = ColetorFalso("b3_oficios", [HOJE])
    atualizador = _atualizador(tmp_path, [quebrada, boa])

    atualizador.iniciar()
    assert atualizador.aguardar(10)

    estado = atualizador.estado()
    assert estado.estado == "erro"
    assert estado.novos == 1
    assert "BCB fora do ar" in estado.mensagem


def test_nada_novo_fecha_ok_com_a_frase(tmp_path: Path):
    atualizador = _atualizador(tmp_path, [ColetorFalso("b3_oficios", [])])

    atualizador.iniciar()
    assert atualizador.aguardar(10)

    estado = atualizador.estado()
    assert estado.estado == "ok"
    assert estado.novos == 0
    assert "Nada novo" in estado.mensagem


def test_antes_de_atualizar_o_estado_e_ocioso(tmp_path: Path):
    assert _atualizador(tmp_path, []).estado().estado == "ocioso"


def test_um_tempo_esgotado_ganha_uma_segunda_tentativa():
    chamadas: list[int] = []

    def responder(pedido: httpx.Request) -> httpx.Response:
        chamadas.append(1)
        if len(chamadas) == 1:
            raise httpx.ReadTimeout("devagar", request=pedido)
        return httpx.Response(200, text="<ul class='accordion list'></ul>")

    assert ColetorDaB3().listar(_cliente(responder), DESDE, HOJE) == []
    assert len(chamadas) == 2


def test_dois_tempos_esgotados_viram_erro_de_ingestao():
    def responder(pedido: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("devagar", request=pedido)

    with pytest.raises(ErroDeIngestao, match="www.b3.com.br"):
        ColetorDaB3().listar(_cliente(responder), DESDE, HOJE)
