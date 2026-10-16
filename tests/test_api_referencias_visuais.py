"""A API expõe a biblioteca SQLite usada pela direção de arte."""

from io import BytesIO
from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image

from suno.api.app import criar_app
from suno.dominio import ComposicaoCarrossel, PapelLLM
from suno.pacote.referencias_visuais import REFERENCIAS_INICIAIS
from suno.provedores.falso import ProvedorFalso


def test_api_lista_as_referencias_iniciais(tmp_path: Path) -> None:
    pasta_execucoes = tmp_path / "execucoes"
    cliente = TestClient(
        criar_app(
            pasta_execucoes,
            pasta_atas=tmp_path / "atas",
            pasta_fontes=tmp_path / "fontes",
            recuperar_ao_iniciar=False,
        )
    )

    resposta = cliente.get("/api/referencias-visuais")

    assert resposta.status_code == 200
    referencias = resposta.json()
    assert len(referencias) == len(REFERENCIAS_INICIAIS)
    assert {item["composicao"] for item in referencias} == {
        composicao.value for composicao in ComposicaoCarrossel
    }
    assert all(item["aprovada"] for item in referencias)
    assert (pasta_execucoes / "suno.sqlite3").is_file()


def test_api_importa_e_aprova_uma_referencia_manual(tmp_path: Path) -> None:
    cliente = TestClient(
        criar_app(
            tmp_path / "execucoes",
            pasta_atas=tmp_path / "atas",
            pasta_fontes=tmp_path / "fontes",
            recuperar_ao_iniciar=False,
        )
    )

    resposta = cliente.post(
        "/api/referencias-visuais",
        json={
            "titulo": "Crédito privado lado a lado",
            "tema": "renda fixa",
            "composicao": "comparativo",
            "descricao": "Uma comparação autorizada de risco, liquidez e prazo.",
            "instrucao_de_design": "Use critérios equivalentes e mantenha a leitura neutra.",
            "origem": "https://exemplo.test/referencia-autorizada",
        },
    )

    assert resposta.status_code == 201
    importada = resposta.json()
    assert importada["aprovada"] is False
    aprovada = cliente.patch(
        f"/api/referencias-visuais/{importada['identificador']}",
        json={"aprovada": True},
    )
    assert aprovada.status_code == 200
    assert aprovada.json()["aprovada"] is True


def _png() -> bytes:
    memoria = BytesIO()
    Image.new("RGB", (320, 400), "#252525").save(memoria, format="PNG")
    return memoria.getvalue()


def test_upload_analisa_imagem_com_provedor_multimodal_e_exige_nova_aprovacao(
    tmp_path: Path,
) -> None:
    provedor = ProvedorFalso(
        {
            "analise_visual:suno-editorial-cenario-de-juros": [
                {
                    "posicao_do_titulo": "superior_esquerda",
                    "proeminencia_do_titulo": "alta",
                    "densidade_textual": "baixa",
                    "uso_de_imagem": "grafico_lateral",
                    "tipo_de_fundo": "escuro_solido",
                    "elementos_visuais": ["linha_de_mercado"],
                    "estrutura_do_conteudo": ["titulo", "grafico", "apoio"],
                }
            ]
        }
    )
    cliente = TestClient(
        criar_app(
            tmp_path / "execucoes",
            pasta_atas=tmp_path / "atas",
            pasta_fontes=tmp_path / "fontes",
            provedor_visao=provedor,
            recuperar_ao_iniciar=False,
        )
    )

    resposta = cliente.post(
        "/api/referencias-visuais/suno-editorial-cenario-de-juros/imagem",
        content=_png(),
        headers={"content-type": "image/png"},
    )

    assert resposta.status_code == 200
    referencia = resposta.json()
    assert referencia["imagem_disponivel"] is True
    assert referencia["estado_analise"] == "concluida"
    assert referencia["provedor_analise"] == "falso"
    assert referencia["aprovada"] is False
    assert referencia["analise"]["uso_de_imagem"] == "grafico_lateral"
    assert provedor.pedidos[0].papel is PapelLLM.ANALISTA_VISUAL
    assert provedor.pedidos[0].mensagens[-1].imagem_png.startswith(b"\x89PNG")
    imagem = cliente.get(
        "/api/referencias-visuais/suno-editorial-cenario-de-juros/imagem"
    )
    assert imagem.status_code == 200
    assert imagem.headers["content-type"] == "image/png"


def test_upload_continua_disponivel_para_revisao_quando_gemini_nao_esta_configurado(
    tmp_path: Path,
) -> None:
    cliente = TestClient(
        criar_app(
            tmp_path / "execucoes",
            pasta_atas=tmp_path / "atas",
            pasta_fontes=tmp_path / "fontes",
            recuperar_ao_iniciar=False,
        )
    )

    resposta = cliente.post(
        "/api/referencias-visuais/suno-minimalista-reserva-de-emergencia/imagem",
        content=_png(),
        headers={"content-type": "image/png"},
    )

    assert resposta.status_code == 200
    assert resposta.json()["estado_analise"] == "erro"
    assert resposta.json()["imagem_disponivel"] is True
    assert resposta.json()["mensagem_analise"]


def test_upload_recusa_arquivo_que_nao_e_imagem(tmp_path: Path) -> None:
    cliente = TestClient(
        criar_app(
            tmp_path / "execucoes",
            pasta_atas=tmp_path / "atas",
            pasta_fontes=tmp_path / "fontes",
            recuperar_ao_iniciar=False,
        )
    )

    resposta = cliente.post(
        "/api/referencias-visuais/suno-editorial-cenario-de-juros/imagem",
        content=b"nao e imagem",
        headers={"content-type": "application/octet-stream"},
    )

    assert resposta.status_code == 422


def test_referencia_de_familia_serve_a_miniatura_do_layout_sem_imagem_enviada(tmp_path: Path) -> None:
    cliente = TestClient(
        criar_app(
            tmp_path / "execucoes",
            pasta_atas=tmp_path / "atas",
            pasta_fontes=tmp_path / "fontes",
            recuperar_ao_iniciar=False,
        )
    )
    referencias = cliente.get("/api/referencias-visuais").json()
    com_miniatura = [r for r in referencias if r["imagem_disponivel"]]
    assert com_miniatura, "as referências das famílias trazem miniatura"

    for referencia in com_miniatura:
        resposta = cliente.get(f"/api/referencias-visuais/{referencia['identificador']}/imagem")
        assert resposta.status_code == 200, referencia["identificador"]
        assert resposta.headers["content-type"] == "image/png"
        assert resposta.content.startswith(b"\x89PNG")


def test_api_diz_os_papeis_que_cada_familia_cobre(tmp_path: Path) -> None:
    """A guia usa isto para não oferecer uma família que não monta o carrossel (a Asset)."""
    cliente = TestClient(
        criar_app(
            tmp_path / "execucoes",
            pasta_atas=tmp_path / "atas",
            pasta_fontes=tmp_path / "fontes",
            recuperar_ao_iniciar=False,
        )
    )

    resposta = cliente.get("/api/familias-visuais")

    assert resposta.status_code == 200
    papeis = {item["familia"]: set(item["papeis"]) for item in resposta.json()}
    assert papeis["asset"] == {"hook", "cta"}
    assert papeis["dados"] == {"hook", "ponto", "citacao", "cta"}
    assert "suno_escuro" not in papeis
