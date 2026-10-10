"""Gera os seis PNGs do carrossel pela API de imagem do Gemini."""

from __future__ import annotations

import argparse
import base64
import io
import json
import os
import time
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv
from PIL import Image, ImageDraw


ESPERA_POR_STATUS_S = {429: 90, 500: 30, 502: 30, 503: 60, 504: 30}
INTERVALO_ENTRE_SUCESSOS_S = 40


def _argumentos() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prompts", required=True, type=Path)
    return parser.parse_args()


def _imagem_da_resposta(corpo: dict[str, Any]) -> tuple[bytes, str]:
    candidatos = corpo.get("candidates") or []
    if not candidatos:
        raise RuntimeError(f"Gemini não devolveu candidato: {json.dumps(corpo, ensure_ascii=False)[:1000]}")
    partes = candidatos[0].get("content", {}).get("parts", [])
    for parte in partes:
        inline = parte.get("inlineData") or parte.get("inline_data")
        if inline and inline.get("data"):
            return base64.b64decode(inline["data"]), inline.get("mimeType", "image/png")
    raise RuntimeError(f"Gemini não devolveu imagem: {json.dumps(corpo, ensure_ascii=False)[:1000]}")


def _pedir(
    cliente: httpx.Client,
    *,
    chave: str,
    modelo: str,
    prompt: str,
    proporcao: str,
    resolucao: str,
    referencia: bytes | None,
) -> tuple[bytes, str]:
    partes: list[dict[str, Any]] = []
    if referencia is not None:
        partes.extend(
            [
                {
                    "text": (
                        "A imagem anexada é somente referência de identidade visual do slide 01. "
                        "Preserve paleta, tipografia, textura, iluminação, margens e linha vermelha, "
                        "mas crie a composição nova descrita depois."
                    )
                },
                {
                    "inlineData": {
                        "mimeType": "image/png",
                        "data": base64.b64encode(referencia).decode("ascii"),
                    }
                },
            ]
        )
    partes.append({"text": prompt})
    payload = {
        "contents": [{"role": "user", "parts": partes}],
        "generationConfig": {
            "responseModalities": ["IMAGE"],
            "imageConfig": {"aspectRatio": proporcao, "imageSize": resolucao},
        },
    }
    url = f"https://generativelanguage.googleapis.com/v1/models/{modelo}:generateContent"
    for tentativa in range(2):
        resposta = cliente.post(url, headers={"x-goog-api-key": chave}, json=payload)
        if resposta.status_code < 400:
            return _imagem_da_resposta(resposta.json())
        espera = ESPERA_POR_STATUS_S.get(resposta.status_code)
        if espera is None or tentativa == 1:
            resposta.raise_for_status()
        print(f"  HTTP {resposta.status_code}; nova tentativa em {espera}s", flush=True)
        time.sleep(espera)
    raise RuntimeError("tentativas esgotadas")


def _salvar_png(dados: bytes, destino: Path) -> None:
    with Image.open(io.BytesIO(dados)) as imagem:
        imagem.convert("RGB").save(destino, "PNG", optimize=True)


def _folha_de_contato(arquivos: list[Path], destino: Path) -> None:
    miniaturas: list[Image.Image] = []
    for arquivo in arquivos:
        with Image.open(arquivo) as imagem:
            miniaturas.append(imagem.convert("RGB").resize((324, 405), Image.Resampling.LANCZOS))
    folha = Image.new("RGB", (1012, 842), "#090909")
    desenho = ImageDraw.Draw(folha)
    for indice, miniatura in enumerate(miniaturas):
        x = 16 + (indice % 3) * 332
        y = 16 + (indice // 3) * 413
        folha.paste(miniatura, (x, y))
        desenho.rectangle((x - 1, y - 1, x + 324, y + 405), outline="#E3262E", width=1)
    folha.save(destino, "PNG", optimize=True)


def main() -> int:
    args = _argumentos()
    load_dotenv()
    chave = os.environ.get("GEMINI_API_KEY", "")
    if not chave:
        raise SystemExit("GEMINI_API_KEY ausente no .env")
    especificacao = json.loads(args.prompts.read_text(encoding="utf-8"))
    saida = args.prompts.parent
    modelo = especificacao["modelo"]
    compartilhada = especificacao["direcao_compartilhada"]
    referencia: bytes | None = None
    gerados: list[Path] = []
    manifesto: list[dict[str, Any]] = []
    with httpx.Client(timeout=180.0) as cliente:
        for indice, slide in enumerate(especificacao["slides"], start=1):
            destino = saida / slide["arquivo"]
            if destino.exists():
                print(f"slide {indice}/6: já existe; pulando", flush=True)
                dados_png = destino.read_bytes()
                if referencia is None:
                    referencia = dados_png
                gerados.append(destino)
                manifesto.append({"slide": indice, "arquivo": destino.name, "retomado": True})
                continue
            print(f"slide {indice}/6: enviando para {modelo}", flush=True)
            prompt = f"{compartilhada}\n\n{slide['briefing']}"
            dados, mime = _pedir(
                cliente,
                chave=chave,
                modelo=modelo,
                prompt=prompt,
                proporcao=especificacao["proporcao"],
                resolucao=especificacao["resolucao"],
                referencia=referencia,
            )
            _salvar_png(dados, destino)
            dados_png = destino.read_bytes()
            if referencia is None:
                referencia = dados_png
            gerados.append(destino)
            manifesto.append({"slide": indice, "arquivo": destino.name, "mime_original": mime})
            print(f"slide {indice}/6: salvo em {destino}", flush=True)
            if indice < len(especificacao["slides"]):
                print(f"  aguardando {INTERVALO_ENTRE_SUCESSOS_S}s para proteger a cota", flush=True)
                time.sleep(INTERVALO_ENTRE_SUCESSOS_S)
    _folha_de_contato(gerados, saida / "folha-de-contato.png")
    (saida / "manifesto.json").write_text(
        json.dumps({"modelo": modelo, "imagens": manifesto}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"carrossel concluído: {saida}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
