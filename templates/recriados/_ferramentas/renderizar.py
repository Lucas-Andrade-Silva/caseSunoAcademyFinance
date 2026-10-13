"""Renderiza os HTML de uma pasta em PNG 1080x1350 e monta a comparação com a referência real.

Uso:  python templates/recriados/_ferramentas/renderizar.py <pasta_com_html> [--ref <pasta_de_referencia>]

Nos HTML, use estes marcadores (trocados antes de renderizar):
  {{FONTES}}   -> bloco @font-face com todas as fontes do projeto (Anton, Poppins 300/400/600/700,
                  Inter 400/500/600/700, Newsreader 400/600/700). Famílias: "Anton", "Poppins",
                  "Inter", "Newsreader".
  {{IMG:nome}} -> caminho file:// de templates/recriados/_imagens/nome.jpg
Saída: <pasta>/png/<nome>.png e, com --ref, <pasta>/comparacao/<nome>.png (original | recriado).
"""
from __future__ import annotations
import argparse, json, re, subprocess, sys, tempfile
from pathlib import Path
from PIL import Image

RAIZ = Path(__file__).resolve().parents[3]
FONTES = RAIZ / "src/suno/pacote/fontes"
IMAGENS = RAIZ / "templates/recriados/_imagens"
RENDER = RAIZ / "render/render.mjs"
FACES = [("Anton", 400, "anton-latin-400-normal"), ("Poppins", 300, "poppins-latin-300-normal"),
         ("Poppins", 400, "poppins-latin-400-normal"), ("Poppins", 600, "poppins-latin-600-normal"),
         ("Poppins", 700, "poppins-latin-700-normal"), ("Inter", 400, "inter-latin-400-normal"),
         ("Inter", 500, "inter-latin-500-normal"), ("Inter", 600, "inter-latin-600-normal"),
         ("Inter", 700, "inter-latin-700-normal"), ("Newsreader", 400, "newsreader-latin-400-normal"),
         ("Newsreader", 600, "newsreader-latin-600-normal"), ("Newsreader", 700, "newsreader-latin-700-normal")]

def bloco_fontes() -> str:
    return "<style>" + "".join(
        f'@font-face{{font-family:"{f}";font-weight:{w};src:url("{(FONTES / (a + ".woff2")).as_uri()}")}}'
        for f, w, a in FACES) + "</style>"

def main() -> None:
    ap = argparse.ArgumentParser(); ap.add_argument("pasta"); ap.add_argument("--ref")
    a = ap.parse_args(); pasta = Path(a.pasta).resolve()
    htmls = sorted(pasta.glob("*.html")); (pasta / "png").mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        trabalho = []
        for h in htmls:
            t = h.read_text(encoding="utf-8").replace("{{FONTES}}", bloco_fontes())
            t = re.sub(r"\{\{IMG:([\w\-]+)\}\}", lambda m: (IMAGENS / f"{m.group(1)}.jpg").as_uri(), t)
            (Path(tmp) / h.name).write_text(t, encoding="utf-8")
            trabalho.append({"html": str(Path(tmp) / h.name), "png": str(pasta / "png" / f"{h.stem}.png"),
                             "json": str(Path(tmp) / f"{h.stem}.json")})
        (Path(tmp) / "t.json").write_text(json.dumps({"largura": 1080, "altura": 1350, "slides": trabalho}))
        r = subprocess.run(["node", str(RENDER), str(Path(tmp) / "t.json")], capture_output=True, text=True)
        if r.returncode: sys.exit(r.stderr)
    print(len(htmls), "renderizados em", pasta / "png")
    if a.ref:
        ref = Path(a.ref); (pasta / "comparacao").mkdir(exist_ok=True)
        for h in htmls:  # o HTML guarda "<!-- ref: arquivo.jpg -->" na primeira linha
            m = re.search(r"<!--\s*ref:\s*(\S+)\s*-->", h.read_text(encoding="utf-8"))
            if not m: continue
            o = Image.open(ref / m.group(1)).convert("RGB").resize((1080, 1350))
            n = Image.open(pasta / "png" / f"{h.stem}.png").convert("RGB")
            s = Image.new("RGB", (2180, 1350), (40, 40, 40)); s.paste(o, (0, 0)); s.paste(n, (1100, 0))
            s.save(pasta / "comparacao" / f"{h.stem}.png")
        print("comparações em", pasta / "comparacao")

if __name__ == "__main__":
    main()
