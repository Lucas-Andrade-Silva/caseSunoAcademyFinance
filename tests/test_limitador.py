"""O teto de requisições por minuto aos LLMs."""

from suno.provedores.limitador import JANELA_S, LimitadorPorMinuto


def test_a_nona_requisicao_espera_a_janela_abrir():
    agora = [0.0]
    esperas: list[float] = []

    def dormir(s: float) -> None:
        esperas.append(s)
        agora[0] += s

    limitador = LimitadorPorMinuto(8, relogio=lambda: agora[0], dormir=dormir)
    for _ in range(8):
        assert limitador.aguardar() == 0.0
    assert esperas == []
    assert limitador.aguardar() == JANELA_S
    assert esperas == [JANELA_S]


def test_zero_desliga_o_limite():
    limitador = LimitadorPorMinuto(0, relogio=lambda: 0.0, dormir=lambda s: (_ for _ in ()).throw(AssertionError))
    for _ in range(50):
        assert limitador.aguardar() == 0.0
