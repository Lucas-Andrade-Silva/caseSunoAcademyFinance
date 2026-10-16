"""A paleta escolhida no editor recolore os Layouts das famílias sem tocar no texto nem na foto."""

from pathlib import Path

import pytest

from suno.dominio import PaletaVisual
from suno.pacote.recolorir import embutir_arquivos, recolorir

FLORESTA = PaletaVisual(fundo="#0C1A14", texto="#F1FBF5", destaque="#3DDC84", apoio="#1B6B45")


def _documento(estilo: str, corpo: str = "", fundo: str = "#FFFFFF") -> str:
    return f'<style>{estilo}</style><body data-fundo data-fundo-cor="{fundo}">{corpo}</body>'


def test_sem_paleta_o_html_sai_igual() -> None:
    html = _documento(".a{color:#b80000}")
    assert recolorir(html, None) == html


def test_no_layout_claro_o_branco_vira_o_fundo_e_o_preto_vira_o_texto() -> None:
    html = recolorir(_documento(".f{background:#fff}.t{color:#000000}"), FLORESTA)
    assert ".f{background:#0c1a14}" in html
    assert ".t{color:#f1fbf5}" in html


def test_no_layout_escuro_a_polaridade_se_inverte() -> None:
    html = recolorir(_documento(".f{background:#000}.t{color:#fff}", fundo="#000000"), FLORESTA)
    assert ".f{background:#0c1a14}" in html
    assert ".t{color:#f1fbf5}" in html


def test_o_vermelho_vira_o_destaque_e_o_vinho_vira_o_apoio() -> None:
    html = recolorir(_documento(".r{color:#e30613}.v{color:#3a0507}"), FLORESTA)
    assert ".r{color:#3ddc84}" in html
    assert ".v{color:#1b6b45}" in html


def test_cinza_fica_entre_o_fundo_e_o_texto() -> None:
    html = recolorir(_documento(".c{color:#808080}"), FLORESTA)
    cor = html.split(".c{color:")[1][:7]
    assert cor not in {"#0c1a14", "#f1fbf5", "#808080"}


def test_a_transparencia_do_rgba_se_mantem() -> None:
    html = recolorir(_documento(".s{box-shadow:0 0 4px rgba(0,0,0,.35)}"), FLORESTA)
    assert "rgba(241,251,245,0.35)" in html


def test_cores_de_atributos_svg_tambem_mudam_e_o_texto_nao() -> None:
    corpo = '<svg><path stroke="#000" fill="url(#abc)"/></svg><p>Meta #fff de 2026</p>'
    html = recolorir(_documento("", corpo), FLORESTA)
    assert 'stroke="#f1fbf5"' in html
    assert 'fill="url(#abc)"' in html
    assert "Meta #fff de 2026" in html


def test_documento_sem_fundo_declarado_nao_e_recolorido() -> None:
    html = "<style>.a{color:#b80000}</style><body>x</body>"
    assert recolorir(html, FLORESTA) == html


def test_paleta_rejeita_cor_fora_do_formato() -> None:
    with pytest.raises(ValueError):
        PaletaVisual(fundo="verde", texto="#FFFFFF", destaque="#FF0000", apoio="#000000")


def test_paleta_le_a_forma_curta_da_rota() -> None:
    assert PaletaVisual.da_rota("#0C1A14,#F1FBF5,#3DDC84,#1B6B45") == FLORESTA


def test_embutir_troca_arquivo_permitido_por_data_uri(tmp_path: Path) -> None:
    fonte = tmp_path / "fonte.woff2"
    fonte.write_bytes(b"abc")
    fora = tmp_path.parent / "segredo.txt"
    html = f'<style>src:url("{fonte.as_uri()}")</style><img src="{fora.as_uri()}">'
    saida = embutir_arquivos(html, permitidas=[tmp_path])
    assert 'url("data:font/woff2;base64,YWJj")' in saida
    assert fora.as_uri() not in saida
