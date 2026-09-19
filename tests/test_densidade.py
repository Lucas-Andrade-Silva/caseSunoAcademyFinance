"""Casos obrigatórios do brief do Agente 2 (Etapa 1) para a Densidade. ADR 0012."""

from __future__ import annotations

from suno.avaliador.densidade import carregar_lexico, medir_densidade, termos_do_nucleo
from suno.dominio import ExigenciaDeExplicacao


def test_sempre_acusa_termo_sem_explicacao_mesmo_com_outro_explicado() -> None:
    # Caso 1: Selic vem explicada por parêntese; "hiato do produto" não vem explicada.
    texto = (
        "A Selic (a taxa básica que orienta o custo do crédito no país) caiu para "
        "14,00% ao ano nesta reunião. "
        "O hiato do produto ficou mais positivo neste trimestre."
    )
    resultado = medir_densidade(texto, ExigenciaDeExplicacao.SEMPRE)
    assert resultado.sem_explicacao == ["hiato do produto"]


def test_fora_do_nucleo_acusa_termo_fora_do_nucleo_mas_nao_termo_do_nucleo() -> None:
    # Caso 2, parte 1: mesmo texto do caso 1, agora com FORA_DO_NUCLEO — ainda acusa
    # "hiato do produto" (nucleo: false).
    texto = (
        "A Selic (a taxa básica que orienta o custo do crédito no país) caiu para "
        "14,00% ao ano nesta reunião. "
        "O hiato do produto ficou mais positivo neste trimestre."
    )
    resultado = medir_densidade(texto, ExigenciaDeExplicacao.FORA_DO_NUCLEO)
    assert "hiato do produto" in resultado.sem_explicacao

    # Caso 2, parte 2: Selic (núcleo) sem nenhuma explicação e FORA_DO_NUCLEO — não acusa
    # Selic, porque ela é núcleo.
    texto_sem_explicacao = "A Selic caiu para 14,00% ao ano nesta reunião do Copom."
    resultado_sem_explicacao = medir_densidade(texto_sem_explicacao, ExigenciaDeExplicacao.FORA_DO_NUCLEO)
    assert "Selic" not in resultado_sem_explicacao.sem_explicacao


def test_nunca_nao_acusa_nada_mesmo_sem_explicacao() -> None:
    # Caso 3: nenhum termo é explicado, mas a Exigência é NUNCA — lista sempre vazia.
    texto = "O Copom decidiu reduzir a Selic. O hiato do produto ficou mais positivo."
    resultado = medir_densidade(texto, ExigenciaDeExplicacao.NUNCA)
    assert resultado.sem_explicacao == []


def test_explicacao_na_frase_anterior_nao_vale_mas_na_seguinte_vale() -> None:
    # Caso 4, parte 1: a marca de explicação está numa frase ANTES do termo — não conta.
    texto_antes = (
        "Isso é uma boa notícia para quem acompanha o mercado. "
        "O hiato do produto ficou mais positivo neste trimestre."
    )
    resultado_antes = medir_densidade(texto_antes, ExigenciaDeExplicacao.SEMPRE)
    assert "hiato do produto" in resultado_antes.sem_explicacao

    # Caso 4, parte 2: a mesma marca, agora na frase SEGUINTE ao termo — conta.
    texto_depois = (
        "O hiato do produto ficou mais positivo neste trimestre. "
        "Isso é uma medida da diferença entre o produto efetivo e o potencial."
    )
    resultado_depois = medir_densidade(texto_depois, ExigenciaDeExplicacao.SEMPRE)
    assert "hiato do produto" not in resultado_depois.sem_explicacao


def test_segunda_ocorrencia_sem_explicacao_nao_acusa_se_primeira_foi_explicada() -> None:
    # Caso 5: primeira ocorrência de "Selic" vem com parêntese; a segunda, não. Não acusa.
    texto = (
        "A Selic (a taxa básica que orienta o custo do crédito no país) foi mantida "
        "nesta reunião. "
        "Depois da decisão, analistas voltaram a comentar a Selic em suas notas."
    )
    resultado = medir_densidade(texto, ExigenciaDeExplicacao.SEMPRE)
    assert "Selic" not in resultado.sem_explicacao
    ocorrencias_de_selic = [t for t in resultado.termos if t.termo == "Selic"]
    assert len(ocorrencias_de_selic) == 2
    assert ocorrencias_de_selic[0].explicado is True
    assert ocorrencias_de_selic[1].explicado is False


def test_limite_de_palavra_e_case_insensitive() -> None:
    # Caso 6: "reação" não casa com "ação"; "ações" casa com "ação"; SELIC/selic casam.
    texto = (
        "A reação do mercado às ações foi imediata, mas a aplicação de recursos não mudou. "
        "SELIC e selic devem contar como o mesmo termo."
    )
    resultado = medir_densidade(texto, ExigenciaDeExplicacao.NUNCA)
    nomes = [t.termo for t in resultado.termos]
    assert nomes.count("ação") == 1
    assert nomes.count("Selic") == 2


def test_termo_multi_palavra_conta_uma_vez() -> None:
    # Caso 7: "marcação a mercado" é um termo, não três palavras soltas.
    texto = "Os fundos praticam marcação a mercado diariamente, o que evita distorções."
    resultado = medir_densidade(texto, ExigenciaDeExplicacao.NUNCA)
    nomes = [t.termo for t in resultado.termos]
    assert nomes.count("marcação a mercado") == 1


def test_texto_sem_palavras_tem_proporcao_none() -> None:
    # Caso 8: nunca zero por falta de base.
    resultado = medir_densidade("   ", ExigenciaDeExplicacao.NUNCA)
    assert resultado.proporcao is None
    assert resultado.termos == []
    assert resultado.sem_explicacao == []


def test_paragrafo_real_da_ata_tem_proporcao_positiva_e_acusa_sob_sempre(texto_ata: str) -> None:
    # Caso 9: um parágrafo real da Ata do Copom (a decisão de política monetária).
    inicio = texto_ata.index("17. O Copom decidiu")
    fim = texto_ata.index("Tabela 1", inicio)
    paragrafo = texto_ata[inicio:fim]

    resultado = medir_densidade(paragrafo, ExigenciaDeExplicacao.SEMPRE)

    assert resultado.proporcao is not None
    assert resultado.proporcao > 0
    assert len(resultado.sem_explicacao) > 0


def test_lexico_carrega_com_pelo_menos_150_termos_bem_formados() -> None:
    # Caso 10: o Léxico carrega, tem >= 150 termos, todos com nucleo booleano e origem
    # preenchida, sem termos duplicados após normalização.
    termos = carregar_lexico()

    assert len(termos) >= 150
    for termo in termos:
        assert isinstance(termo.nucleo, bool)
        assert termo.origem

    nomes_normalizados = [termo.termo.strip().lower() for termo in termos]
    assert len(nomes_normalizados) == len(set(nomes_normalizados))

    nucleo = termos_do_nucleo()
    assert "Selic" in nucleo
    assert "CDI" in nucleo
    assert "hiato do produto" not in nucleo


def test_conjuncao_e_nao_e_confundida_com_a_copula_e() -> None:
    """Achado do revisor de erros (2026-09-19): sem acento, "é a"/"é o" (cópula) e "e a"/"e o"
    (conjunção "e" + artigo) viram a mesma string — quase toda frase com dois termos do
    Léxico marcava o primeiro como explicado só por causa do "e" que os liga."""
    resultado = medir_densidade("A Selic e o IPCA subiram em agosto.", ExigenciaDeExplicacao.SEMPRE)

    termo_selic = next(t for t in resultado.termos if t.termo == "Selic")
    assert termo_selic.explicado is False
    assert "Selic" in resultado.sem_explicacao


def test_verbo_sao_nao_e_confundido_com_o_toponimo_sao() -> None:
    """Mesma família de achado: "são" sem acento vira "sao", que também é o "São" de nome de
    cidade — mas aqui o ponto é mais simples ainda: nenhum termo do Léxico está sendo
    explicado, "são" é só o verbo "ser" no plural."""
    resultado = medir_densidade("Os juros sao altos.", ExigenciaDeExplicacao.SEMPRE)

    termo_juros = next(t for t in resultado.termos if t.termo == "juros")
    assert termo_juros.explicado is False


def test_copula_com_acento_continua_explicando_de_verdade() -> None:
    """O outro lado da correção: "é a" (com acento) continua funcionando como marca."""
    resultado = medir_densidade(
        "A Selic é a taxa básica de juros do país.", ExigenciaDeExplicacao.SEMPRE
    )

    termo_selic = next(t for t in resultado.termos if t.termo == "Selic")
    assert termo_selic.explicado is True
