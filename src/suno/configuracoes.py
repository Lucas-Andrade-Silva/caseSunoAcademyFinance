"""Configurações do sistema que a interface edita: o que liga e desliga, o teto de requisições por
minuto e qual provedor e modelo atende cada papel de LLM.

Valem na hora (cada chamada relê o arquivo quando ele muda) e sobrevivem à reinicialização. As chaves
de API ficam no ``.env``: a interface só diz se elas existem, nunca as lê nem as grava.

Precedência: o que a pessoa salvou aqui, depois o ``.env`` (``SUNO_JEV``, ``SUNO_FIDELIDADE``,
``SUNO_RPM``, ``GEMINI_MODELO``, ``GROQ_MODELO``, ``JEV_URL``, ``SUNO_JEV_LIMIAR``), depois o padrão
do código. Sem arquivo salvo, o comportamento é exatamente o do ``.env``.
"""

from __future__ import annotations

import json
import logging
import os
import threading
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from suno.dominio import RODADAS_MAXIMAS, PapelLLM

_REGISTRO = logging.getLogger(__name__)

VARIAVEL_DO_ARQUIVO = "SUNO_CONFIGURACOES"
ARQUIVO_PADRAO = Path("data/configuracoes.json")

NomeDoProvedor = Literal["gemini", "groq"]
PROVEDORES: tuple[str, ...] = ("gemini", "groq")

RPM_PADRAO = 8
RPM_MAXIMO = 600
RODADAS_PADRAO = 4

# Gemini gera (só ele aguenta a Ata inteira) e o Groq é a reserva. O checador de fidelidade e o prompt
# do vídeo gastam a cota do Groq primeiro. O juiz de visão precisa de imagem, então o Gemini vem à frente
# (ADR 0007, ADR 0036).
ORDEM_PADRAO: dict[PapelLLM, tuple[str, ...]] = {
    PapelLLM.GERADOR: ("gemini", "groq"),
    PapelLLM.JUIZ_VISAO: ("gemini", "groq"),
    PapelLLM.CHECADOR: ("groq", "gemini"),
    PapelLLM.DIRETOR_ARTE: ("gemini", "groq"),
    PapelLLM.ANALISTA_VISUAL: ("gemini", "groq"),
    PapelLLM.VIDEO: ("groq", "gemini"),
}

CHAVES_DE_API: dict[str, tuple[str, ...]] = {
    "gemini": ("GEMINI_API_KEY",),
    "groq": ("GROQ_API_KEY",),
    "jev": ("JEV_API_KEY", "TYPESAFE_API_KEY"),
}

MODELOS_SUGERIDOS: dict[str, tuple[str, ...]] = {
    "gemini": ("gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-2.5-pro"),
    "groq": ("openai/gpt-oss-120b", "openai/gpt-oss-20b", "llama-3.3-70b-versatile"),
}

_VARIAVEL_DO_MODELO = {"gemini": "GEMINI_MODELO", "groq": "GROQ_MODELO"}


class EntradaDeProvedor(BaseModel):
    """Um provedor da fila de um papel. ``modelo`` vazio usa o modelo padrão do provedor."""

    model_config = ConfigDict(frozen=True)

    provedor: NomeDoProvedor
    modelo: str = Field(default="", max_length=100)

    @field_validator("modelo")
    @classmethod
    def _modelo_sem_espaco(cls, valor: str) -> str:
        valor = valor.strip()
        if any(c.isspace() for c in valor):
            raise ValueError("o nome do modelo não tem espaço")
        return valor


class ConfiguracoesDoSistema(BaseModel):
    model_config = ConfigDict(frozen=True)

    jev_ligado: bool
    """A Qualidade pelo Jev (ADR 0035). Ligado, ela roda em toda Célula que passou no determinístico."""
    jev_url: str = ""
    """Endereço do ``systemone`` (a Netlify Function). Vazio usa o da TypeSafe. Só https."""
    jev_limiar: float | None = Field(default=None, ge=0.0, le=1.0)
    """Nota mínima de cada dimensão, de 0 a 1. ``None`` usa o padrão do código."""
    fidelidade_ligada: bool
    """O checador de fidelidade à Ata (ADR 0036): um LLM confere a Célula contra a Ata."""
    requisicoes_por_minuto: int = Field(ge=0, le=RPM_MAXIMO)
    """Teto de requisições por minuto aos LLMs, somando os provedores. ``0`` não limita."""
    rodadas_de_correcao: int = Field(ge=0, le=RODADAS_MAXIMAS)
    """Quantas vezes o Ciclo regenera e reavalia uma Célula reprovada (depois da geração original). O
    determinístico roda de novo a cada rodada; o Jev e o checador só rodam quando ele aprova."""
    modelo_padrao: dict[NomeDoProvedor, str]
    """O modelo de cada provedor quando o papel não escolhe o seu."""
    papeis: dict[PapelLLM, list[EntradaDeProvedor]]
    """Para cada papel, a fila de provedores (de um a dois) e o modelo de cada um."""

    @field_validator("jev_url")
    @classmethod
    def _url_https(cls, valor: str) -> str:
        valor = valor.strip()
        if valor and not valor.lower().startswith("https://"):
            raise ValueError("o endereço do Jev precisa começar com https://")
        return valor

    @field_validator("modelo_padrao")
    @classmethod
    def _modelos_padrao(cls, valor: dict[str, str]) -> dict[str, str]:
        limpo: dict[str, str] = {}
        for provedor, modelo in valor.items():
            modelo = modelo.strip()
            if len(modelo) > 100 or any(c.isspace() for c in modelo):
                raise ValueError(f"modelo inválido para {provedor}")
            limpo[provedor] = modelo
        return limpo

    @model_validator(mode="after")
    def _filas_validas(self) -> "ConfiguracoesDoSistema":
        for papel in PapelLLM:
            fila = self.papeis.get(papel)
            if not fila:
                raise ValueError(f"o papel {papel.value} precisa de ao menos um provedor")
            if len(fila) > len(PROVEDORES):
                raise ValueError(f"o papel {papel.value} aceita no máximo {len(PROVEDORES)} provedores")
            nomes = [entrada.provedor for entrada in fila]
            if len(set(nomes)) != len(nomes):
                raise ValueError(f"o papel {papel.value} repete o provedor")
        return self

    def fila_do_papel(self, papel: PapelLLM) -> list[EntradaDeProvedor]:
        return self.papeis.get(papel) or [EntradaDeProvedor(provedor=p) for p in ORDEM_PADRAO[papel]]

    def modelo_de(self, provedor: str, entrada: EntradaDeProvedor | None = None) -> str:
        """O modelo do papel, ou o padrão do provedor quando o papel deixa em branco."""
        if entrada is not None and entrada.modelo:
            return entrada.modelo
        return self.modelo_padrao.get(provedor, "")  # type: ignore[call-overload]


# ---------------------------------------------------------------------------
# Padrão: o que o .env e o código dizem quando nada foi salvo
# ---------------------------------------------------------------------------


def _inteiro(bruto: str, padrao: int, maximo: int = RPM_MAXIMO) -> int:
    try:
        return max(0, min(maximo, int(bruto.strip()))) if bruto.strip() else padrao
    except ValueError:
        return padrao


def _decimal(bruto: str) -> float | None:
    bruto = bruto.strip().replace(",", ".")
    if not bruto:
        return None
    try:
        valor = float(bruto)
    except ValueError:
        return None
    return valor if 0.0 <= valor <= 1.0 else None


def padrao() -> ConfiguracoesDoSistema:
    ambiente = os.environ
    url = ambiente.get("JEV_URL", "").strip()
    return ConfiguracoesDoSistema(
        jev_ligado=ambiente.get("SUNO_JEV", "1").strip() != "0",
        jev_url=url if url.lower().startswith("https://") else "",
        jev_limiar=_decimal(ambiente.get("SUNO_JEV_LIMIAR", "")),
        fidelidade_ligada=ambiente.get("SUNO_FIDELIDADE", "1").strip() != "0",
        requisicoes_por_minuto=_inteiro(ambiente.get("SUNO_RPM", ""), RPM_PADRAO),
        rodadas_de_correcao=_inteiro(ambiente.get("SUNO_RODADAS", ""), RODADAS_PADRAO, RODADAS_MAXIMAS),
        modelo_padrao={p: ambiente.get(_VARIAVEL_DO_MODELO[p], "").strip() for p in PROVEDORES},  # type: ignore[misc]
        papeis={
            papel: [EntradaDeProvedor(provedor=p) for p in ordem]  # type: ignore[arg-type]
            for papel, ordem in ORDEM_PADRAO.items()
        },
    )


# ---------------------------------------------------------------------------
# Arquivo
# ---------------------------------------------------------------------------

_trava = threading.Lock()
_memoria: tuple[Path, int, ConfiguracoesDoSistema] | None = None


def caminho_do_arquivo() -> Path:
    return Path(os.environ.get(VARIAVEL_DO_ARQUIVO, "") or ARQUIVO_PADRAO)


def carregar() -> ConfiguracoesDoSistema:
    """O que vale agora. Relê o arquivo só quando ele muda; sem arquivo, vale o padrão do ambiente."""
    global _memoria
    caminho = caminho_do_arquivo()
    try:
        estado = caminho.stat()
    except OSError:
        return padrao()
    assinatura = estado.st_mtime_ns
    with _trava:
        if _memoria is not None and _memoria[0] == caminho and _memoria[1] == assinatura:
            return _memoria[2]
    try:
        salvo = json.loads(caminho.read_text(encoding="utf-8"))
        fundido = padrao().model_dump(mode="json")
        for campo, valor in salvo.items():
            if campo == "papeis" and isinstance(valor, dict):
                fundido["papeis"].update(valor)
            elif campo == "modelo_padrao" and isinstance(valor, dict):
                fundido["modelo_padrao"].update(valor)
            else:
                fundido[campo] = valor
        configuracoes = ConfiguracoesDoSistema.model_validate(fundido)
    except (OSError, ValueError) as erro:
        _REGISTRO.warning("configuracoes.json ilegível, valendo o padrão do ambiente: %s", erro)
        return padrao()
    with _trava:
        _memoria = (caminho, assinatura, configuracoes)
    return configuracoes


def salvar(configuracoes: ConfiguracoesDoSistema) -> ConfiguracoesDoSistema:
    caminho = caminho_do_arquivo()
    caminho.parent.mkdir(parents=True, exist_ok=True)
    provisorio = caminho.with_suffix(caminho.suffix + ".tmp")
    provisorio.write_text(configuracoes.model_dump_json(indent=2), encoding="utf-8")
    os.replace(provisorio, caminho)
    return carregar()


def restaurar() -> ConfiguracoesDoSistema:
    """Apaga o que foi salvo: volta a valer o ``.env``."""
    try:
        caminho_do_arquivo().unlink()
    except FileNotFoundError:
        pass
    return carregar()


def chaves_presentes() -> dict[str, bool]:
    """Quais chaves existem no ambiente. Nunca o valor."""
    return {nome: any(os.environ.get(v, "").strip() for v in variaveis) for nome, variaveis in CHAVES_DE_API.items()}
