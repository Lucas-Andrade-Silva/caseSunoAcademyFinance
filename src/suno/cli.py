"""Linha de comando do Suno Content.

    python -m suno.cli executar   --ata data/atas/<ata>.pdf --provedor falso [--comite]
    python -m suno.cli pacote     --execucao <id>
    python -m suno.cli buscar-ata [--reuniao 280]          # H1: roda antes, com rede
    python -m suno.cli video      --execucao <id> --audiencia iniciante
    python -m suno.cli servir     [--porta 8000]

Só ``argparse``, da biblioteca padrão. Cada subcomando delega ao módulo dono; este arquivo
não contém lógica de negócio.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from suno.dominio import Audiencia

PASTA_ATAS = Path("data/atas")


def _pasta_execucoes(argumento: str | None) -> Path:
    return Path(argumento or os.environ.get("SUNO_EXECUCOES", "data/execucoes"))


def _carregar_env() -> None:
    """Lê o .env se existir. A demo com ``--provedor falso`` não precisa dele."""
    try:
        from dotenv import load_dotenv

        load_dotenv(override=False)
    except ImportError:  # pragma: no cover
        pass


def cmd_executar(args: argparse.Namespace) -> int:
    from suno.gerador.execucao import executar

    # --comite liga; sem a flag, SUNO_COMITE=1 no .env também liga (ADR 0008: nasce desligado).
    comite = args.comite or os.environ.get("SUNO_COMITE", "0") == "1"
    execucao = executar(
        Path(args.ata),
        args.provedor,
        _pasta_execucoes(args.execucoes),
        comite=comite,
        identificador=args.identificador,
    )
    aprovadas = sum(1 for h in execucao.celulas if h.destino_final.value == "aprovado")
    print(f"execucao={execucao.identificador} ata={execucao.ata} provedor={execucao.provedor_gerador}")
    print(f"celulas={len(execucao.celulas)} aprovadas={aprovadas} pendencias={len(execucao.pendencias)}")
    if execucao.ciclo_transversal is not None:
        print(
            "matriz="
            f"{execucao.ciclo_transversal.estado.value} "
            f"julgamentos={len(execucao.ciclo_transversal.julgamentos)} "
            f"correcoes={len(execucao.ciclo_transversal.correcoes_aplicadas)}"
        )
    for h in execucao.celulas:
        laudo = h.laudo_final
        motivos = ",".join(m.value for m in laudo.motivos) if laudo else ""
        print(f"  {h.audiencia.value:<14} {h.formato.value:<16} rodadas={len(h.tentativas)} {h.destino_final.value} {motivos}")
    print(f"custo: chamadas={execucao.custo.chamadas} tokens={execucao.custo.tokens_entrada + execucao.custo.tokens_saida} segundos={execucao.custo.segundos:.1f}")
    return 0


def cmd_pacote(args: argparse.Namespace) -> int:
    from suno.pacote import montar_pacote

    pacotes = montar_pacote(args.execucao, _pasta_execucoes(args.execucoes))
    print(f"execucao={args.execucao} pacotes={len(pacotes)}")
    for p in pacotes:
        defeitos = ";".join(m.defeito.value for m in p.conferencia.defeitos) or "sem defeito de render"
        print(f"  {p.audiencia.value:<14} {p.formato.value:<16} imagens={len(p.imagens)} video={'sim' if p.video else 'nao'} {defeitos}")
    return 0


def cmd_buscar_ata(args: argparse.Namespace) -> int:
    from suno.ingestao.bcb import buscar_ata

    ata = buscar_ata(Path(args.destino), reuniao=args.reuniao)
    print(f"ata={ata.identificador} titulo={ata.titulo!r} caracteres={len(ata.texto)}")
    return 0


def cmd_video(args: argparse.Namespace) -> int:
    from suno.video.render import medir_video, renderizar_video

    caminho = renderizar_video(
        args.execucao, Audiencia(args.audiencia), _pasta_execucoes(args.execucoes), narracao=args.narracao
    )
    print(f"video={caminho}")
    for m in medir_video(caminho):
        print(f"  {m.detalhe} {'DEFEITO ' + m.defeito.value if m.defeito else 'ok'}")
    return 0


def cmd_servir(args: argparse.Namespace) -> int:
    import uvicorn

    from suno.api.app import criar_app

    app = criar_app(_pasta_execucoes(args.execucoes))
    uvicorn.run(app, host=args.host, port=args.porta)
    return 0


def construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="suno", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="comando", required=True)

    p = sub.add_parser("executar", help="gera as nove Células de uma Ata e as avalia")
    p.add_argument("--ata", required=True, help="caminho do .pdf ou .txt em data/atas/")
    p.add_argument("--provedor", default="falso", help="falso | gemini | groq | sambanova | roteador")
    p.add_argument("--comite", action="store_true", help="liga o comitê de juízes-LLM (ADR 0008)")
    p.add_argument("--execucoes", default=None, help="pasta de saída (padrão: SUNO_EXECUCOES ou data/execucoes)")
    p.add_argument("--identificador", default=None, help="nome fixo da execução (padrão: <ata>-<provedor>-<carimbo>)")
    p.set_defaults(funcao=cmd_executar)

    p = sub.add_parser("pacote", help="monta o Pacote de publicação das Células aprovadas")
    p.add_argument("--execucao", required=True)
    p.add_argument("--execucoes", default=None)
    p.set_defaults(funcao=cmd_pacote)

    p = sub.add_parser("buscar-ata", help="H1: baixa uma Ata do BCB para data/atas/ (precisa de rede)")
    p.add_argument("--reuniao", type=int, default=None, help="número da reunião; padrão é a mais recente")
    p.add_argument("--destino", default=str(PASTA_ATAS))
    p.set_defaults(funcao=cmd_buscar_ata)

    p = sub.add_parser("video", help="renderiza o mp4 9:16 de um Roteiro aprovado (fora do grafo)")
    p.add_argument("--execucao", required=True)
    p.add_argument("--audiencia", required=True, choices=[a.value for a in Audiencia])
    p.add_argument(
        "--narracao", action="store_true", help="sintetiza voz pt-BR com edge-tts (precisa de rede; falha vira mp4 sem áudio)"
    )
    p.add_argument("--execucoes", default=None)
    p.set_defaults(funcao=cmd_video)

    p = sub.add_parser("servir", help="sobe a API e a interface")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--porta", type=int, default=8000)
    p.add_argument("--execucoes", default=None)
    p.set_defaults(funcao=cmd_servir)
    return parser


def main(argv: list[str] | None = None) -> int:
    _carregar_env()
    args = construir_parser().parse_args(argv)
    return args.funcao(args)


if __name__ == "__main__":
    sys.exit(main())
