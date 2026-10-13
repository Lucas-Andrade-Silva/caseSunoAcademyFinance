"""Busca foto no Wikimedia Commons e baixa a miniatura com licença, autor e link.

Só aceita licenças que permitem reuso (CC0, domínio público, CC BY, CC BY-SA). Sem chave, sem login.
Uso: python buscar_commons.py <apelido> "<consulta>" [<consulta2> ...]
Grava <apelido>.jpg e acrescenta o crédito em creditos.json (pasta deste arquivo).
"""
from __future__ import annotations
import html, json, re, sys, urllib.parse, urllib.request
from pathlib import Path

PASTA = Path(__file__).parent
UA = {"User-Agent": "SunoContentCase/0.1 (projeto academico; contato: lucas.silva@estimulo.org)"}
LICENCAS = re.compile(r"^(CC0|Public domain|PD|CC BY(-SA)? [\d.]+)", re.I)

def _get(url: str) -> bytes:
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40) as r:
        return r.read()

def buscar(consulta: str, largura: int = 1200) -> dict | None:
    q = urllib.parse.urlencode({
        "action": "query", "generator": "search", "gsrnamespace": 6, "gsrlimit": 12,
        "gsrsearch": f"{consulta} filetype:bitmap", "prop": "imageinfo",
        "iiprop": "url|size|extmetadata", "iiurlwidth": largura, "format": "json"})
    dados = json.loads(_get("https://commons.wikimedia.org/w/api.php?" + q))
    paginas = sorted(dados.get("query", {}).get("pages", {}).values(), key=lambda p: p.get("index", 0))
    for p in paginas:
        ii = p["imageinfo"][0]; m = ii["extmetadata"]
        lic = m.get("LicenseShortName", {}).get("value", "")
        if not LICENCAS.match(lic) or ii["width"] < 900 or "thumburl" not in ii:
            continue
        autor = re.sub(r"<[^>]+>", "", html.unescape(m.get("Artist", {}).get("value", ""))).strip()
        return {"titulo": p["title"].removeprefix("File:"), "licenca": lic, "autor": autor or "autor não informado",
                "pagina": ii["descriptionurl"], "miniatura": ii["thumburl"]}
    return None

if __name__ == "__main__":
    apelido, consultas = sys.argv[1], sys.argv[2:]
    for c in consultas:
        achado = buscar(c)
        if achado:
            break
    else:
        sys.exit(f"nada com licença livre para {consultas}")
    (PASTA / f"{apelido}.jpg").write_bytes(_get(achado["miniatura"]))
    arq = PASTA / "creditos.json"
    creditos = json.loads(arq.read_text(encoding="utf-8")) if arq.exists() else {}
    creditos[apelido] = {k: v for k, v in achado.items() if k != "miniatura"} | {"consulta": c}
    arq.write_text(json.dumps(creditos, ensure_ascii=False, indent=2), encoding="utf-8")
    print(apelido, "<-", achado["titulo"][:60], "|", achado["licenca"], "|", achado["autor"][:40])
