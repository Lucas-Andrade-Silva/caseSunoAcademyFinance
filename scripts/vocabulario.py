"""Procura as palavras da lista _Avoid_ do CONTEXT.md em nomes do código.

Varre classes, funções, parâmetros, variáveis, campos e nomes de arquivo em ``src/``,
``tests/``, ``evals/`` e ``web/src/``. Sai com código 1 se achar algo.

    uv run python scripts/vocabulario.py

Exceções registradas em docs/plano-de-execucao.md: ``ingestao/pdf.py`` (formato de arquivo,
não a Ata) e ``docs/relatorio-experimental.md`` (nome mandado pelo enunciado).
"""

from __future__ import annotations

import ast
import re
import sys
import unicodedata
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
EXCECOES_DE_ARQUIVO = {"pdf"}
EXCECOES_DE_NOME = {"eh_pdf"}


def normalizar(texto: str) -> str:
    return unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode().lower().replace("-", "_").replace(" ", "_")


def palavras_a_evitar() -> set[str]:
    contexto = (RAIZ / "CONTEXT.md").read_text(encoding="utf-8")
    palavras: set[str] = set()
    for linha in contexto.splitlines():
        if linha.strip().startswith("_Avoid_:"):
            for termo in linha.split(":", 1)[1].split(","):
                palavras.add(normalizar(termo.strip()))
    return palavras


def partes_do_nome(nome: str) -> list[str]:
    return [p for p in re.split(r"_|(?<=[a-z0-9])(?=[A-Z])", nome) if p]


def nomes_do_python(caminho: Path) -> set[str]:
    arvore = ast.parse(caminho.read_text(encoding="utf-8"))
    nomes: set[str] = set()
    for no in ast.walk(arvore):
        if isinstance(no, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            nomes.add(no.name)
        elif isinstance(no, ast.arg):
            nomes.add(no.arg)
        elif isinstance(no, ast.Name) and isinstance(no.ctx, ast.Store):
            nomes.add(no.id)
        elif isinstance(no, ast.Attribute) and isinstance(no.ctx, ast.Store):
            nomes.add(no.attr)
    return nomes


def nomes_do_typescript(caminho: Path) -> set[str]:
    texto = caminho.read_text(encoding="utf-8", errors="ignore")
    padrao = re.compile(r"\b(?:function|const|let|var|class|interface|type|enum)\s+([A-Za-z_$][\w$]*)")
    return set(padrao.findall(texto))


def main() -> int:
    evitar = palavras_a_evitar()
    achados: list[tuple[str, str, str]] = []
    pastas = [RAIZ / "src", RAIZ / "tests", RAIZ / "evals", RAIZ / "web" / "src"]
    for pasta in pastas:
        if not pasta.exists():
            continue
        for arquivo in pasta.rglob("*"):
            if arquivo.is_dir() or "node_modules" in arquivo.parts or "api" in arquivo.parts and arquivo.suffix == ".ts" and "generated" in str(arquivo):
                continue
            if arquivo.suffix == ".py":
                nomes = nomes_do_python(arquivo)
            elif arquivo.suffix in {".ts", ".tsx"}:
                nomes = nomes_do_typescript(arquivo)
            else:
                continue
            tronco = normalizar(arquivo.stem)
            for parte in partes_do_nome(tronco):
                if parte in evitar and tronco not in EXCECOES_DE_ARQUIVO:
                    achados.append((str(arquivo.relative_to(RAIZ)), "<arquivo>", parte))
            for nome in nomes:
                if nome in EXCECOES_DE_NOME:
                    continue
                if nome.startswith("__") and nome.endswith("__"):
                    continue  # dunders são protocolo do Python (__post_init__), não nome nosso
                for parte in partes_do_nome(nome):
                    if normalizar(parte) in evitar:
                        achados.append((str(arquivo.relative_to(RAIZ)), nome, normalizar(parte)))
    # Termos compostos da lista (ex. "sugestão de investimento") só batem se o nome inteiro bater.
    for arquivo, nome, parte in sorted(set(achados)):
        print(f"{arquivo}: {nome!r} contém {parte!r}")
    print(f"{len(set(achados))} achado(s); {len(evitar)} palavras a evitar")
    return 1 if achados else 0


if __name__ == "__main__":
    sys.exit(main())
