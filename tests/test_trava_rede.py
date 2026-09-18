"""Prova que a trava de rede existe: quem tentar sair quebra."""

from __future__ import annotations

import os
import socket

import httpx
import pytest

from tests.conftest import CHAVES_DE_PROVEDOR, RedeBloqueada


def test_socket_direto_e_bloqueado():
    with pytest.raises(RedeBloqueada):
        socket.create_connection(("example.com", 80), timeout=1)


def test_conexao_por_socket_e_bloqueada():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        with pytest.raises(RedeBloqueada):
            s.connect(("192.0.2.1", 9))  # TEST-NET-1: nunca roteável
    finally:
        s.close()


def test_loopback_fica_livre_para_o_laco_asyncio():
    """No Windows, `asyncio.new_event_loop()` conecta em 127.0.0.1 via socketpair; não pode cair na trava."""
    a, b = socket.socketpair()
    a.close()
    b.close()


def test_resolucao_de_nome_e_bloqueada():
    with pytest.raises(RedeBloqueada):
        socket.getaddrinfo("www.bcb.gov.br", 443)


def test_httpx_nao_sai_para_a_rede():
    """httpx é o único caminho para a rede no projeto (ADR 0007); ele também cai na trava."""
    with pytest.raises((RedeBloqueada, httpx.HTTPError)):
        httpx.get("https://www.bcb.gov.br/api/servico/sitebcb/atascopom/ultimas?quantidade=1&filtro=", timeout=2)


def test_nenhuma_chave_de_provedor_no_ambiente():
    for chave in CHAVES_DE_PROVEDOR:
        assert chave not in os.environ
