"""Exportar uma Saída: JSON, Markdown ou ZIP.

O JSON e o Markdown saem do próprio ``Execucao`` em memória (já com ``nome`` e ``decisoes``),
e não de arquivos em disco: uma execução gravada antes do front novo não tem esses campos no
``execucao.json``. O ZIP leva também a pasta ``pacote/`` quando ela existe.
"""

from __future__ import annotations

import io
import zipfile
from enum import StrEnum
from pathlib import Path

from suno.dominio import Audiencia, Execucao, Formato
from suno.gerador.execucao import _markdown_da_celula

ROTULO_DA_AUDIENCIA: dict[Audiencia, str] = {
    Audiencia.INICIANTE: "Iniciante",
    Audiencia.INTERMEDIARIO: "Intermediário",
    Audiencia.AVANCADO: "Avançado",
}
ROTULO_DO_FORMATO: dict[Formato, str] = {
    Formato.TEXTO_ANALITICO: "Texto analítico",
    Formato.CARROSSEL: "Carrossel",
    Formato.ROTEIRO: "Roteiro",
}


class FormatoExportacao(StrEnum):
    JSON = "json"
    MARKDOWN = "md"
    ZIP = "zip"


def _linha_da_decisao(execucao: Execucao, audiencia: Audiencia, formato: Formato) -> str:
    decisao = execucao.decisao_de(audiencia, formato)
    if decisao is None:
        return "Decisão: pendente"
    quem = f" por {decisao.revisor}" if decisao.revisor else ""
    motivo = f" — {decisao.motivo}" if decisao.motivo else ""
    return f"Decisão: {decisao.estado.value}{quem}{motivo}"


def _markdown(execucao: Execucao) -> str:
    partes = [
        f"# {execucao.nome}",
        "",
        f"Ata: {execucao.ata} · provedor: {execucao.provedor_gerador}",
    ]
    for historico in execucao.celulas:
        partes += [
            "",
            "---",
            "",
            f"## {ROTULO_DA_AUDIENCIA[historico.audiencia]} · {ROTULO_DO_FORMATO[historico.formato]}",
            "",
            _linha_da_decisao(execucao, historico.audiencia, historico.formato),
            "",
            _markdown_da_celula(historico),
        ]
    return "\n".join(partes)


def _zip(execucao: Execucao, pasta: Path) -> bytes:
    raiz = execucao.identificador
    memoria = io.BytesIO()
    with zipfile.ZipFile(memoria, "w", zipfile.ZIP_DEFLATED) as arquivo:
        arquivo.writestr(f"{raiz}/execucao.json", execucao.model_dump_json(indent=2))
        for historico in execucao.celulas:
            nome = f"{historico.audiencia.value}-{historico.formato.value}.md"
            arquivo.writestr(f"{raiz}/celulas/{nome}", _markdown_da_celula(historico))
        pasta_do_pacote = pasta / "pacote"
        if pasta_do_pacote.is_dir():
            for caminho in sorted(pasta_do_pacote.rglob("*")):
                if caminho.is_file():
                    relativo = caminho.relative_to(pasta).as_posix()
                    arquivo.write(caminho, f"{raiz}/{relativo}")
    return memoria.getvalue()


def exportar(
    execucao: Execucao, pasta: Path, formato: FormatoExportacao
) -> tuple[bytes, str, str]:
    """Devolve ``(conteúdo, media_type, nome_do_arquivo)``.

    ``pasta`` é ``<pasta_execucoes>/<identificador>``; só o ZIP a lê (para o Pacote).
    """
    identificador = execucao.identificador
    if formato is FormatoExportacao.JSON:
        return (
            execucao.model_dump_json(indent=2).encode("utf-8"),
            "application/json",
            f"{identificador}.json",
        )
    if formato is FormatoExportacao.MARKDOWN:
        return (
            _markdown(execucao).encode("utf-8"),
            "text/markdown; charset=utf-8",
            f"{identificador}.md",
        )
    return _zip(execucao, pasta), "application/zip", f"{identificador}.zip"
