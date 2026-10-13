"""Linha de comando do Suno Content.

    python -m suno.cli executar   --ata data/atas/<ata>.pdf --provedor falso [--comite]
    python -m suno.cli pacote     --execucao <id>
    python -m suno.cli buscar-ata [--reuniao 280]          # H1: roda antes, com rede
    python -m suno.cli video      --execucao <id> --audiencia iniciante
    python -m suno.cli plano      --execucao <id> --audiencia iniciante
    python -m suno.cli servir     [--porta 8000]
    python -m suno.cli imagens    listar | buscar "<assunto>" [--rede] | aprovar <id>

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
    from suno.video.design import duracao_valida

    # --comite liga; sem a flag, SUNO_COMITE=1 no .env também liga (ADR 0008: nasce desligado).
    comite = args.comite or os.environ.get("SUNO_COMITE", "0") == "1"
    execucao = executar(
        Path(args.ata),
        args.provedor,
        _pasta_execucoes(args.execucoes),
        comite=comite,
        identificador=args.identificador,
        duracao=duracao_valida(args.duracao),
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

    from suno.dominio import FamiliaVisual

    pacotes = montar_pacote(
        args.execucao,
        _pasta_execucoes(args.execucoes),
        familia_visual=FamiliaVisual(args.familia) if args.familia else None,
        buscar_fotos=args.buscar_fotos,
    )
    print(f"execucao={args.execucao} pacotes={len(pacotes)}")
    for p in pacotes:
        defeitos = ";".join(m.defeito.value for m in p.conferencia.defeitos) or "sem defeito de render"
        familia = p.direcao_de_arte.familia.value if p.direcao_de_arte and p.direcao_de_arte.familia else "-"
        print(
            f"  {p.audiencia.value:<14} {p.formato.value:<16} imagens={len(p.imagens)} fotos={len(p.fotos)} "
            f"familia={familia} video={'sim' if p.video else 'nao'} {defeitos}"
        )
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


def cmd_plano(args: argparse.Namespace) -> int:
    from suno.video.plano import plano_do_roteiro

    caminho = plano_do_roteiro(args.execucao, Audiencia(args.audiencia), _pasta_execucoes(args.execucoes))
    print(f"plano={caminho}")
    print(f"markdown={caminho.with_suffix('.md')}")
    return 0


def cmd_servir(args: argparse.Namespace) -> int:
    import uvicorn

    from suno.api.app import criar_app

    app = criar_app(_pasta_execucoes(args.execucoes))
    uvicorn.run(app, host=args.host, port=args.porta)
    return 0


def cmd_imagens(args: argparse.Namespace) -> int:
    from suno.dominio import ErroProvedor, PapelLLM
    from suno.imagens import BibliotecaDeImagens, ImagemInexistente, resolver_imagem

    biblioteca = BibliotecaDeImagens(args.pasta)
    if args.acao == "listar":
        for e in biblioteca.listar():
            estado = "aprovada" if e.aprovada else "rejeitada" if e.rejeitada else "pendente"
            print(f"{e.id:<24} {estado:<9} {e.licenca:<12} {e.autor[:30]:<30} tags={','.join(e.tags)}")
        return 0
    if args.acao == "aprovar":
        try:
            biblioteca.aprovar(args.id)
        except ImagemInexistente:
            print(f"imagem {args.id!r} não está no índice", file=sys.stderr)
            return 1
        print(f"aprovada: {args.id}")
        return 0
    provedor_visao = None
    if args.rede:
        try:
            from suno.provedores.roteador import roteador_para

            provedor_visao = roteador_para(PapelLLM.JUIZ_VISAO)
        except ErroProvedor as erro:
            print(f"sem juiz de visão ({erro}): a foto baixada fica pendente de aprovação humana", file=sys.stderr)
    imagem = resolver_imagem(
        args.consulta, biblioteca, contexto=args.contexto, permitir_rede=args.rede, provedor_visao=provedor_visao
    )
    if imagem is None:
        pendentes = [e.id for e in biblioteca.listar() if not e.aprovada and not e.rejeitada]
        print("nenhuma imagem aprovada para esse assunto")
        if args.rede and pendentes:
            print(f"pendentes de aprovação humana: {', '.join(pendentes)} (use: imagens aprovar <id>)")
        return 1
    print(f"arquivo={imagem.arquivo} origem={imagem.origem} validada_por={imagem.validada_por} {imagem.largura}x{imagem.altura}")
    print(imagem.credito())
    return 0


def construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="suno", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="comando", required=True)

    p = sub.add_parser("executar", help="gera as nove Células de uma Ata e as avalia")
    p.add_argument("--ata", required=True, help="caminho do .pdf ou .txt em data/atas/")
    p.add_argument("--provedor", default="falso", help="falso | gemini | groq | sambanova | roteador")
    p.add_argument("--comite", action="store_true", help="liga o comitê de juízes-LLM (ADR 0008)")
    p.add_argument("--execucoes", default=None, help="pasta de saída (padrão: SUNO_EXECUCOES ou data/execucoes)")
    p.add_argument(
        "--duracao", type=int, default=60, choices=[40, 60, 90, 120, 180],
        help="duração do Roteiro em segundos (padrão: 60)",
    )
    p.add_argument("--identificador", default=None, help="nome fixo da execução (padrão: <ata>-<provedor>-<carimbo>)")
    p.set_defaults(funcao=cmd_executar)

    p = sub.add_parser("pacote", help="monta o Pacote de publicação das Células aprovadas")
    p.add_argument("--execucao", required=True)
    p.add_argument("--execucoes", default=None)
    p.add_argument(
        "--familia",
        choices=["suno_escuro", "noticia", "explicativo", "jornal", "dados", "asset"],
        default=None,
        help="família visual do Carrossel (padrão: escolha automática entre notícia, explicativo, jornal e dados)",
    )
    p.add_argument(
        "--buscar-fotos",
        action="store_true",
        help="busca no Wikimedia Commons as fotos que a biblioteca local não tem (precisa de rede; a demo não usa)",
    )
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

    p = sub.add_parser("plano", help="grava o plano de edição (JSON para avatar + Markdown) de um Roteiro aprovado")
    p.add_argument("--execucao", required=True)
    p.add_argument("--audiencia", required=True, choices=[a.value for a in Audiencia])
    p.add_argument("--execucoes", default=None)
    p.set_defaults(funcao=cmd_plano)

    p = sub.add_parser("servir", help="sobe a API e a interface")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--porta", type=int, default=8000)
    p.add_argument("--execucoes", default=None)
    p.set_defaults(funcao=cmd_servir)

    p = sub.add_parser("imagens", help="fotos reais dos slides: biblioteca local e Wikimedia Commons")
    p.add_argument("--pasta", default="data/imagens", help="pasta da biblioteca (padrão: data/imagens)")
    acoes = p.add_subparsers(dest="acao", required=True)
    acoes.add_parser("listar", help="lista as fotos do índice e seu estado")
    a = acoes.add_parser("buscar", help="resolve um assunto em uma foto aprovada e imprime o crédito")
    a.add_argument("consulta")
    a.add_argument("--contexto", default="", help="o que o slide diz, para o juiz de visão")
    a.add_argument("--rede", action="store_true", help="busca no Commons se a biblioteca não tiver (precisa de rede)")
    a = acoes.add_parser("aprovar", help="aprova à mão uma foto pendente")
    a.add_argument("id")
    p.set_defaults(funcao=cmd_imagens)
    return parser


def main(argv: list[str] | None = None) -> int:
    _carregar_env()
    args = construir_parser().parse_args(argv)
    return args.funcao(args)


if __name__ == "__main__":
    sys.exit(main())
