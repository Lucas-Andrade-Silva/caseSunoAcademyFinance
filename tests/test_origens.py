"""As Origens (o que a tela chama de Fontes): catálogo, repositório de Atas, resumo e a sugestão da
curadoria. Tudo determinístico, sem LLM, sem cota e sem rede.
"""

from __future__ import annotations

import json
import os
from datetime import date
from pathlib import Path

import pytest

from suno.dominio import CategoriaDaAta
from suno.origens.catalogo import (
    Origem,
    OrigemDesconhecida,
    OrigemIndisponivel,
    alternar,
    carregar_catalogo,
)
from suno.origens.curadoria import sugerir, sugerir_visao_unida
from suno.origens.repositorio import RepositorioDeAtas
from suno.origens.resumo import ResumoDaAta

RAIZ = Path(__file__).resolve().parent.parent
ATAS = RAIZ / "data" / "atas"
FONTES = RAIZ / "data" / "fontes"
ATA_DO_COPOM = "copom-280-2026-08-05"


def _comunicado(pasta: Path, identificador: str, texto: str, data: str = "2026-10-08") -> None:
    pasta.mkdir(parents=True, exist_ok=True)
    (pasta / f"{identificador}.txt").write_text(texto, encoding="utf-8")
    (pasta / f"{identificador}.json").write_text(
        json.dumps(
            {
                "titulo": f"Fato {identificador}",
                "data_referencia": data,
                "categoria": "comunicado_relevante",
                "origem": "cvm_fatos_relevantes",
            }
        ),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Catálogo
# ---------------------------------------------------------------------------


def test_o_catalogo_padrao_tem_as_quatro_origens(tmp_path: Path):
    origens = {o.id: o for o in carregar_catalogo(tmp_path)}

    assert list(origens) == ["copom", "cvm_fatos_relevantes", "cvm_demonstracoes", "bcb_relatorios", "bcb_resolucoes", "b3_oficios", "importados"]
    assert origens["copom"].ativa and origens["copom"].categoria is CategoriaDaAta.COPOM
    assert not origens["cvm_fatos_relevantes"].ativa
    assert origens["cvm_fatos_relevantes"].categoria is CategoriaDaAta.COMUNICADO_RELEVANTE
    assert origens["importados"].ativa
    assert origens["importados"].categoria is CategoriaDaAta.IMPORTADA


def test_o_catalogo_versionado_e_o_padrao(tmp_path: Path):
    # O estado da interface na máquina não pertence ao catálogo versionado.
    (tmp_path / "catalogo.json").write_bytes((FONTES / "catalogo.json").read_bytes())
    assert carregar_catalogo(tmp_path) == carregar_catalogo(tmp_path / "nao-existe")


def test_ligar_e_desligar_persiste_em_arquivo_de_preferencias(tmp_path: Path):
    ligada = alternar(tmp_path, "cvm_fatos_relevantes", True)

    assert ligada.ativa
    assert {o.id: o.ativa for o in carregar_catalogo(tmp_path)}["cvm_fatos_relevantes"]
    assert (tmp_path / "preferencias.json").exists()
    assert not (tmp_path / "catalogo.json").exists()  # o catálogo versionado não é tocado

    desligada = alternar(tmp_path, "cvm_fatos_relevantes", False)
    assert not desligada.ativa


def test_origem_desconhecida_e_recusada(tmp_path: Path):
    with pytest.raises(OrigemDesconhecida):
        alternar(tmp_path, "nao-existe", True)


def test_preferencia_ilegivel_cai_no_padrao(tmp_path: Path):
    (tmp_path / "preferencias.json").write_text("{ isto não é json", encoding="utf-8")

    origens = {o.id: o for o in carregar_catalogo(tmp_path)}

    assert origens["copom"].ativa


# ---------------------------------------------------------------------------
# Repositório e resumo
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("campo", "valor", "esperado"),
    [
        ("titulo", "Título corrigido da companhia", "Título corrigido da companhia"),
        ("data_referencia", "2026-10-17", date(2026, 10, 17)),
    ],
)
def test_cache_atualiza_ata_e_resumo_quando_metadados_mudam(
    tmp_path: Path, campo: str, valor: str, esperado: str | date
):
    pasta = tmp_path / "cvm_fatos_relevantes"
    _comunicado(pasta, "corrigida", "A companhia aprovou uma operação de R$ 2 bilhões.")
    repositorio = RepositorioDeAtas(tmp_path / "atas", tmp_path)
    antes = repositorio.carregar("corrigida")
    resumo_antes = repositorio.resumir("corrigida")
    assert antes is not None and resumo_antes is not None
    assert getattr(antes, campo) != esperado
    estado_do_texto = (pasta / "corrigida.txt").stat()
    metadados = pasta / "corrigida.json"
    estado = metadados.stat()
    dados = json.loads(metadados.read_text(encoding="utf-8"))
    dados[campo] = valor
    metadados.write_text(json.dumps(dados), encoding="utf-8")
    os.utime(metadados, ns=(estado.st_atime_ns, estado.st_mtime_ns + 1_000_000_000))

    depois = repositorio.carregar("corrigida")
    resumo_depois = repositorio.resumir("corrigida")

    assert depois is not None and resumo_depois is not None
    assert getattr(depois, campo) == esperado
    assert getattr(resumo_depois, campo) == esperado
    assert (pasta / "corrigida.txt").stat().st_mtime_ns == estado_do_texto.st_mtime_ns


def test_cache_do_arquivo_atualiza_quando_txt_auxiliar_muda(tmp_path: Path):
    pasta = tmp_path / "cvm_fatos_relevantes"
    _comunicado(pasta, "paginada", "A companhia aprovou uma operação de R$ 2 bilhões.")
    arquivo_original = pasta / "paginada.pdf"
    arquivo_original.write_bytes((ATAS / f"{ATA_DO_COPOM}.pdf").read_bytes())
    estado_do_original = arquivo_original.stat()
    repositorio = RepositorioDeAtas(tmp_path / "atas", tmp_path)
    antes = repositorio.carregar("paginada")
    resumo_antes = repositorio.resumir("paginada")
    assert antes is not None and resumo_antes is not None
    texto_corrigido = "A companhia anunciou uma operação de R$ 30 milhões e manteve a administração."
    (pasta / "paginada.txt").write_text(texto_corrigido, encoding="utf-8")

    depois = repositorio.carregar("paginada")
    resumo_depois = repositorio.resumir("paginada")

    assert depois is not None and resumo_depois is not None
    assert depois.texto == texto_corrigido != antes.texto
    assert resumo_depois.resumo == texto_corrigido != resumo_antes.resumo
    assert depois.arquivo == arquivo_original
    assert arquivo_original.stat().st_mtime_ns == estado_do_original.st_mtime_ns


def test_o_resumo_da_ata_do_copom_traz_a_frase_da_decisao():
    repositorio = RepositorioDeAtas(ATAS, FONTES)

    resumo = repositorio.resumir(ATA_DO_COPOM)

    assert resumo is not None
    assert resumo.titulo == "280ª Reunião - 4-5 agosto, 2026"
    assert resumo.data_referencia == date(2026, 8, 5)
    assert resumo.origem == "copom"
    assert resumo.categoria is CategoriaDaAta.COPOM
    assert resumo.calibrada
    assert resumo.demo_disponivel
    assert resumo.total_ancoras >= 10
    assert resumo.resumo.startswith("O Copom decidiu reduzir a taxa básica")
    assert len(resumo.resumo) <= 280


def test_a_ata_do_copom_tem_extracao_completa():
    resumo = RepositorioDeAtas(ATAS, FONTES).resumir(ATA_DO_COPOM)

    assert resumo is not None and resumo.extracao_completa


def test_comunicado_com_data_e_numero_tem_extracao_completa(tmp_path: Path):
    _comunicado(
        tmp_path / "cvm_fatos_relevantes",
        "com-numero",
        "Em 8 de outubro de 2026 a companhia aprovou uma operação de R$ 2 bilhões.",
    )

    resumo = RepositorioDeAtas(ATAS, tmp_path).resumir("com-numero")

    assert resumo is not None and resumo.extracao_completa


def test_comunicado_sem_numero_avisa_que_a_extracao_vai_falhar(tmp_path: Path):
    _comunicado(
        tmp_path / "cvm_fatos_relevantes",
        "sem-numero",
        "São Paulo, 8 de outubro de 2026. A companhia pediu o cancelamento do registro.",
    )

    resumo = RepositorioDeAtas(ATAS, tmp_path).resumir("sem-numero")

    assert resumo is not None and not resumo.extracao_completa


def test_comunicado_sem_data_no_texto_usa_a_data_dos_metadados(tmp_path: Path):
    _comunicado(
        tmp_path / "cvm_fatos_relevantes",
        "sem-data",
        "A companhia aprovou uma operação de R$ 2 bilhões.",
    )

    resumo = RepositorioDeAtas(ATAS, tmp_path).resumir("sem-data")

    assert resumo is not None and resumo.extracao_completa and not resumo.qualitativa


def test_comunicado_longo_sem_numero_gera_e_e_marcado_como_qualitativo(tmp_path: Path):
    corpo = (
        "A companhia comunicou ao mercado a saída de seu diretor-presidente e a escolha de um "
        "sucessor interno, que assume o cargo após a aprovação do conselho de administração. "
        "A mudança segue o plano de sucessão aprovado pelos acionistas e não altera a estratégia."
    )
    _comunicado(tmp_path / "cvm_fatos_relevantes", "so-texto", corpo)

    resumo = RepositorioDeAtas(ATAS, tmp_path).resumir("so-texto")

    assert resumo is not None and resumo.extracao_completa and resumo.qualitativa


def test_os_itens_de_uma_origem_vem_da_pasta_dela(tmp_path: Path):
    _comunicado(tmp_path / "cvm_fatos_relevantes", "fato-a", "Aprovou R$ 2 bilhões em 8 de outubro de 2026.")
    repositorio = RepositorioDeAtas(ATAS, tmp_path)
    origem = Origem(
        id="cvm_fatos_relevantes",
        nome="Fatos Relevantes da CVM",
        categoria=CategoriaDaAta.COMUNICADO_RELEVANTE,
    )

    itens = repositorio.itens_da_origem(origem)

    assert [i.identificador for i in itens] == ["fato-a"]
    assert itens[0].origem == "cvm_fatos_relevantes"
    assert not itens[0].calibrada
    assert not itens[0].demo_disponivel


def test_os_itens_saem_do_mais_recente_para_o_mais_antigo(tmp_path: Path):
    pasta = tmp_path / "cvm_fatos_relevantes"
    _comunicado(pasta, "antigo", "Texto com R$ 1 milhão.", data="2026-01-10")
    _comunicado(pasta, "novo", "Texto com R$ 1 milhão.", data="2026-10-08")
    _comunicado(pasta, "meio", "Texto com R$ 1 milhão.", data="2026-05-02")
    origem = Origem(
        id="cvm_fatos_relevantes",
        nome="Fatos Relevantes da CVM",
        categoria=CategoriaDaAta.COMUNICADO_RELEVANTE,
    )

    itens = RepositorioDeAtas(ATAS, tmp_path).itens_da_origem(origem)

    assert [i.identificador for i in itens] == ["novo", "meio", "antigo"]


def test_acha_o_arquivo_em_data_atas_e_em_data_fontes(tmp_path: Path):
    _comunicado(tmp_path / "cvm_fatos_relevantes", "fato-b", "Texto.")
    repositorio = RepositorioDeAtas(ATAS, tmp_path)

    assert repositorio.arquivo(ATA_DO_COPOM) == ATAS / f"{ATA_DO_COPOM}.pdf"
    assert repositorio.arquivo("fato-b") == tmp_path / "cvm_fatos_relevantes" / "fato-b.txt"
    assert repositorio.arquivo("nao-existe") is None


@pytest.mark.parametrize("identificador", ["../data/atas/copom-280-2026-08-05", "a/b", "..", ""])
def test_identificador_com_caminho_nunca_acha_arquivo(tmp_path: Path, identificador: str):
    assert RepositorioDeAtas(ATAS, tmp_path).arquivo(identificador) is None


def test_o_resumo_cai_nas_primeiras_frases_sem_verbo_de_decisao(tmp_path: Path):
    _comunicado(
        tmp_path / "cvm_fatos_relevantes",
        "sem-verbo",
        "Reunião do conselho em 8 de outubro de 2026.\nPauta: 3 itens.\n"
        "A diretoria discutiu a estrutura de capital da companhia e os prazos do plano de 2027.",
    )

    resumo = RepositorioDeAtas(ATAS, tmp_path).resumir("sem-verbo")

    assert resumo is not None
    assert resumo.resumo.startswith("A diretoria discutiu a estrutura de capital")


def test_o_resumo_de_texto_curto_e_o_proprio_texto(tmp_path: Path):
    _comunicado(tmp_path / "importados", "curtinho", "Nota curta.")

    resumo = RepositorioDeAtas(ATAS, tmp_path).resumir("curtinho")

    assert resumo is not None and resumo.resumo == "Nota curta."


def test_o_resumo_corta_em_280_caracteres_com_reticencias(tmp_path: Path):
    longo = "A companhia aprovou " + "uma operação muito detalhada " * 30 + "em 8 de outubro de 2026."
    _comunicado(tmp_path / "importados", "longo", longo)

    resumo = RepositorioDeAtas(ATAS, tmp_path).resumir("longo")

    assert resumo is not None
    assert len(resumo.resumo) <= 280
    assert resumo.resumo.endswith("…")


# ---------------------------------------------------------------------------
# A sugestão da curadoria
# ---------------------------------------------------------------------------


def _resumo(
    identificador: str,
    origem: str,
    data: date,
    ancoras: int,
    categoria=CategoriaDaAta.COPOM,
    extracao_completa: bool = True,
) -> ResumoDaAta:
    return ResumoDaAta(
        identificador=identificador,
        origem=origem,
        categoria=categoria,
        titulo=identificador,
        data_referencia=data,
        resumo="r",
        total_ancoras=ancoras,
        calibrada=categoria is CategoriaDaAta.COPOM,
        demo_disponivel=False,
        extracao_completa=extracao_completa,
    )


COPOM = Origem(id="copom", nome="Copom", categoria=CategoriaDaAta.COPOM, ativa=True)
CVM = Origem(
    id="cvm_fatos_relevantes",
    nome="CVM",
    categoria=CategoriaDaAta.COMUNICADO_RELEVANTE,
    ativa=True,
)
IMPORTADOS = Origem(
    id="importados", nome="Importados", categoria=CategoriaDaAta.IMPORTADA, ativa=True
)


def test_o_destaque_e_a_ata_mais_recente():
    itens = {
        "copom": [_resumo("copom-1", "copom", date(2026, 8, 5), 12)],
        "cvm_fatos_relevantes": [
            _resumo("fato-1", "cvm_fatos_relevantes", date(2026, 10, 8), 3, CategoriaDaAta.COMUNICADO_RELEVANTE)
        ],
    }

    sugestao = sugerir([COPOM, CVM], itens)

    assert sugestao is not None
    assert [i.identificador for i in sugestao.itens] == ["fato-1"]
    assert "mais recente" in sugestao.motivo


def test_na_mesma_data_ganha_quem_tem_mais_ancoras():
    itens = {
        "copom": [
            _resumo("a", "copom", date(2026, 8, 5), 4),
            _resumo("b", "copom", date(2026, 8, 5), 9),
        ]
    }

    sugestao = sugerir([COPOM], itens)

    assert sugestao is not None and sugestao.itens[0].identificador == "b"
    assert "mais Âncoras" in sugestao.motivo or "mais números" in sugestao.motivo


def test_no_empate_total_ganha_a_origem_de_maior_peso():
    data = date(2026, 8, 5)
    itens = {
        "importados": [_resumo("doc", "importados", data, 5, CategoriaDaAta.IMPORTADA)],
        "cvm_fatos_relevantes": [
            _resumo("fato", "cvm_fatos_relevantes", data, 5, CategoriaDaAta.COMUNICADO_RELEVANTE)
        ],
        "copom": [_resumo("ata", "copom", data, 5)],
    }

    sugestao = sugerir([IMPORTADOS, CVM, COPOM], itens)

    assert sugestao is not None and sugestao.itens[0].identificador == "ata"


def test_origem_desligada_nao_entra_na_sugestao():
    desligada = CVM.model_copy(update={"ativa": False})
    itens = {
        "copom": [_resumo("ata", "copom", date(2026, 8, 5), 12)],
        "cvm_fatos_relevantes": [
            _resumo("fato", "cvm_fatos_relevantes", date(2026, 10, 8), 9, CategoriaDaAta.COMUNICADO_RELEVANTE)
        ],
    }

    sugestao = sugerir([COPOM, desligada], itens)

    assert sugestao is not None and sugestao.itens[0].identificador == "ata"


def test_sem_itens_nao_ha_sugestao():
    assert sugerir([COPOM], {"copom": []}) is None
    assert sugerir([], {}) is None


def test_a_sugestao_de_fora_do_copom_avisa_que_nao_e_calibrada():
    itens = {
        "cvm_fatos_relevantes": [
            _resumo("fato", "cvm_fatos_relevantes", date(2026, 10, 8), 3, CategoriaDaAta.COMUNICADO_RELEVANTE)
        ]
    }

    sugestao = sugerir([CVM], itens)

    assert sugestao is not None
    assert "não calibrad" in sugestao.motivo


def test_quem_nao_consegue_gerar_perde_para_o_mais_antigo_que_consegue():
    itens = {
        "copom": [_resumo("ata", "copom", date(2026, 8, 5), 12)],
        "cvm_fatos_relevantes": [
            _resumo(
                "fato-sem-numero",
                "cvm_fatos_relevantes",
                date(2026, 10, 8),
                1,
                CategoriaDaAta.COMUNICADO_RELEVANTE,
                extracao_completa=False,
            )
        ],
    }

    sugestao = sugerir([COPOM, CVM], itens)

    assert sugestao is not None and sugestao.itens[0].identificador == "ata"


def test_se_ninguem_consegue_gerar_a_sugestao_avisa():
    itens = {
        "cvm_fatos_relevantes": [
            _resumo(
                "fato-sem-numero",
                "cvm_fatos_relevantes",
                date(2026, 10, 8),
                1,
                CategoriaDaAta.COMUNICADO_RELEVANTE,
                extracao_completa=False,
            )
        ]
    }

    sugestao = sugerir([CVM], itens)

    assert sugestao is not None
    assert "falha de extração" in sugestao.motivo


# ---------------------------------------------------------------------------
# A sugestão da Visão unida
# ---------------------------------------------------------------------------


def _quatro_atas() -> dict:
    return {
        "copom": [_resumo("ata", "copom", date(2026, 8, 5), 18)],
        "cvm_fatos_relevantes": [
            _resumo("fato-a", "cvm_fatos_relevantes", date(2026, 10, 8), 4, CategoriaDaAta.COMUNICADO_RELEVANTE),
            _resumo("fato-b", "cvm_fatos_relevantes", date(2026, 10, 7), 6, CategoriaDaAta.COMUNICADO_RELEVANTE),
            _resumo("fato-c", "cvm_fatos_relevantes", date(2026, 9, 1), 2, CategoriaDaAta.COMUNICADO_RELEVANTE),
        ],
    }


def test_a_visao_unida_junta_as_tres_atas_mais_bem_colocadas():
    sugestao = sugerir_visao_unida([COPOM, CVM], _quatro_atas())

    assert sugestao is not None
    assert [a.identificador for a in sugestao.itens] == ["fato-a", "fato-b", "fato-c"]
    assert "3 itens" in sugestao.motivo
    assert "Cada número cita" in sugestao.motivo


def test_a_visao_unida_exige_ao_menos_duas_atas():
    uma = {"copom": [_resumo("ata", "copom", date(2026, 8, 5), 18)]}

    assert sugerir_visao_unida([COPOM], uma) is None
    assert sugerir_visao_unida([COPOM], {"copom": []}) is None
    assert sugerir_visao_unida([], {}) is None


def test_a_visao_unida_ignora_quem_nao_consegue_gerar():
    itens = _quatro_atas()
    itens["cvm_fatos_relevantes"][0] = _resumo(
        "fato-a",
        "cvm_fatos_relevantes",
        date(2026, 10, 8),
        1,
        CategoriaDaAta.COMUNICADO_RELEVANTE,
        extracao_completa=False,
    )

    sugestao = sugerir_visao_unida([COPOM, CVM], itens)

    assert sugestao is not None
    assert "fato-a" not in [a.identificador for a in sugestao.itens]
    assert len(sugestao.itens) == 3


def test_a_visao_unida_avisa_quando_inclui_ata_nao_calibrada():
    sugestao = sugerir_visao_unida([COPOM, CVM], _quatro_atas())

    assert sugestao is not None
    assert "não calibrado" in sugestao.motivo


def test_a_visao_unida_so_do_copom_nao_avisa_calibracao():
    itens = {
        "copom": [
            _resumo("ata-1", "copom", date(2026, 8, 5), 18),
            _resumo("ata-2", "copom", date(2026, 6, 18), 16),
        ]
    }

    sugestao = sugerir_visao_unida([COPOM], itens)

    assert sugestao is not None
    assert "calibrado" not in sugestao.motivo
