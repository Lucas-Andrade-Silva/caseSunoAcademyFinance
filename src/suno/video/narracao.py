"""A narração opcional do vídeo: ``edge-tts``, voz pt-BR. Nunca roda em teste e nunca no
caminho crítico da demo — falha de rede é o caso normal, não a exceção (ADR 0004).

Pesquisa (viabilidade-tecnica.md §6): ``edge-tts`` fala com um endpoint não documentado da
Microsoft, sem contrato de nível de serviço. Isso é aceitável aqui porque a narração é a
primeira coisa que cai na ordem de corte do CLAUDE.md se o prazo apertar (item 3: "Avatar
falante → vídeo sem rosto" já cortou o rosto; a voz é a próxima camada, não a Célula em si) —
e porque ``renderizar_video`` sem narração já produz um vídeo completo, só sem trilha.
"""

from __future__ import annotations

from pathlib import Path

VOZ_PADRAO = "pt-BR-FranciscaNeural"
"""Uma das duas vozes pt-BR do Edge TTS; feminina, neural. A escolha não afeta o Avaliador
— a fala já foi julgada como texto, antes de qualquer síntese existir (ADR 0004)."""


def sintetizar(texto: str, destino: Path) -> Path | None:
    """Sintetiza ``texto`` em pt-BR e grava em ``destino``. Devolve ``None`` — nunca levanta —
    se a rede falhar, se o pacote ``edge-tts`` não estiver instalado ou se a síntese vier
    vazia: o vídeo sai sem trilha e ``medir_video`` acusa ``SEM_AUDIO`` honestamente, em vez
    de uma trilha de silêncio fingindo que há narração (ADR 0014).
    """
    if not texto.strip():
        return None
    try:
        import edge_tts
    except ImportError:
        return None
    try:
        destino.parent.mkdir(parents=True, exist_ok=True)
        edge_tts.Communicate(texto, VOZ_PADRAO).save_sync(str(destino))
    except Exception:
        return None
    if not destino.exists() or destino.stat().st_size == 0:
        return None
    return destino
