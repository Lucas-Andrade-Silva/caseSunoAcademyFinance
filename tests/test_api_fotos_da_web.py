"""A API liga a busca de fotos na web ao montar o Pacote só quando mandam ligar."""

from __future__ import annotations

from pathlib import Path

import pytest

from suno.api import app as modulo_app
from suno.dominio import Audiencia, Formato


@pytest.fixture
def chamadas(monkeypatch):
    vistas: list[dict] = []

    def falso(identificador, pasta, **kwargs):
        vistas.append(kwargs)
        return []

    monkeypatch.setattr(modulo_app, "montar_pacote", falso)
    return vistas


@pytest.mark.parametrize("ligar", [False, True])
def test_montar_repassa_buscar_fotos_e_o_juiz_das_fotos(tmp_path: Path, chamadas, ligar):
    juiz = object()
    app = modulo_app.criar_app(tmp_path, recuperar_ao_iniciar=False, buscar_fotos=ligar, provedor_fotos=juiz)
    montador = app.state.montador
    montador._montar("x", tmp_path)
    montador._montar_celula("x", tmp_path, Audiencia.INICIANTE, Formato.CARROSSEL)
    assert len(chamadas) == 2
    assert all(c["buscar_fotos"] is ligar and c["provedor_fotos"] is juiz for c in chamadas)


def test_por_padrao_nunca_toca_a_rede(tmp_path: Path, chamadas):
    app = modulo_app.criar_app(tmp_path, recuperar_ao_iniciar=False)
    app.state.montador._montar("x", tmp_path)
    assert chamadas[0]["buscar_fotos"] is False and chamadas[0]["provedor_fotos"] is None
