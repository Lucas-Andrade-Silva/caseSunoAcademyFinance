"""Teste de fumaça das duas camadas de LLM do Avaliador: o Jev (Qualidade, ADR 0035) e o checador de
fidelidade no Groq e depois no Gemini (ADR 0036). Faz UMA chamada de cada, com texto de exemplo, e imprime o que voltou.

Precisa de rede e gasta cota (o Jev cobra pela entrada). Não faz parte do pytest, que roda offline.

    uv run python scripts/testar_llm_de_avaliacao.py            # os dois
    uv run python scripts/testar_llm_de_avaliacao.py jev        # só o Jev
    uv run python scripts/testar_llm_de_avaliacao.py checador   # só o checador (Groq, depois Gemini)

Lê o .env da raiz. Nunca imprime chave.
"""

from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))
load_dotenv(RAIZ / ".env", override=False)

from suno.avaliador.fidelidade import VerificadorDeFidelidade  # noqa: E402
from suno.avaliador.qualidade import AvaliadorDeQualidade  # noqa: E402
from suno.dominio import Audiencia, Conteudo, ErroProvedor, Formato  # noqa: E402

TEXTO_BOM = (
    "A Selic (a taxa básica de juros do país) ficou em 14,00% ao ano. O Banco Central: é a instituição "
    "que cuida do valor do dinheiro. A decisão foi tomada por 7 votos a 0.\n\n"
    "O comitê avalia que os riscos para a inflação seguem desiguais e diz que vai acompanhar de perto "
    "os preços dos serviços. Na prática, isso quer dizer que o custo do crédito não deve mudar logo."
)
TEXTO_CORTADO = (
    "A Selic (a taxa básica de juros do país) ficou em 14,00% ao ano. O Banco Central decidiu isso porque"
)
TEXTO_COM_INVENCAO = TEXTO_BOM + " O comitê prometeu baixar os preços dos alimentos no mês que vem."
ATA = RAIZ / "data" / "atas" / "copom-280-2026-08-05.txt"


def jev() -> bool:
    avaliador = AvaliadorDeQualidade.de_ambiente(ligado=True)
    if avaliador is None:
        print("JEV: não montou. Preencha JEV_API_KEY (e JEV_URL, se usar uma Netlify Function) no .env.")
        return False
    ok = True
    for rotulo, texto in (("texto bom", TEXTO_BOM), ("texto cortado no meio", TEXTO_CORTADO)):
        try:
            resultado = avaliador.medir(Conteudo(formato=Formato.TEXTO_ANALITICO, texto=texto), Audiencia.INICIANTE)
        except ErroProvedor as erro:
            print(f"JEV falhou em '{rotulo}': {erro}")
            ok = False
            continue
        print(f"JEV — {rotulo}:")
        for d in resultado.dimensoes:
            confianca = "?" if d.confianca is None else f"{d.confianca:.2f}"
            print(f"   {d.rotulo:<16} {d.nota:>4.0%}  (confiança {confianca})  {d.nivel}")
        print(f"   menor nota {resultado.menor.nota:.0%}; Limiar {avaliador.limiar:.0%}")
    return ok


def checador() -> bool:
    if not ATA.exists():
        print(f"CHECADOR: falta {ATA}")
        return False
    verificador = VerificadorDeFidelidade.de_ambiente(ATA.read_text(encoding="utf-8"), ligado=True)
    if verificador is None:
        print("CHECADOR: não montou. Preencha GROQ_API_KEY e GROQ_MODELO (ou GEMINI_API_KEY e GEMINI_MODELO) no .env.")
        return False
    ok = True
    for rotulo, texto in (("texto fiel", TEXTO_BOM), ("texto com uma afirmação inventada", TEXTO_COM_INVENCAO)):
        try:
            resultado = verificador.verificar(Conteudo(formato=Formato.TEXTO_ANALITICO, texto=texto), Audiencia.INICIANTE)
        except ErroProvedor as erro:
            print(f"CHECADOR falhou em '{rotulo}': {erro}")
            ok = False
            continue
        print(f"CHECADOR — {rotulo}: {len(resultado.achados)} achado(s), {resultado.descartados} descartado(s)")
        for linha in getattr(verificador.provedor, "historico", []):
            print(f"   [roteador] {linha}")
        for achado in resultado.achados:
            print(f"   - {achado.descricao}")
    return ok


if __name__ == "__main__":
    alvo = sys.argv[1] if len(sys.argv) > 1 else "todos"
    resultados = []
    if alvo in ("todos", "jev"):
        resultados.append(jev())
    if alvo in ("todos", "checador"):
        resultados.append(checador())
    sys.exit(0 if resultados and all(resultados) else 1)
