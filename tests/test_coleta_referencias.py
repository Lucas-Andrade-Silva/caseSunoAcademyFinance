"""A coleta publica e opcional, idempotente e nunca aprova referencias."""

from datetime import datetime, timezone
from pathlib import Path

from fastapi.testclient import TestClient

from suno.api.app import criar_app
from suno.pacote.coleta_referencias import (
    CandidatoDeReferencia,
    ColetaIndisponivel,
    RepositorioDaColeta,
    classificar_setor,
)


class ColetorFalso:
    def __init__(self, *, falhar: bool = False) -> None:
        self.falhar = falhar
        self.chamadas: list[str] = []

    def coletar(self, usuario: str, desde: datetime) -> list[CandidatoDeReferencia]:
        self.chamadas.append(usuario)
        if self.falhar:
            raise ColetaIndisponivel("consulta publica indisponivel")
        curtidas = 180 if usuario == "perfil.b" else 80
        return [
            CandidatoDeReferencia(
                identificador=f"instagram-{usuario}-abc",
                usuario=usuario,
                titulo="Cinco leituras sobre juros",
                legenda="Uma leitura visual do cenario de juros e renda fixa.",
                url=f"https://www.instagram.com/p/{usuario}-abc/",
                publicado_em=datetime(2026, 10, 1, tzinfo=timezone.utc),
                curtidas=curtidas,
                comentarios=20,
                seguidores=1000,
                taxa_engajamento=(curtidas + 20) / 10,
            )
        ]


def test_classificacao_de_setor_ignora_acentos() -> None:
    assert classificar_setor("Ações, inflação e investimentos").value == "investimentos"


def test_coleta_guarda_metadados_sem_duplicar_e_sem_imagem(tmp_path: Path) -> None:
    repositorio = RepositorioDaColeta(tmp_path / "suno.sqlite3")
    repositorio.adicionar_perfil("@Perfil.Financeiro")
    coletor = ColetorFalso()

    primeira = repositorio.coletar(
        coletor, janela_dias=30, agora=datetime(2026, 10, 10, tzinfo=timezone.utc)
    )
    segunda = repositorio.coletar(
        coletor, janela_dias=30, agora=datetime(2026, 10, 10, tzinfo=timezone.utc)
    )

    assert primeira.candidatos_novos == 1
    assert segunda.candidatos_novos == 0
    assert len(repositorio.listar_candidatos()) == 1
    assert repositorio.listar_candidatos()[0].importado is False
    assert repositorio.listar_perfis()[0].ultimo_estado == "concluida"


def test_falha_de_um_perfil_fica_registrada_sem_interromper_a_biblioteca(
    tmp_path: Path,
) -> None:
    repositorio = RepositorioDaColeta(tmp_path / "suno.sqlite3")
    repositorio.adicionar_perfil("mercado.publico")

    resultado = repositorio.coletar(ColetorFalso(falhar=True), janela_dias=60)

    assert resultado.candidatos_novos == 0
    assert resultado.falhas == [
        "@mercado.publico: consulta publica indisponivel"
    ]
    assert repositorio.listar_perfis()[0].ultimo_estado == "erro"


def test_api_coleta_e_importa_candidato_para_curadoria_nao_aprovada(
    tmp_path: Path,
) -> None:
    cliente = TestClient(
        criar_app(
            tmp_path / "execucoes",
            pasta_atas=tmp_path / "atas",
            pasta_fontes=tmp_path / "fontes",
            coletor_referencias=ColetorFalso(),
            recuperar_ao_iniciar=False,
        )
    )
    perfil = cliente.post(
        "/api/referencias-visuais/coleta/perfis", json={"usuario": "financas.abertas"}
    )
    assert perfil.status_code == 201

    coleta = cliente.post(
        "/api/referencias-visuais/coleta/executar", json={"janela_dias": 30}
    )
    assert coleta.status_code == 200
    assert coleta.json()["candidatos_novos"] == 1
    candidato = cliente.get(
        "/api/referencias-visuais/coleta/candidatos"
    ).json()[0]
    assert candidato["taxa_engajamento"] == 10

    importada = cliente.post(
        f"/api/referencias-visuais/coleta/candidatos/{candidato['identificador']}/importar",
        json={"composicao": "editorial"},
    )

    assert importada.status_code == 201
    assert importada.json()["aprovada"] is False
    assert importada.json()["origem"] == candidato["url"]
    assert cliente.get("/api/referencias-visuais/coleta/candidatos").json()[0][
        "importado"
    ] is True


def test_api_recusa_janela_fora_do_catalogo(tmp_path: Path) -> None:
    cliente = TestClient(
        criar_app(
            tmp_path / "execucoes",
            pasta_atas=tmp_path / "atas",
            pasta_fontes=tmp_path / "fontes",
            coletor_referencias=ColetorFalso(),
            recuperar_ao_iniciar=False,
        )
    )

    resposta = cliente.post(
        "/api/referencias-visuais/coleta/executar", json={"janela_dias": 7}
    )

    assert resposta.status_code == 422


def test_descoberta_filtra_setor_e_ranqueia_perfis_por_movimentacao(tmp_path: Path) -> None:
    repositorio = RepositorioDaColeta(tmp_path / "suno.sqlite3")
    for usuario in ("perfil.a", "perfil.b"):
        repositorio.adicionar_perfil(usuario)
    coletor = ColetorFalso()
    repositorio.coletar(
        coletor, janela_dias=30, agora=datetime(2026, 10, 10, tzinfo=timezone.utc)
    )

    descoberta = repositorio.descobrir(
        janela_dias=30,
        setor="investimentos",
        agora=datetime(2026, 10, 10, tzinfo=timezone.utc),
    )

    assert [item.usuario for item in descoberta.perfis] == ["perfil.b", "perfil.a"]
    assert all(item.setor.value == "investimentos" for item in descoberta.candidatos)
    assert descoberta.perfis[0].movimentacao == 200
