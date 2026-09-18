"""A trava de rede e a ausência de ``.env``: valem para a suíte inteira (ADR 0001).

Qualquer teste que tente abrir um socket para fora quebra com ``RedeBloqueada``. O único
teste autorizado a "tentar" é ``tests/test_trava_rede.py``, que prova que a trava existe.
"""

from __future__ import annotations

import os
import socket
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
DADOS = RAIZ / "data"
ATAS = DADOS / "atas"

CHAVES_DE_PROVEDOR = (
    "GEMINI_API_KEY",
    "GROQ_API_KEY",
    "SAMBANOVA_API_KEY",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
)


class RedeBloqueada(RuntimeError):
    """Um teste tentou acessar a rede."""


LOOPBACK = frozenset({"127.0.0.1", "::1", "localhost"})
"""O loopback fica livre: no Windows, criar um laço asyncio usa ``socket.socketpair()``, que
conecta em 127.0.0.1 (o ``pydantic-evals`` precisa disso). Nada fora da máquina passa."""


def _destino(endereco: object) -> str | None:
    if isinstance(endereco, tuple) and endereco and isinstance(endereco[0], str):
        return endereco[0]
    return None


def _recusar() -> None:
    raise RedeBloqueada("acesso à rede é proibido nos testes (ADR 0001): a suíte roda offline")


def _fazer_trava(original, posicao_do_endereco: int):
    def travado(*args, **kwargs):
        endereco = args[posicao_do_endereco] if len(args) > posicao_do_endereco else kwargs.get("address")
        if _destino(endereco) in LOOPBACK:
            return original(*args, **kwargs)
        _recusar()

    return travado


def _getaddrinfo_travado(original):
    def travado(host, *args, **kwargs):
        if host in LOOPBACK or host is None:
            return original(host, *args, **kwargs)
        _recusar()

    return travado


@pytest.fixture(autouse=True, scope="session")
def trava_de_rede():
    originais = {
        "connect": socket.socket.connect,
        "connect_ex": socket.socket.connect_ex,
        "create_connection": socket.create_connection,
        "getaddrinfo": socket.getaddrinfo,
    }
    socket.socket.connect = _fazer_trava(originais["connect"], 1)  # type: ignore[method-assign]
    socket.socket.connect_ex = _fazer_trava(originais["connect_ex"], 1)  # type: ignore[method-assign]
    socket.create_connection = _fazer_trava(originais["create_connection"], 0)  # type: ignore[assignment]
    socket.getaddrinfo = _getaddrinfo_travado(originais["getaddrinfo"])  # type: ignore[assignment]
    try:
        yield
    finally:
        socket.socket.connect = originais["connect"]  # type: ignore[method-assign]
        socket.socket.connect_ex = originais["connect_ex"]  # type: ignore[method-assign]
        socket.create_connection = originais["create_connection"]  # type: ignore[assignment]
        socket.getaddrinfo = originais["getaddrinfo"]  # type: ignore[assignment]


@pytest.fixture(autouse=True)
def sem_chaves_de_provedor(monkeypatch: pytest.MonkeyPatch):
    """Nenhum teste enxerga chave de API, mesmo que exista um .env na máquina."""
    for chave in CHAVES_DE_PROVEDOR:
        monkeypatch.delenv(chave, raising=False)
    monkeypatch.setenv("SUNO_COMITE", "0")
    monkeypatch.setenv("SUNO_JUIZ_VISAO", "0")
    yield


@pytest.fixture(scope="session")
def caminho_ata() -> Path:
    return ATAS / "copom-280-2026-08-05.pdf"


@pytest.fixture(scope="session")
def caminho_ata_txt() -> Path:
    return ATAS / "copom-280-2026-08-05.txt"


@pytest.fixture(scope="session")
def texto_ata(caminho_ata_txt: Path) -> str:
    return caminho_ata_txt.read_text(encoding="utf-8")


@pytest.fixture
def pasta_execucoes(tmp_path: Path) -> Path:
    pasta = tmp_path / "execucoes"
    pasta.mkdir()
    return pasta


def pytest_configure(config: pytest.Config) -> None:
    os.environ.setdefault("MPLBACKEND", "Agg")
