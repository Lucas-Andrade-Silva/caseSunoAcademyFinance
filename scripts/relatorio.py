"""Gera ``docs/relatorio/<id>.json`` a partir de uma execução gravada em disco.

O arquivo é o resumo que o Entregável 6 cita — nenhuma tabela do relatório experimental
escreve um número que não venha daqui. O conteúdo é ``resumo_da_execucao(execucao)``
(``src/suno/avaliador/calibracao.py``): contagem por motivo de reprovação, rodadas por
Célula, a matriz de confusão automática (Audiência pretendida × Audiência que o Flesch-BR
mediria, ``origem: NILC, aguardando Calibração``) e a contagem de pendências.

    uv run --offline python scripts/relatorio.py --execucao demo-copom-280

Só lê ``data/execucoes/<id>/execucao.json`` (o mesmo arquivo que o pytest lê e que a API
expõe) e grava ``docs/relatorio/<id>.json``. Não acessa rede, não muda a execução.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))

from suno.avaliador.calibracao import resumo_da_execucao  # noqa: E402
from suno.gerador.execucao import carregar_execucao  # noqa: E402


def gerar(identificador: str, pasta_execucoes: Path, pasta_saida: Path) -> Path:
    execucao = carregar_execucao(identificador, pasta_execucoes)
    resumo = resumo_da_execucao(execucao)
    pasta_saida.mkdir(parents=True, exist_ok=True)
    destino = pasta_saida / f"{identificador}.json"
    destino.write_text(
        json.dumps(resumo, ensure_ascii=False, indent=2, sort_keys=False),
        encoding="utf-8",
    )
    return destino


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--execucao", required=True, help="identificador da execução em data/execucoes/")
    parser.add_argument(
        "--execucoes",
        default=os.environ.get("SUNO_EXECUCOES", "data/execucoes"),
        help="pasta onde as execuções estão gravadas (padrão: SUNO_EXECUCOES ou data/execucoes)",
    )
    parser.add_argument("--saida", default="docs/relatorio", help="pasta de saída dos JSON (padrão: docs/relatorio)")
    args = parser.parse_args(argv)

    destino = gerar(args.execucao, Path(args.execucoes), RAIZ / args.saida)
    print(f"gravado: {destino.relative_to(RAIZ)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
