"""Teste de campo da busca de imagens: roda assuntos reais na web e monta folhas de contato.

Não é teste de CI (usa rede). Serve para conferir, a olho, se a foto que o sistema escolhe é a
do assunto. Cada assunto é do tamanho do que o Gerador põe em ``Slide.imagem``.

    uv run python scripts/testar_busca_de_imagens.py [--saida PASTA] [--juiz] [--so empresas,conceitos]

Sem ``--juiz`` o Gemini não é chamado: o que o texto aprova aparece como "texto" e o que ficaria
para o juiz aparece como "dúvida". Com ``--juiz`` a dúvida é decidida pela visão (cota gratuita).
Grava ``resultado.json``, ``resumo.md`` e uma folha ``folha-N.png`` por 12 assuntos.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path

from PIL import Image, ImageDraw

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))

from suno.imagens import BibliotecaDeImagens, resolver_imagem  # noqa: E402
from suno.imagens.consulta import planejar  # noqa: E402

ASSUNTOS: dict[str, list[str]] = {
    "empresas": [
        "sede da B3", "logo B3", "Petrobras", "logo Petrobras", "Vale mineradora", "Itaú Unibanco",
        "logo Itaú", "Bradesco", "Banco do Brasil", "Caixa Econômica Federal", "Santander Brasil",
        "logo Nubank", "BTG Pactual", "XP Investimentos", "Banco Inter", "Magazine Luiza", "Americanas",
        "Ambev", "JBS", "WEG motores", "Embraer", "Suzano", "Gerdau", "Eletrobras", "Localiza",
        "Azul linhas aéreas", "Gol Linhas Aéreas", "LATAM", "Lojas Renner", "Natura", "Mercado Livre",
        "Apple", "Tesla", "Nvidia", "Amazon",
    ],
    "instituicoes": [
        "sede do Banco Central", "logo do Banco Central", "reunião do Copom", "CVM", "Tesouro Nacional",
        "Ministério da Fazenda", "Federal Reserve", "BNDES", "IBGE", "FGC", "Congresso Nacional",
    ],
    "conceitos": [
        "taxa Selic", "taxa de juros", "inflação IPCA", "dólar", "euro", "CDI", "Tesouro Direto",
        "CDB renda fixa", "poupança", "Bitcoin", "ouro", "petróleo", "PIB", "desemprego",
        "contas públicas", "recessão", "crédito", "endividamento", "cartão de crédito", "Pix",
        "financiamento imobiliário", "FGTS", "aposentadoria INSS", "imposto de renda", "Wall Street",
        "Ibovespa", "pregão da B3", "dividendos", "fundos imobiliários", "ETF", "ações", "China",
    ],
    "setores": [
        "agronegócio", "soja", "mineração", "conta de luz", "posto de gasolina", "bancos", "varejo",
        "aviação", "inteligência artificial", "fintech", "planos de saúde", "carne frigorífico",
        "porto exportação", "construção civil",
    ],
    "fora_do_catalogo": [
        "Faria Lima", "mercado de carbono", "bolsa de Tóquio", "reforma da previdência",
        "greve dos caminhoneiros", "Galípolo", "Warren Buffett", "shopping center",
    ],
}

COLUNAS, LINHAS = 4, 3
CELULA = (360, 300)
FOTO = (352, 220)


def cor_do_metodo(metodo: str) -> tuple[int, int, int]:
    return {"texto": (30, 130, 60), "visao": (30, 90, 170), "duvida": (200, 120, 0), "nada": (190, 30, 30)}.get(
        metodo, (80, 80, 80)
    )


def montar_folha(itens: list[dict], caminho: Path) -> None:
    folha = Image.new("RGB", (COLUNAS * CELULA[0], LINHAS * CELULA[1]), (245, 245, 245))
    desenho = ImageDraw.Draw(folha)
    for n, item in enumerate(itens):
        x, y = (n % COLUNAS) * CELULA[0], (n // COLUNAS) * CELULA[1]
        if item.get("arquivo"):
            try:
                with Image.open(item["arquivo"]) as imagem:
                    imagem = imagem.convert("RGB")
                    imagem.thumbnail(FOTO)
                    folha.paste(imagem, (x + 4 + (FOTO[0] - imagem.width) // 2, y + 4))
            except OSError:
                desenho.text((x + 10, y + 100), "(imagem ilegível)", fill=(0, 0, 0))
        else:
            desenho.rectangle((x + 4, y + 4, x + FOTO[0], y + FOTO[1]), outline=(190, 30, 30))
            desenho.text((x + 120, y + 100), "SEM FOTO", fill=(190, 30, 30))
        desenho.text((x + 6, y + FOTO[1] + 8), f"{item['assunto']}  [{item['plano']}]", fill=(0, 0, 0))
        desenho.text((x + 6, y + FOTO[1] + 24), f"{item['metodo'].upper()}  {item.get('dominio', '')}", fill=cor_do_metodo(item["metodo"]))
        desenho.text((x + 6, y + FOTO[1] + 40), (item.get("titulo") or "")[:58], fill=(90, 90, 90))
    folha.save(caminho)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--saida", default="saida-busca-de-imagens")
    parser.add_argument("--juiz", action="store_true", help="usa o juiz de visão (Gemini) nas dúvidas")
    parser.add_argument("--so", default="", help="grupos separados por vírgula (padrão: todos)")
    args = parser.parse_args()
    logging.basicConfig(level=logging.WARNING)
    try:  # as chaves (Gemini, Serper) vêm do .env, como na CLI
        from dotenv import load_dotenv

        load_dotenv(RAIZ / ".env", override=False)
    except ImportError:
        pass

    pasta = Path(args.saida)
    pasta.mkdir(parents=True, exist_ok=True)
    biblioteca = BibliotecaDeImagens(pasta / "biblioteca")
    biblioteca.pasta.mkdir(parents=True, exist_ok=True)
    if not biblioteca.caminho_do_indice.exists():
        biblioteca.caminho_do_indice.write_text("[]", encoding="utf-8")

    juiz = None
    if args.juiz:
        from suno.dominio import PapelLLM
        from suno.provedores.roteador import roteador_para

        juiz = roteador_para(PapelLLM.JUIZ_VISAO)

    grupos = [g for g in ASSUNTOS if not args.so or g in args.so.split(",")]
    resultados: list[dict] = []
    for grupo in grupos:
        for assunto in ASSUNTOS[grupo]:
            inicio = time.time()
            plano = planejar(assunto)
            antes = {e.id for e in biblioteca.listar()}
            imagem = resolver_imagem(assunto, biblioteca, permitir_rede=True, provedor_visao=juiz, contexto=assunto)
            novas = [e for e in biblioteca.listar() if e.id not in antes]
            registro: dict = {"grupo": grupo, "assunto": assunto, "plano": plano.id, "consulta": plano.consultas[0], "segundos": round(time.time() - inicio, 1)}
            if imagem is not None:
                registro |= {"metodo": imagem.validada_por or "biblioteca", "arquivo": str(imagem.arquivo), "titulo": imagem.titulo, "dominio": imagem.autor, "url": imagem.url_origem}
            elif novas:
                pendente = novas[0]
                registro |= {"metodo": "duvida", "arquivo": str(biblioteca.pasta / pendente.arquivo), "titulo": pendente.titulo, "dominio": pendente.autor, "url": pendente.url_origem}
            else:
                registro["metodo"] = "nada"
            resultados.append(registro)
            print(f"{grupo[:5]:<5} {assunto:<28} {plano.id:<16} {registro['metodo']:<8} {registro['segundos']:>5}s  {registro.get('dominio', '')}", flush=True)
            time.sleep(1.0)

    (pasta / "resultado.json").write_text(json.dumps(resultados, ensure_ascii=False, indent=1), encoding="utf-8")
    por_metodo: dict[str, int] = {}
    for r in resultados:
        por_metodo[r["metodo"]] = por_metodo.get(r["metodo"], 0) + 1
    resumo = ["# Teste de campo da busca de imagens", "", f"{len(resultados)} assuntos.", ""]
    resumo += [f"- {metodo}: {n}" for metodo, n in sorted(por_metodo.items())]
    (pasta / "resumo.md").write_text("\n".join(resumo) + "\n", encoding="utf-8")
    por_folha = COLUNAS * LINHAS
    for n in range(0, len(resultados), por_folha):
        montar_folha(resultados[n : n + por_folha], pasta / f"folha-{n // por_folha + 1}.png")
    print("\n".join(resumo))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
