# Front do Suno Content, Fases 0 e 1: casca nova e revisão do que já existe

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Trocar o front por um painel escuro (preto e vermelho da Suno) com as guias Fontes, Curadoria e Saídas, e deixar a equipe revisar o que já foi gerado: abrir uma Saída, ler uma Célula, aprovar ou reprovar, renomear e exportar.

**Architecture:** Evolui o que existe (React + Vite + Tailwind sobre FastAPI, estado em arquivos no disco). O backend ganha `nome` e `decisoes` no `Execucao`, a regra de decisão humana em `src/suno/revisao.py`, a exportação em `src/suno/exportacao.py` e cinco rotas. O front troca as páginas por Saídas, Saída aberta e Célula aberta, sobre tokens de cor próprios. A lógica pura do front fica em `web/src/lib/matriz.ts`, coberta por Vitest.

**Tech Stack:** Python 3.12, FastAPI, Pydantic v2, pytest · React 19, Vite 8, Tailwind 4, TypeScript 5.9, openapi-fetch, Vitest (novo).

**Spec:** `docs/superpowers/specs/2026-10-09-front-suno-design.md` (seções 4, 5, 6.2, 6.3, 6.6, 6.7 e fases 0 e 1). Mockups em `docs/superpowers/specs/mockups-2026-10-09/`: `05-saidas-lista.html`, `02-saida-aberta.html` (opção A), `03-celula-aberta.html` (opção B).

## Global Constraints

Valem para todas as tarefas.

- **Não commitar.** O usuário não pediu commit. Onde a skill pede commit, este plano põe um **Checkpoint** (rodar testes e olhar o `git status`). `src/suno/dominio.py`, `src/suno/gerador/execucao.py`, `tests/test_execucao.py` e outros arquivos têm alterações da equipe **não commitadas**: um `git add` desses arquivos misturaria trabalho alheio. Este plano só **acrescenta** a `dominio.py` e não toca em `execucao.py`, `matriz.py`, `avaliador/`, `README.md` nem `docs/ARQUITETURA.md`.
- **Linha de base antes de começar:** `uv run pytest -q` dá `837 passed`; `npx tsc --noEmit -p tsconfig.app.json` (em `web/`) sai limpo; `uv run python scripts/vocabulario.py` já acusa 16 achados, todos do trabalho da equipe (anote o número na Tarefa 1).
- **Vocabulário** ([CONTEXT.md](../../../CONTEXT.md), `scripts/vocabulario.py`): nenhum identificador novo (classe, função, parâmetro, variável, campo, nome de arquivo, em Python ou TypeScript) pode conter palavra da lista _Avoid_. Palavras que mais tentam entrar: `painel`, `item`, `tipo`, `fonte`, `documento`, `grade`, `tabela`, `export`, `versao`, `meta`, `corte`, `estilo`, `post`, `entrega`, `score`, `avaliacao`, `persona`, `retry`, `canal`, `nivel`, `baseline`. Os nomes deste plano já respeitam isso: não os "melhore" para um sinônimo da lista.
- **Rótulos de tela em pt-BR, com acento.** "Saída" é só rótulo de tela; no código continua `Execucao`. A curadoria nunca se chama "Recomendação" (palavra proibida).
- **Tema só escuro.** Nada de variante `dark:` do Tailwind. Tokens exatos: fundo `#0e0e0f`, menu lateral `#141415`, cartão `#1c1c1e`, cartão 2 `#242427`, linha `#2c2c30`, texto `#f3f3f4`, texto suave `#8d8d93`, vermelho Suno `#ef4b3f`, ok `#3ecf8e`, alerta `#f5b042`. O vermelho foi estimado de uma captura de tela; o hex oficial substitui depois.
- **Nada de API aberta `/v1`, chaves de API, guia API.** Foi adiada pelo usuário.
- **A regra "Compliance bloqueia" é do servidor.** Célula cujo Laudo final tem `MotivoReprovacao.RECOMENDACAO` não pode ser aprovada: a rota responde 409. A tela só reflete.
- **Rotas existentes não mudam de nome nem de comportamento** (`/api/execucoes/...`). Só se acrescenta.
- **Testes offline.** A trava de rede de `tests/conftest.py` vale para tudo. `TestClient` usa transporte em processo.
- **Todo acesso à API do front passa por `web/src/dados/cliente.ts`.** Nenhum outro arquivo chama `fetch`.
- **Todo caminho abaixo é relativo à raiz do repositório.** No Bash, rode comandos a partir da raiz e use `cd web && ...` só dentro da mesma linha. Use caminhos absolutos ao ler e escrever arquivos.

---

## Estrutura de arquivos

**Backend**

| Arquivo | Responsabilidade |
|---|---|
| `src/suno/dominio.py` (modificar) | `EstadoDecisao`, `DecisaoHumana`, `Execucao.nome`, `Execucao.decisoes`, `Execucao.decisao_de`. |
| `src/suno/revisao.py` (criar) | `decidir`, `celula_bloqueada` e as três exceções. A regra da linha que não se cruza. |
| `src/suno/exportacao.py` (criar) | `FormatoExportacao` e `exportar`: JSON, Markdown e ZIP de uma Saída. |
| `src/suno/api/resumo.py` (criar) | `PosicaoResumo`, `StatusSaida`, `montar_posicoes`, `status_da_saida`. |
| `src/suno/api/app.py` (modificar) | `ExecucaoResumo` ampliado; rotas `resumo`, renomear, decisão e exportar; fallback de SPA. |
| `tests/construtores_de_execucao.py` (criar) | Construtores pequenos de `Execucao` usados por vários testes. |
| `tests/test_decisao_humana.py`, `tests/test_revisao.py`, `tests/test_exportacao.py`, `tests/test_resumo.py`, `tests/test_contrato_openapi.py` (criar) | Um arquivo por módulo novo. |
| `tests/test_api.py` (modificar, só acrescentar no fim) | Rotas novas. |
| `web/openapi.json`, `web/src/api/schema.d.ts` (regerar) | Contrato. |

**Front** (`web/`)

| Arquivo | Responsabilidade |
|---|---|
| `package.json`, `vite.config.ts`, `index.html` (modificar) | Vitest, cores do manifesto PWA. |
| `src/estilos/global.css` (reescrever) | Tokens `@theme`, tema escuro. |
| `src/lib/matriz.ts` + `matriz.test.ts` (criar) | Lógica pura: estado e chips de uma posição, contagens, filtro, ordem, barra do Laudo, vizinhas. |
| `src/lib/revisor.ts` (criar) | Nome do revisor guardado no navegador. |
| `src/dados/cliente.ts`, `src/texto/rotulos.ts` (modificar) | Rotas novas e rótulos novos. |
| `src/componentes/` | `Chip`, `MiniMatriz`, `CartaoSaida`, `MenuDoCartao`, `LinksDeExportacao`, `CelulaDaMatriz`, `ConteudoCelula`, `SecaoLaudo`, `SecaoAncoras`, `SecaoPacote`, `BarraDecisao`, `EmConstrucao` (criar); `EstadoRequisicao`, `VereditoCartao`, `Reprovacao`, `Ancoras`, `Layout` (reescrever no tema escuro). |
| `src/paginas/` | `Saidas`, `SaidaAberta`, `CelulaAberta`, `Fontes`, `Curadoria` (criar); `Execucoes`, `Matriz`, `CelulaVista`, `Filas`, `Pacotes` (remover). |
| `src/App.tsx` (modificar) | Rotas novas. |

**Docs:** `docs/adr/0017-api-dispara-a-geracao-em-segundo-plano.md` (criar), `CONTEXT.md` e `web/README.md` (modificar).

---

## Task 1: Domínio: nome e decisão humana

**Files:**
- Modify: `src/suno/dominio.py` (três acréscimos, nenhuma linha existente muda)
- Create: `tests/construtores_de_execucao.py`
- Create: `tests/test_decisao_humana.py`

**Interfaces:**
- Produces: `EstadoDecisao` (`APROVADA="aprovada"`, `REPROVADA="reprovada"`); `DecisaoHumana(audiencia, formato, estado, motivo: str | None, revisor: str | None, em: datetime)`; `Execucao.nome: str` (vazio vira o `identificador`); `Execucao.decisoes: list[DecisaoHumana]`; `Execucao.decisao_de(audiencia, formato) -> DecisaoHumana | None`; nos testes, `historico_de_texto(audiencia, destino, motivos=())` e `execucao_de_teste(*historicos, nome="", pendencias=())`, com `IDENTIFICADOR = "exec-teste"`.

- [ ] **Step 1: Anotar a linha de base do vocabulário**

Run: `uv run python scripts/vocabulario.py | tail -1`
Expected: `16 achado(s); 67 palavras a evitar`. Anote o primeiro número. Todas as tarefas devem terminar com o mesmo número.

- [ ] **Step 2: Criar os construtores de teste**

Create `tests/construtores_de_execucao.py`:

```python
"""Construtores pequenos de Execução para os testes da revisão humana e da exportação.

Só Texto analítico, que não pede slides nem blocos: o que importa aqui é o destino do Laudo
e os motivos, não o conteúdo.
"""

from __future__ import annotations

from datetime import datetime, timezone

from suno.dominio import (
    Ancoras,
    Audiencia,
    Celula,
    Conteudo,
    Destino,
    Execucao,
    Formato,
    HistoricoCelula,
    Laudo,
    Medida,
    Metrica,
    MotivoReprovacao,
    Pendencia,
    Tentativa,
)

IDENTIFICADOR = "exec-teste"
ATA = "copom-280-2026-08-05"


def historico_de_texto(
    audiencia: Audiencia,
    destino: Destino,
    motivos: tuple[MotivoReprovacao, ...] = (),
) -> HistoricoCelula:
    """Uma posição Audiência × Texto analítico, com uma tentativa e o destino pedido."""
    formato = Formato.TEXTO_ANALITICO
    celula = Celula(
        audiencia=audiencia,
        formato=formato,
        conteudo=Conteudo(formato=formato, texto=f"Texto de teste para {audiencia.value}."),
    )
    laudo = Laudo(
        audiencia=audiencia,
        formato=formato,
        medidas=[
            Medida(metrica=Metrica.ADERENCIA, valor=1.0, atingiu=destino is Destino.APROVADO)
        ],
        destino=destino,
        motivos=list(motivos),
    )
    return HistoricoCelula(
        audiencia=audiencia,
        formato=formato,
        tentativas=[Tentativa(rodada=0, celula=celula, laudo=laudo)],
        destino_final=destino,
    )


def execucao_de_teste(
    *historicos: HistoricoCelula,
    nome: str = "",
    pendencias: tuple[Pendencia, ...] = (),
) -> Execucao:
    return Execucao(
        identificador=IDENTIFICADOR,
        nome=nome,
        ata=ATA,
        provedor_gerador="falso",
        iniciada_em=datetime(2026, 10, 9, 12, 0, tzinfo=timezone.utc),
        ancoras=Ancoras(ata=ATA),
        celulas=list(historicos),
        pendencias=list(pendencias),
    )
```

- [ ] **Step 3: Escrever os testes que falham**

Create `tests/test_decisao_humana.py`:

```python
"""O nome da Saída e a decisão humana no domínio: valores padrão, validação e compatibilidade
com execucao.json gravado antes do front novo."""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from suno.dominio import Audiencia, DecisaoHumana, Destino, EstadoDecisao, Execucao, Formato
from tests.construtores_de_execucao import IDENTIFICADOR, execucao_de_teste, historico_de_texto


def test_nome_vazio_vira_o_identificador() -> None:
    assert execucao_de_teste().nome == IDENTIFICADOR


def test_nome_dado_pelo_usuario_e_preservado() -> None:
    assert execucao_de_teste(nome="Copom 280 · pauta juros").nome == "Copom 280 · pauta juros"


def test_execucao_gravada_antes_do_front_novo_continua_carregando() -> None:
    dados = json.loads(execucao_de_teste().model_dump_json())
    del dados["nome"]
    del dados["decisoes"]

    reconstruida = Execucao.model_validate(dados)

    assert reconstruida.nome == IDENTIFICADOR
    assert reconstruida.decisoes == []


def test_decisao_reprovada_exige_motivo() -> None:
    with pytest.raises(ValidationError, match="motivo"):
        DecisaoHumana(
            audiencia=Audiencia.INICIANTE,
            formato=Formato.TEXTO_ANALITICO,
            estado=EstadoDecisao.REPROVADA,
            motivo="   ",
        )


def test_decisao_aprovada_nao_exige_motivo() -> None:
    decisao = DecisaoHumana(
        audiencia=Audiencia.INICIANTE,
        formato=Formato.TEXTO_ANALITICO,
        estado=EstadoDecisao.APROVADA,
    )
    assert decisao.motivo is None
    assert decisao.revisor is None


def test_decisao_de_acha_a_decisao_da_posicao() -> None:
    execucao = execucao_de_teste(historico_de_texto(Audiencia.INICIANTE, Destino.APROVADO))
    decisao = DecisaoHumana(
        audiencia=Audiencia.INICIANTE,
        formato=Formato.TEXTO_ANALITICO,
        estado=EstadoDecisao.APROVADA,
    )
    execucao.decisoes.append(decisao)

    assert execucao.decisao_de(Audiencia.INICIANTE, Formato.TEXTO_ANALITICO) is decisao
    assert execucao.decisao_de(Audiencia.AVANCADO, Formato.TEXTO_ANALITICO) is None
```

- [ ] **Step 4: Rodar e ver falhar**

Run: `uv run pytest tests/test_decisao_humana.py -q`
Expected: erro de importação (`cannot import name 'DecisaoHumana'` ou `EstadoDecisao` de `suno.dominio`).

- [ ] **Step 5: Acrescentar `EstadoDecisao` e `DecisaoHumana` ao domínio**

Em `src/suno/dominio.py`, use Edit com este `old_string` (é único) e o `new_string` abaixo dele.

`old_string`:

```python
    resolvida: bool = False
    decisao: str | None = None


class Custo(BaseModel):
```

`new_string`:

```python
    resolvida: bool = False
    decisao: str | None = None


class EstadoDecisao(StrEnum):
    """O que um humano decidiu sobre uma Célula."""

    APROVADA = "aprovada"
    REPROVADA = "reprovada"


class DecisaoHumana(BaseModel):
    """A decisão de um revisor sobre uma Célula. Sem registro, a Célula está pendente."""

    audiencia: Audiencia
    formato: Formato
    estado: EstadoDecisao
    motivo: str | None = Field(default=None, description="Obrigatório quando reprovada.")
    revisor: str | None = None
    em: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @model_validator(mode="after")
    def _reprovada_exige_motivo(self) -> DecisaoHumana:
        if self.estado is EstadoDecisao.REPROVADA and not (self.motivo or "").strip():
            raise ValueError("reprovar exige motivo")
        return self


class Custo(BaseModel):
```

- [ ] **Step 6: Acrescentar `nome`, `decisoes` e `decisao_de` ao `Execucao`**

Edit 1, em `src/suno/dominio.py`. `old_string`:

```python
        description="Ciclo do LLM Judge e correções; ausente apenas em execuções antigas.",
    )

    def historico(self, audiencia: Audiencia, formato: Formato) -> HistoricoCelula | None:
```

`new_string`:

```python
        description="Ciclo do LLM Judge e correções; ausente apenas em execuções antigas.",
    )
    nome: str = Field(
        default="",
        description="Nome dado pelo usuário à Saída; vazio vira o identificador.",
    )
    decisoes: list[DecisaoHumana] = Field(
        default_factory=list,
        description="Decisões humanas por Célula; posição sem registro está pendente.",
    )

    @model_validator(mode="after")
    def _nome_padrao(self) -> Execucao:
        if not self.nome.strip():
            self.nome = self.identificador
        return self

    def historico(self, audiencia: Audiencia, formato: Formato) -> HistoricoCelula | None:
```

Edit 2, no mesmo arquivo. `old_string`:

```python
                return h
        return None

    def contagem_por_motivo(self) -> dict[MotivoReprovacao, int]:
```

`new_string`:

```python
                return h
        return None

    def decisao_de(self, audiencia: Audiencia, formato: Formato) -> DecisaoHumana | None:
        for decisao in self.decisoes:
            if decisao.audiencia is audiencia and decisao.formato is formato:
                return decisao
        return None

    def contagem_por_motivo(self) -> dict[MotivoReprovacao, int]:
```

- [ ] **Step 7: Rodar e ver passar**

Run: `uv run pytest tests/test_decisao_humana.py -q`
Expected: `6 passed`.

- [ ] **Step 8: Checkpoint**

Run: `uv run pytest -q -x`
Expected: `843 passed` (837 + 6), 0 failed. Depois `uv run python scripts/vocabulario.py | tail -1` deve repetir o número anotado no Step 1. Não commite.

---

## Task 2: A regra da decisão humana (`revisao.py`)

**Files:**
- Create: `src/suno/revisao.py`
- Create: `tests/test_revisao.py`

**Interfaces:**
- Consumes: de `suno.dominio`: `DecisaoHumana`, `EstadoDecisao`, `Execucao`, `HistoricoCelula`, `MotivoReprovacao`, `Destino`, `FilaHumana`; de `tests.construtores_de_execucao`: `historico_de_texto`, `execucao_de_teste`.
- Produces: `celula_bloqueada(historico: HistoricoCelula) -> bool`; `decidir(execucao: Execucao, audiencia: Audiencia, formato: Formato, estado: EstadoDecisao, *, motivo: str | None = None, revisor: str | None = None) -> DecisaoHumana` (muda `execucao.decisoes` e resolve a Pendência H4 da posição); exceções `CelulaNaoEncontrada(LookupError)`, `DecisaoInvalida(ValueError)`, `DecisaoBloqueada(Exception)`.

- [ ] **Step 1: Escrever os testes que falham**

Create `tests/test_revisao.py`:

```python
"""A decisão humana sobre uma Célula, e a linha que ninguém cruza.

Compliance é métrica do Laudo (CLAUDE.md): a Célula cujo Laudo final tem Recomendação não
pode ser aprovada por rota nenhuma. Tudo aqui roda sem rede e sem LLM.
"""

from __future__ import annotations

import pytest

from suno.dominio import (
    Audiencia,
    Destino,
    EstadoDecisao,
    FilaHumana,
    Formato,
    HistoricoCelula,
    MotivoReprovacao,
    Pendencia,
)
from suno.revisao import (
    CelulaNaoEncontrada,
    DecisaoBloqueada,
    DecisaoInvalida,
    celula_bloqueada,
    decidir,
)
from tests.construtores_de_execucao import execucao_de_teste, historico_de_texto

TEXTO = Formato.TEXTO_ANALITICO


def test_aprovar_celula_aprovada_pelo_laudo_registra_a_decisao() -> None:
    execucao = execucao_de_teste(historico_de_texto(Audiencia.INICIANTE, Destino.APROVADO))

    decisao = decidir(execucao, Audiencia.INICIANTE, TEXTO, EstadoDecisao.APROVADA, revisor=" Ana ")

    assert decisao.estado is EstadoDecisao.APROVADA
    assert decisao.revisor == "Ana"
    assert execucao.decisao_de(Audiencia.INICIANTE, TEXTO) is decisao


def test_reprovar_exige_motivo() -> None:
    execucao = execucao_de_teste(historico_de_texto(Audiencia.INICIANTE, Destino.APROVADO))

    with pytest.raises(DecisaoInvalida, match="motivo"):
        decidir(execucao, Audiencia.INICIANTE, TEXTO, EstadoDecisao.REPROVADA, motivo="  ")

    assert execucao.decisoes == []


def test_reprovar_com_motivo_guarda_o_motivo() -> None:
    execucao = execucao_de_teste(historico_de_texto(Audiencia.INICIANTE, Destino.APROVADO))

    decisao = decidir(
        execucao, Audiencia.INICIANTE, TEXTO, EstadoDecisao.REPROVADA, motivo="tom condescendente"
    )

    assert decisao.estado is EstadoDecisao.REPROVADA
    assert decisao.motivo == "tom condescendente"


def test_celula_com_recomendacao_nao_pode_ser_aprovada() -> None:
    historico = historico_de_texto(
        Audiencia.AVANCADO,
        Destino.REPROVADO_REVISAO_HUMANA,
        (MotivoReprovacao.RECOMENDACAO,),
    )
    execucao = execucao_de_teste(historico)

    assert celula_bloqueada(historico) is True
    with pytest.raises(DecisaoBloqueada, match="Recomendação"):
        decidir(execucao, Audiencia.AVANCADO, TEXTO, EstadoDecisao.APROVADA)

    assert execucao.decisoes == []


def test_celula_com_recomendacao_pode_ser_reprovada_por_humano() -> None:
    historico = historico_de_texto(
        Audiencia.AVANCADO,
        Destino.REPROVADO_REVISAO_HUMANA,
        (MotivoReprovacao.RECOMENDACAO,),
    )
    execucao = execucao_de_teste(historico)

    decisao = decidir(
        execucao, Audiencia.AVANCADO, TEXTO, EstadoDecisao.REPROVADA, motivo="recomenda comprar"
    )

    assert decisao.estado is EstadoDecisao.REPROVADA


def test_celula_em_revisao_humana_sem_recomendacao_pode_ser_aprovada() -> None:
    historico = historico_de_texto(
        Audiencia.INTERMEDIARIO,
        Destino.REPROVADO_REVISAO_HUMANA,
        (MotivoReprovacao.FLESCH_BR,),
    )
    execucao = execucao_de_teste(historico)

    decisao = decidir(execucao, Audiencia.INTERMEDIARIO, TEXTO, EstadoDecisao.APROVADA)

    assert decisao.estado is EstadoDecisao.APROVADA


def test_celula_ainda_em_correcao_nao_pode_ser_aprovada() -> None:
    historico = historico_de_texto(
        Audiencia.INICIANTE,
        Destino.REPROVADO_CORRIGIVEL,
        (MotivoReprovacao.FLESCH_BR,),
    )
    execucao = execucao_de_teste(historico)

    with pytest.raises(DecisaoInvalida, match="correção"):
        decidir(execucao, Audiencia.INICIANTE, TEXTO, EstadoDecisao.APROVADA)


def test_celula_inexistente_nao_e_encontrada() -> None:
    execucao = execucao_de_teste(historico_de_texto(Audiencia.INICIANTE, Destino.APROVADO))

    with pytest.raises(CelulaNaoEncontrada):
        decidir(execucao, Audiencia.AVANCADO, TEXTO, EstadoDecisao.APROVADA)


def test_celula_sem_conteudo_nao_tem_o_que_decidir() -> None:
    sem_conteudo = HistoricoCelula(
        audiencia=Audiencia.INICIANTE,
        formato=TEXTO,
        tentativas=[],
        destino_final=Destino.REPROVADO_REVISAO_HUMANA,
        falha="provedor sem cota",
    )
    execucao = execucao_de_teste(sem_conteudo)

    with pytest.raises(DecisaoInvalida, match="conteúdo"):
        decidir(execucao, Audiencia.INICIANTE, TEXTO, EstadoDecisao.REPROVADA, motivo="x")


def test_nova_decisao_substitui_a_anterior() -> None:
    execucao = execucao_de_teste(historico_de_texto(Audiencia.INICIANTE, Destino.APROVADO))

    decidir(execucao, Audiencia.INICIANTE, TEXTO, EstadoDecisao.APROVADA)
    decidir(execucao, Audiencia.INICIANTE, TEXTO, EstadoDecisao.REPROVADA, motivo="mudei de ideia")

    assert len(execucao.decisoes) == 1
    assert execucao.decisoes[0].estado is EstadoDecisao.REPROVADA


def test_decidir_resolve_a_pendencia_h4_da_celula() -> None:
    historico = historico_de_texto(
        Audiencia.INTERMEDIARIO,
        Destino.REPROVADO_REVISAO_HUMANA,
        (MotivoReprovacao.FLESCH_BR,),
    )
    pendencia = Pendencia(
        fila=FilaHumana.H4_REVISAO,
        audiencia=Audiencia.INTERMEDIARIO,
        formato=TEXTO,
        motivo="flesch_br",
    )
    execucao = execucao_de_teste(historico, pendencias=(pendencia,))

    decidir(execucao, Audiencia.INTERMEDIARIO, TEXTO, EstadoDecisao.APROVADA)

    assert execucao.pendencias[0].resolvida is True
    assert (execucao.pendencias[0].decisao or "").startswith("aprovada")
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `uv run pytest tests/test_revisao.py -q`
Expected: erro de importação (`No module named 'suno.revisao'`).

- [ ] **Step 3: Implementar `revisao.py`**

Create `src/suno/revisao.py`:

```python
"""A decisão humana sobre uma Célula: aprovar ou reprovar, e quando isso é proibido.

Compliance é métrica do Laudo (CLAUDE.md): a Célula cujo Laudo final carrega
``MotivoReprovacao.RECOMENDACAO`` não pode ser aprovada por ninguém. A regra mora aqui, e não
na tela, para que a API a imponha mesmo a quem chamar a rota sem passar pela interface.
"""

from __future__ import annotations

from suno.dominio import (
    Audiencia,
    DecisaoHumana,
    Destino,
    EstadoDecisao,
    Execucao,
    FilaHumana,
    Formato,
    HistoricoCelula,
    MotivoReprovacao,
)


class CelulaNaoEncontrada(LookupError):
    """A posição não existe nesta execução."""


class DecisaoInvalida(ValueError):
    """O pedido não faz sentido para esta Célula: sem conteúdo, em correção ou sem motivo."""


class DecisaoBloqueada(Exception):
    """O Laudo proíbe a decisão: a Célula cruzou a linha da Recomendação."""


def celula_bloqueada(historico: HistoricoCelula) -> bool:
    """O Laudo final detectou Recomendação: esta Célula não pode ser aprovada."""
    laudo = historico.laudo_final
    return laudo is not None and MotivoReprovacao.RECOMENDACAO in laudo.motivos


def decidir(
    execucao: Execucao,
    audiencia: Audiencia,
    formato: Formato,
    estado: EstadoDecisao,
    *,
    motivo: str | None = None,
    revisor: str | None = None,
) -> DecisaoHumana:
    """Registra a decisão em ``execucao.decisoes`` e resolve a Pendência H4 da posição.

    Muda o objeto em memória; quem chama grava em disco. Uma decisão nova na mesma posição
    substitui a anterior.
    """
    historico = execucao.historico(audiencia, formato)
    if historico is None:
        raise CelulaNaoEncontrada("Célula não encontrada nesta execução")
    if historico.celula_final is None:
        raise DecisaoInvalida("a Célula não tem conteúdo gerado: não há o que decidir")

    motivo_limpo = (motivo or "").strip() or None
    if estado is EstadoDecisao.REPROVADA and motivo_limpo is None:
        raise DecisaoInvalida("reprovar exige motivo")

    if estado is EstadoDecisao.APROVADA:
        if celula_bloqueada(historico):
            raise DecisaoBloqueada(
                "o Laudo detectou Recomendação: esta Célula não pode ser aprovada"
            )
        if historico.destino_final is Destino.REPROVADO_CORRIGIVEL:
            raise DecisaoInvalida("a Célula ainda está em correção: espere o Ciclo terminar")

    decisao = DecisaoHumana(
        audiencia=audiencia,
        formato=formato,
        estado=estado,
        motivo=motivo_limpo,
        revisor=(revisor or "").strip() or None,
    )
    execucao.decisoes = [
        anterior
        for anterior in execucao.decisoes
        if (anterior.audiencia, anterior.formato) != (audiencia, formato)
    ] + [decisao]

    resumo_da_decisao = estado.value if motivo_limpo is None else f"{estado.value}: {motivo_limpo}"
    for pendencia in execucao.pendencias:
        if (
            pendencia.fila is FilaHumana.H4_REVISAO
            and (pendencia.audiencia, pendencia.formato) == (audiencia, formato)
            and not pendencia.resolvida
        ):
            pendencia.resolvida = True
            pendencia.decisao = resumo_da_decisao
    return decisao
```

- [ ] **Step 4: Rodar e ver passar**

Run: `uv run pytest tests/test_revisao.py -q`
Expected: `11 passed`.

- [ ] **Step 5: Checkpoint**

Run: `uv run pytest -q -x` → `854 passed`, 0 failed. `uv run python scripts/vocabulario.py | tail -1` → mesmo número do Step 1 da Tarefa 1. Não commite.

---

## Task 3: Exportar uma Saída (`exportacao.py`)

**Files:**
- Create: `src/suno/exportacao.py`
- Create: `tests/test_exportacao.py`

**Interfaces:**
- Consumes: `Execucao` (com `nome`, `decisoes`, `decisao_de`), `gravar_execucao` e o `_markdown_da_celula` de `suno.gerador.execucao` (a mesma renderização que escreve `celulas/*.md`; é a única fonte do Markdown, por isso se importa o nome com sublinhado: se a equipe renomear, `tests/test_exportacao.py` falha na importação, alto).
- Produces: `FormatoExportacao` (`JSON="json"`, `MARKDOWN="md"`, `ZIP="zip"`); `exportar(execucao: Execucao, pasta: Path, formato: FormatoExportacao) -> tuple[bytes, str, str]`, devolvendo `(conteudo, media_type, nome_do_arquivo)`.

- [ ] **Step 1: Escrever os testes que falham**

Create `tests/test_exportacao.py`:

```python
"""Exportar uma Saída: JSON, Markdown e ZIP. Tudo em memória e em pasta temporária."""

from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

from suno.dominio import Audiencia, Destino, EstadoDecisao, Formato
from suno.exportacao import FormatoExportacao, exportar
from suno.gerador.execucao import gravar_execucao
from suno.revisao import decidir
from tests.construtores_de_execucao import IDENTIFICADOR, execucao_de_teste, historico_de_texto

TEXTO = Formato.TEXTO_ANALITICO


def _execucao_gravada(pasta: Path):
    execucao = execucao_de_teste(
        historico_de_texto(Audiencia.INICIANTE, Destino.APROVADO),
        historico_de_texto(Audiencia.INTERMEDIARIO, Destino.APROVADO),
        nome="Copom 280 · pauta juros",
    )
    decidir(execucao, Audiencia.INICIANTE, TEXTO, EstadoDecisao.APROVADA, revisor="Ana")
    gravar_execucao(execucao, pasta)
    return execucao


def test_json_traz_o_nome_e_as_decisoes(tmp_path: Path) -> None:
    execucao = _execucao_gravada(tmp_path)

    conteudo, media_type, nome_do_arquivo = exportar(
        execucao, tmp_path / IDENTIFICADOR, FormatoExportacao.JSON
    )

    dados = json.loads(conteudo)
    assert dados["nome"] == "Copom 280 · pauta juros"
    assert dados["decisoes"][0]["estado"] == "aprovada"
    assert media_type == "application/json"
    assert nome_do_arquivo == f"{IDENTIFICADOR}.json"


def test_markdown_junta_as_celulas_com_a_decisao_de_cada_uma(tmp_path: Path) -> None:
    execucao = _execucao_gravada(tmp_path)

    conteudo, media_type, nome_do_arquivo = exportar(
        execucao, tmp_path / IDENTIFICADOR, FormatoExportacao.MARKDOWN
    )

    texto = conteudo.decode("utf-8")
    assert texto.startswith("# Copom 280 · pauta juros")
    assert "## Iniciante · Texto analítico" in texto
    assert "## Intermediário · Texto analítico" in texto
    assert "Decisão: aprovada por Ana" in texto
    assert "Decisão: pendente" in texto
    assert "Texto de teste para iniciante." in texto
    assert media_type == "text/markdown; charset=utf-8"
    assert nome_do_arquivo == f"{IDENTIFICADOR}.md"


def test_zip_leva_o_json_as_celulas_e_o_pacote(tmp_path: Path) -> None:
    execucao = _execucao_gravada(tmp_path)
    pasta_do_pacote = tmp_path / IDENTIFICADOR / "pacote" / "iniciante-texto_analitico"
    pasta_do_pacote.mkdir(parents=True)
    (pasta_do_pacote / "pacote.json").write_text("{}", encoding="utf-8")

    conteudo, media_type, nome_do_arquivo = exportar(
        execucao, tmp_path / IDENTIFICADOR, FormatoExportacao.ZIP
    )

    with zipfile.ZipFile(io.BytesIO(conteudo)) as arquivo:
        nomes = set(arquivo.namelist())
        dados = json.loads(arquivo.read(f"{IDENTIFICADOR}/execucao.json"))
    assert f"{IDENTIFICADOR}/execucao.json" in nomes
    assert f"{IDENTIFICADOR}/celulas/iniciante-texto_analitico.md" in nomes
    assert f"{IDENTIFICADOR}/pacote/iniciante-texto_analitico/pacote.json" in nomes
    assert dados["nome"] == "Copom 280 · pauta juros"
    assert media_type == "application/zip"
    assert nome_do_arquivo == f"{IDENTIFICADOR}.zip"


def test_zip_sem_pasta_de_pacote_exporta_so_o_que_existe(tmp_path: Path) -> None:
    execucao = _execucao_gravada(tmp_path)

    conteudo, _, _ = exportar(execucao, tmp_path / IDENTIFICADOR, FormatoExportacao.ZIP)

    with zipfile.ZipFile(io.BytesIO(conteudo)) as arquivo:
        nomes = arquivo.namelist()
    assert not any("/pacote/" in nome for nome in nomes)
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `uv run pytest tests/test_exportacao.py -q`
Expected: erro de importação (`No module named 'suno.exportacao'`).

- [ ] **Step 3: Implementar `exportacao.py`**

Create `src/suno/exportacao.py`:

```python
"""Exportar uma Saída: JSON, Markdown ou ZIP.

O JSON e o Markdown saem do próprio ``Execucao`` em memória (já com ``nome`` e ``decisoes``),
e não de arquivos em disco: uma execução gravada antes do front novo não tem esses campos no
``execucao.json``. O ZIP leva também a pasta ``pacote/`` quando ela existe.
"""

from __future__ import annotations

import io
import zipfile
from enum import StrEnum
from pathlib import Path

from suno.dominio import Audiencia, Execucao, Formato
from suno.gerador.execucao import _markdown_da_celula

ROTULO_DA_AUDIENCIA: dict[Audiencia, str] = {
    Audiencia.INICIANTE: "Iniciante",
    Audiencia.INTERMEDIARIO: "Intermediário",
    Audiencia.AVANCADO: "Avançado",
}
ROTULO_DO_FORMATO: dict[Formato, str] = {
    Formato.TEXTO_ANALITICO: "Texto analítico",
    Formato.CARROSSEL: "Carrossel",
    Formato.ROTEIRO: "Roteiro",
}


class FormatoExportacao(StrEnum):
    JSON = "json"
    MARKDOWN = "md"
    ZIP = "zip"


def _linha_da_decisao(execucao: Execucao, audiencia: Audiencia, formato: Formato) -> str:
    decisao = execucao.decisao_de(audiencia, formato)
    if decisao is None:
        return "Decisão: pendente"
    quem = f" por {decisao.revisor}" if decisao.revisor else ""
    motivo = f" — {decisao.motivo}" if decisao.motivo else ""
    return f"Decisão: {decisao.estado.value}{quem}{motivo}"


def _markdown(execucao: Execucao) -> str:
    partes = [
        f"# {execucao.nome}",
        "",
        f"Ata: {execucao.ata} · provedor: {execucao.provedor_gerador}",
    ]
    for historico in execucao.celulas:
        partes += [
            "",
            "---",
            "",
            f"## {ROTULO_DA_AUDIENCIA[historico.audiencia]} · {ROTULO_DO_FORMATO[historico.formato]}",
            "",
            _linha_da_decisao(execucao, historico.audiencia, historico.formato),
            "",
            _markdown_da_celula(historico),
        ]
    return "\n".join(partes)


def _zip(execucao: Execucao, pasta: Path) -> bytes:
    raiz = execucao.identificador
    memoria = io.BytesIO()
    with zipfile.ZipFile(memoria, "w", zipfile.ZIP_DEFLATED) as arquivo:
        arquivo.writestr(f"{raiz}/execucao.json", execucao.model_dump_json(indent=2))
        for historico in execucao.celulas:
            nome = f"{historico.audiencia.value}-{historico.formato.value}.md"
            arquivo.writestr(f"{raiz}/celulas/{nome}", _markdown_da_celula(historico))
        pasta_do_pacote = pasta / "pacote"
        if pasta_do_pacote.is_dir():
            for caminho in sorted(pasta_do_pacote.rglob("*")):
                if caminho.is_file():
                    relativo = caminho.relative_to(pasta).as_posix()
                    arquivo.write(caminho, f"{raiz}/{relativo}")
    return memoria.getvalue()


def exportar(
    execucao: Execucao, pasta: Path, formato: FormatoExportacao
) -> tuple[bytes, str, str]:
    """Devolve ``(conteúdo, media_type, nome_do_arquivo)``.

    ``pasta`` é ``<pasta_execucoes>/<identificador>``; só o ZIP a lê (para o Pacote).
    """
    identificador = execucao.identificador
    if formato is FormatoExportacao.JSON:
        return (
            execucao.model_dump_json(indent=2).encode("utf-8"),
            "application/json",
            f"{identificador}.json",
        )
    if formato is FormatoExportacao.MARKDOWN:
        return (
            _markdown(execucao).encode("utf-8"),
            "text/markdown; charset=utf-8",
            f"{identificador}.md",
        )
    return _zip(execucao, pasta), "application/zip", f"{identificador}.zip"
```

- [ ] **Step 4: Rodar e ver passar**

Run: `uv run pytest tests/test_exportacao.py -q`
Expected: `4 passed`.

- [ ] **Step 5: Checkpoint**

Run: `uv run pytest -q -x` → `858 passed`, 0 failed. `uv run python scripts/vocabulario.py | tail -1` → mesmo número. Não commite.

---

## Task 4: Resumo por posição e status da Saída (`api/resumo.py`)

**Files:**
- Create: `src/suno/api/resumo.py`
- Create: `tests/test_resumo.py`

**Interfaces:**
- Consumes: `Execucao`, `Destino`, `EstadoDecisao`, `EstadoMedida`, `Audiencia`, `Formato`, `ResultadoComite`, `JulgamentoDimensao`, `DimensaoSubjetiva` de `suno.dominio`; `celula_bloqueada` de `suno.revisao`; os construtores de teste.
- Produces: `PosicaoResumo(audiencia, formato, destino: Destino, decisao: EstadoDecisao | None, bloqueada: bool, sem_conteudo: bool, revisao_comite: bool)`; `StatusSaida = Literal["aguardando_revisao", "concluida"]`; `montar_posicoes(execucao) -> list[PosicaoResumo]` (na ordem de `execucao.celulas`); `status_da_saida(posicoes) -> StatusSaida`.

- [ ] **Step 1: Escrever os testes que falham**

Create `tests/test_resumo.py`:

```python
"""O resumo por posição: o que a lista de Saídas e a Matriz precisam saber de cada Célula."""

from __future__ import annotations

from suno.api.resumo import montar_posicoes, status_da_saida
from suno.dominio import (
    Audiencia,
    Destino,
    DimensaoSubjetiva,
    EstadoDecisao,
    EstadoMedida,
    Formato,
    HistoricoCelula,
    JulgamentoDimensao,
    MotivoReprovacao,
    ResultadoComite,
)
from suno.revisao import decidir
from tests.construtores_de_execucao import execucao_de_teste, historico_de_texto

TEXTO = Formato.TEXTO_ANALITICO


def test_posicao_sem_decisao_vem_pendente() -> None:
    execucao = execucao_de_teste(historico_de_texto(Audiencia.INICIANTE, Destino.APROVADO))

    (posicao,) = montar_posicoes(execucao)

    assert posicao.audiencia is Audiencia.INICIANTE
    assert posicao.formato is TEXTO
    assert posicao.destino is Destino.APROVADO
    assert posicao.decisao is None
    assert posicao.bloqueada is False
    assert posicao.sem_conteudo is False
    assert posicao.revisao_comite is False


def test_decisao_humana_aparece_na_posicao() -> None:
    execucao = execucao_de_teste(historico_de_texto(Audiencia.INICIANTE, Destino.APROVADO))
    decidir(execucao, Audiencia.INICIANTE, TEXTO, EstadoDecisao.APROVADA)

    (posicao,) = montar_posicoes(execucao)

    assert posicao.decisao is EstadoDecisao.APROVADA


def test_recomendacao_no_laudo_marca_a_posicao_como_bloqueada() -> None:
    historico = historico_de_texto(
        Audiencia.AVANCADO, Destino.REPROVADO_REVISAO_HUMANA, (MotivoReprovacao.RECOMENDACAO,)
    )

    (posicao,) = montar_posicoes(execucao_de_teste(historico))

    assert posicao.bloqueada is True


def test_posicao_sem_tentativa_e_sem_conteudo() -> None:
    historico = HistoricoCelula(
        audiencia=Audiencia.INICIANTE,
        formato=TEXTO,
        tentativas=[],
        destino_final=Destino.REPROVADO_REVISAO_HUMANA,
        falha="provedor sem cota",
    )

    (posicao,) = montar_posicoes(execucao_de_teste(historico))

    assert posicao.sem_conteudo is True
    assert posicao.destino is Destino.REPROVADO_REVISAO_HUMANA


def test_dimensao_do_comite_em_revisao_humana_marca_a_posicao() -> None:
    historico = historico_de_texto(Audiencia.INICIANTE, Destino.APROVADO)
    historico.tentativas[0].laudo.comite = ResultadoComite(
        dimensoes=[
            JulgamentoDimensao(
                dimensao=DimensaoSubjetiva.TOM, estado=EstadoMedida.REVISAO_HUMANA
            )
        ],
        provedores=["groq", "sambanova"],
    )

    (posicao,) = montar_posicoes(execucao_de_teste(historico))

    assert posicao.revisao_comite is True
    assert posicao.destino is Destino.APROVADO


def test_status_aguarda_revisao_enquanto_alguma_celula_espera_decisao() -> None:
    execucao = execucao_de_teste(
        historico_de_texto(Audiencia.INICIANTE, Destino.APROVADO),
        historico_de_texto(Audiencia.INTERMEDIARIO, Destino.APROVADO),
    )
    decidir(execucao, Audiencia.INICIANTE, TEXTO, EstadoDecisao.APROVADA)

    assert status_da_saida(montar_posicoes(execucao)) == "aguardando_revisao"


def test_status_conclui_quando_tudo_foi_decidido_ou_nao_pode_ser() -> None:
    execucao = execucao_de_teste(
        historico_de_texto(Audiencia.INICIANTE, Destino.APROVADO),
        historico_de_texto(
            Audiencia.AVANCADO, Destino.REPROVADO_REVISAO_HUMANA, (MotivoReprovacao.RECOMENDACAO,)
        ),
    )
    decidir(execucao, Audiencia.INICIANTE, TEXTO, EstadoDecisao.APROVADA)

    assert status_da_saida(montar_posicoes(execucao)) == "concluida"
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `uv run pytest tests/test_resumo.py -q`
Expected: erro de importação (`No module named 'suno.api.resumo'`).

- [ ] **Step 3: Implementar `api/resumo.py`**

Create `src/suno/api/resumo.py`:

```python
"""O que a lista de Saídas e a Matriz precisam saber de cada Célula, sem abrir o Laudo inteiro.

A regra do status vive aqui, no servidor, para que a lista, o contador do menu e a Saída
aberta concordem. Uma Célula bloqueada por Compliance ou sem conteúdo gerado não tem o que
um humano decida, então não segura a Saída em "aguardando revisão".
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from suno.dominio import Audiencia, Destino, EstadoDecisao, EstadoMedida, Execucao, Formato
from suno.revisao import celula_bloqueada

StatusSaida = Literal["aguardando_revisao", "concluida"]


class PosicaoResumo(BaseModel):
    """Uma posição da Matriz, no mínimo que a tela precisa para colorir e rotular."""

    audiencia: Audiencia
    formato: Formato
    destino: Destino
    decisao: EstadoDecisao | None
    bloqueada: bool
    sem_conteudo: bool
    revisao_comite: bool


def montar_posicoes(execucao: Execucao) -> list[PosicaoResumo]:
    """Uma entrada por Célula pedida, na ordem em que estão em ``execucao.celulas``."""
    posicoes: list[PosicaoResumo] = []
    for historico in execucao.celulas:
        decisao = execucao.decisao_de(historico.audiencia, historico.formato)
        laudo = historico.laudo_final
        revisao_comite = (
            laudo is not None
            and laudo.comite is not None
            and any(d.estado is EstadoMedida.REVISAO_HUMANA for d in laudo.comite.dimensoes)
        )
        posicoes.append(
            PosicaoResumo(
                audiencia=historico.audiencia,
                formato=historico.formato,
                destino=historico.destino_final,
                decisao=decisao.estado if decisao is not None else None,
                bloqueada=celula_bloqueada(historico),
                sem_conteudo=historico.celula_final is None,
                revisao_comite=revisao_comite,
            )
        )
    return posicoes


def status_da_saida(posicoes: list[PosicaoResumo]) -> StatusSaida:
    for posicao in posicoes:
        if posicao.decisao is None and not posicao.bloqueada and not posicao.sem_conteudo:
            return "aguardando_revisao"
    return "concluida"
```

- [ ] **Step 4: Rodar e ver passar**

Run: `uv run pytest tests/test_resumo.py -q`
Expected: `7 passed`.

- [ ] **Step 5: Checkpoint**

Run: `uv run pytest -q -x` → `865 passed`, 0 failed. Vocabulário: mesmo número. Não commite.

---

## Task 5: Rotas novas e fallback de SPA (`api/app.py`)

**Files:**
- Modify: `src/suno/api/app.py`
- Modify: `tests/test_api.py` (só acrescentar no fim, mais duas importações)

**Interfaces:**
- Consumes: `montar_posicoes`, `status_da_saida`, `PosicaoResumo`, `StatusSaida` (Tarefa 4); `decidir`, `CelulaNaoEncontrada`, `DecisaoBloqueada`, `DecisaoInvalida` (Tarefa 2); `exportar`, `FormatoExportacao` (Tarefa 3); `gravar_execucao`, `carregar_execucao` de `suno.gerador.execucao`.
- Produces: `GET /api/execucoes/{id}/resumo` → `ExecucaoResumo`; `PATCH /api/execucoes/{id}` (corpo `{nome}`) → `ExecucaoResumo`; `POST /api/execucoes/{id}/celulas/{aud}/{fmt}/decisao` (corpo `{estado, motivo?, revisor?}`) → `DecisaoHumana`, com 404, 409 e 422; `GET /api/execucoes/{id}/exportar?formato=json|md|zip`. `ExecucaoResumo` ganha `nome`, `modo`, `aprovadas_humano`, `status`, `posicoes`. A lista `GET /api/execucoes` devolve o novo resumo.

- [ ] **Step 1: Escrever os testes que falham**

Em `tests/test_api.py`, troque a linha de importação do `carregar_execucao` (use Edit).

`old_string`:

```python
from suno.gerador.execucao import carregar_execucao
```

`new_string`:

```python
from suno.gerador.execucao import carregar_execucao, gravar_execucao
from tests.construtores_de_execucao import execucao_de_teste, historico_de_texto
```

Acrescente **no fim** de `tests/test_api.py`:

```python


# ---------------------------------------------------------------------------
# 9 — a revisão humana: resumo, renomear, decisão e exportar
# ---------------------------------------------------------------------------


def test_resumo_traz_nome_status_e_posicoes(cliente: TestClient) -> None:
    resposta = cliente.get(f"/api/execucoes/{IDENTIFICADOR}/resumo")

    assert resposta.status_code == 200
    resumo = resposta.json()
    assert resumo["nome"] == IDENTIFICADOR
    assert resumo["status"] == "aguardando_revisao"
    assert resumo["modo"] is None
    assert resumo["aprovadas_humano"] == 0
    posicoes = {(p["audiencia"], p["formato"]): p for p in resumo["posicoes"]}
    assert set(posicoes) == {("iniciante", "carrossel"), ("intermediario", "roteiro")}
    assert posicoes[("iniciante", "carrossel")]["destino"] == "aprovado"
    assert posicoes[("iniciante", "carrossel")]["decisao"] is None
    assert posicoes[("intermediario", "roteiro")]["destino"] == "reprovado_revisao_humana"
    assert posicoes[("intermediario", "roteiro")]["bloqueada"] is False


def test_lista_traz_o_resumo_com_posicoes(cliente: TestClient) -> None:
    (resumo,) = cliente.get("/api/execucoes").json()

    assert resumo["nome"] == IDENTIFICADOR
    assert len(resumo["posicoes"]) == 2
    assert resumo["status"] == "aguardando_revisao"


def test_resumo_de_execucao_inexistente_da_404(cliente: TestClient) -> None:
    assert cliente.get("/api/execucoes/nao-existe/resumo").status_code == 404


def test_renomear_grava_e_a_lista_mostra_o_novo_nome(
    cliente: TestClient, execucao_em_disco: Path
) -> None:
    resposta = cliente.patch(
        f"/api/execucoes/{IDENTIFICADOR}", json={"nome": "  Copom 280 · pauta juros  "}
    )

    assert resposta.status_code == 200
    assert resposta.json()["nome"] == "Copom 280 · pauta juros"
    assert carregar_execucao(IDENTIFICADOR, execucao_em_disco).nome == "Copom 280 · pauta juros"
    assert cliente.get("/api/execucoes").json()[0]["nome"] == "Copom 280 · pauta juros"


def test_renomear_com_nome_vazio_da_422(cliente: TestClient) -> None:
    resposta = cliente.patch(f"/api/execucoes/{IDENTIFICADOR}", json={"nome": "   "})
    assert resposta.status_code == 422


def test_renomear_com_nome_longo_demais_da_422(cliente: TestClient) -> None:
    resposta = cliente.patch(f"/api/execucoes/{IDENTIFICADOR}", json={"nome": "x" * 121})
    assert resposta.status_code == 422


def test_renomear_execucao_inexistente_da_404(cliente: TestClient) -> None:
    resposta = cliente.patch("/api/execucoes/nao-existe", json={"nome": "qualquer"})
    assert resposta.status_code == 404


def test_aprovar_celula_grava_a_decisao_e_resolve_a_pendencia(
    cliente: TestClient, execucao_em_disco: Path
) -> None:
    resposta = cliente.post(
        f"/api/execucoes/{IDENTIFICADOR}/celulas/intermediario/roteiro/decisao",
        json={"estado": "aprovada", "revisor": "Ana"},
    )

    assert resposta.status_code == 200
    assert resposta.json()["estado"] == "aprovada"
    em_disco = carregar_execucao(IDENTIFICADOR, execucao_em_disco)
    assert len(em_disco.decisoes) == 1
    assert em_disco.decisoes[0].revisor == "Ana"
    assert em_disco.pendencias[0].resolvida is True
    resumo = cliente.get(f"/api/execucoes/{IDENTIFICADOR}/resumo").json()
    assert resumo["aprovadas_humano"] == 1


def test_reprovar_sem_motivo_da_422(cliente: TestClient) -> None:
    resposta = cliente.post(
        f"/api/execucoes/{IDENTIFICADOR}/celulas/iniciante/carrossel/decisao",
        json={"estado": "reprovada"},
    )
    assert resposta.status_code == 422


def test_decisao_em_celula_inexistente_da_404(cliente: TestClient) -> None:
    resposta = cliente.post(
        f"/api/execucoes/{IDENTIFICADOR}/celulas/avancado/texto_analitico/decisao",
        json={"estado": "aprovada"},
    )
    assert resposta.status_code == 404


def test_celula_com_recomendacao_responde_409_e_nao_grava(pasta_execucoes: Path) -> None:
    historico = historico_de_texto(
        Audiencia.AVANCADO,
        Destino.REPROVADO_REVISAO_HUMANA,
        (MotivoReprovacao.RECOMENDACAO,),
    )
    gravar_execucao(execucao_de_teste(historico), pasta_execucoes)
    cliente_local = TestClient(criar_app(pasta_execucoes))

    resposta = cliente_local.post(
        "/api/execucoes/exec-teste/celulas/avancado/texto_analitico/decisao",
        json={"estado": "aprovada"},
    )

    assert resposta.status_code == 409
    assert "Recomendação" in resposta.json()["detail"]
    assert carregar_execucao("exec-teste", pasta_execucoes).decisoes == []
    resumo = cliente_local.get("/api/execucoes/exec-teste/resumo").json()
    assert resumo["posicoes"][0]["bloqueada"] is True
    assert resumo["status"] == "concluida"


def test_exportar_json_md_e_zip(cliente: TestClient) -> None:
    esperados = {
        "json": "application/json",
        "md": "text/markdown",
        "zip": "application/zip",
    }
    for formato, media_type in esperados.items():
        resposta = cliente.get(
            f"/api/execucoes/{IDENTIFICADOR}/exportar", params={"formato": formato}
        )

        assert resposta.status_code == 200, formato
        assert resposta.headers["content-type"].startswith(media_type), formato
        assert f'filename="{IDENTIFICADOR}.{formato}"' in resposta.headers["content-disposition"]


def test_exportar_markdown_traz_o_nome_e_as_celulas(cliente: TestClient) -> None:
    resposta = cliente.get(
        f"/api/execucoes/{IDENTIFICADOR}/exportar", params={"formato": "md"}
    )

    assert resposta.text.startswith(f"# {IDENTIFICADOR}")
    assert "## Iniciante · Carrossel" in resposta.text
    assert "## Intermediário · Roteiro" in resposta.text


def test_exportar_formato_invalido_da_422(cliente: TestClient) -> None:
    resposta = cliente.get(
        f"/api/execucoes/{IDENTIFICADOR}/exportar", params={"formato": "pdf"}
    )
    assert resposta.status_code == 422


def test_exportar_execucao_inexistente_da_404(cliente: TestClient) -> None:
    resposta = cliente.get("/api/execucoes/nao-existe/exportar", params={"formato": "json"})
    assert resposta.status_code == 404


# ---------------------------------------------------------------------------
# 10 — a SPA: rota interna do React Router não pode dar 404 ao atualizar a página
# ---------------------------------------------------------------------------


def test_rota_interna_da_spa_devolve_o_index_html(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "index.html").write_text("<html>spa de teste</html>", encoding="utf-8")
    monkeypatch.setattr("suno.api.app.PASTA_DA_SPA", tmp_path)
    cliente_spa = TestClient(criar_app(tmp_path / "execucoes"))

    interna = cliente_spa.get("/saidas/abc/celulas/iniciante/carrossel")
    raiz = cliente_spa.get("/")
    api_inexistente = cliente_spa.get("/api/nao-existe")

    assert interna.status_code == 200
    assert "spa de teste" in interna.text
    assert raiz.status_code == 200
    assert api_inexistente.status_code == 404
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `uv run pytest tests/test_api.py -q -k "resumo or renomear or decisao or recomendacao or exportar or spa"`
Expected: falhas (404 nas rotas novas; `KeyError: 'nome'` na lista). Os testes antigos de `test_api.py` continuam passando.

- [ ] **Step 3: Importações do `app.py`**

Em `src/suno/api/app.py`, use Edit. `old_string`:

```python
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ValidationError
```

`new_string`:

```python
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ValidationError
from starlette.exceptions import HTTPException as ErroHttpDoStarlette
from starlette.types import Scope
```

Edit 2. `old_string`:

```python
from suno.dominio import (
    Ancoras,
    AncoraNumerica,
    Ata,
    Audiencia,
    Destino,
    EstadoMedida,
    Execucao,
    FilaHumana,
    Formato,
    HistoricoCelula,
    PacotePublicacao,
    Pendencia,
)
from suno.gerador.execucao import carregar_execucao, gravar_execucao, listar_execucoes
from suno.ingestao.pdf import carregar_ata
```

`new_string`:

```python
from suno.api.resumo import PosicaoResumo, StatusSaida, montar_posicoes, status_da_saida
from suno.dominio import (
    Ancoras,
    AncoraNumerica,
    Ata,
    Audiencia,
    DecisaoHumana,
    Destino,
    EstadoDecisao,
    EstadoMedida,
    Execucao,
    FilaHumana,
    Formato,
    HistoricoCelula,
    ModoSelecao,
    PacotePublicacao,
    Pendencia,
)
from suno.exportacao import FormatoExportacao, exportar
from suno.gerador.execucao import carregar_execucao, gravar_execucao, listar_execucoes
from suno.ingestao.pdf import carregar_ata
from suno.revisao import CelulaNaoEncontrada, DecisaoBloqueada, DecisaoInvalida, decidir
```

- [ ] **Step 4: `ExecucaoResumo` ampliado e corpos novos**

Edit 3, em `src/suno/api/app.py`. `old_string`:

```python
class ExecucaoResumo(BaseModel):
    """O que a lista de execuções mostra sem abrir o Laudo de cada Célula."""

    identificador: str
    ata: str
    provedor: str
    iniciada_em: datetime
    aprovadas: int
    total_celulas: int
    pendencias: int
```

`new_string`:

```python
class ExecucaoResumo(BaseModel):
    """O que a lista de Saídas mostra sem abrir o Laudo de cada Célula."""

    identificador: str
    nome: str
    ata: str
    provedor: str
    modo: ModoSelecao | None
    iniciada_em: datetime
    aprovadas: int
    aprovadas_humano: int
    total_celulas: int
    pendencias: int
    status: StatusSaida
    posicoes: list[PosicaoResumo]
```

Edit 4. `old_string`:

```python
class DecisaoFila(BaseModel):
    """O corpo do ``POST .../resolver``: a decisão que um humano registrou em H4."""

    decisao: str
```

`new_string`:

```python
class DecisaoFila(BaseModel):
    """O corpo do ``POST .../resolver``: a decisão que um humano registrou em H4."""

    decisao: str


class Renomeacao(BaseModel):
    """O corpo do ``PATCH /api/execucoes/{id}``."""

    nome: str


class PedidoDeDecisao(BaseModel):
    """O corpo do ``POST .../decisao``: aprovar ou reprovar uma Célula."""

    estado: EstadoDecisao
    motivo: str | None = None
    revisor: str | None = None


NOME_MAXIMO = 120
```

- [ ] **Step 5: Helper `_resumo_da_execucao`, fallback de SPA e rotas**

Edit 5, em `src/suno/api/app.py`. `old_string`:

```python
def criar_app(pasta_execucoes: Path) -> FastAPI:
```

`new_string`:

```python
def _resumo_da_execucao(execucao: Execucao) -> ExecucaoResumo:
    posicoes = montar_posicoes(execucao)
    return ExecucaoResumo(
        identificador=execucao.identificador,
        nome=execucao.nome,
        ata=execucao.ata,
        provedor=execucao.provedor_gerador,
        modo=execucao.selecao.modo if execucao.selecao is not None else None,
        iniciada_em=execucao.iniciada_em,
        aprovadas=sum(1 for h in execucao.celulas if h.destino_final is Destino.APROVADO),
        aprovadas_humano=sum(1 for d in execucao.decisoes if d.estado is EstadoDecisao.APROVADA),
        total_celulas=len(execucao.celulas),
        pendencias=len(execucao.pendencias),
        status=status_da_saida(posicoes),
        posicoes=posicoes,
    )


class _SpaEstatica(StaticFiles):
    """Serve ``web/dist`` e cai em ``index.html`` para rota do React Router (ex. ``/saidas/abc``).

    ``StaticFiles(html=True)`` só devolve ``index.html`` para o diretório raiz: atualizar a
    página numa rota interna dava 404. Rota de API que não existe continua sendo 404 de verdade.
    """

    async def get_response(self, path: str, scope: Scope) -> Response:
        try:
            return await super().get_response(path, scope)
        except ErroHttpDoStarlette as erro:
            # No Windows o Starlette entrega o caminho com barra invertida ("api\nao-existe").
            e_da_api = path.replace("\\", "/").startswith("api/")
            if erro.status_code == 404 and not e_da_api:
                return await super().get_response("index.html", scope)
            raise


def criar_app(pasta_execucoes: Path) -> FastAPI:
```

Edit 6: a rota de lista passa a usar o helper. `old_string`:

```python
            aprovadas = sum(1 for h in execucao.celulas if h.destino_final is Destino.APROVADO)
            resumos.append(
                ExecucaoResumo(
                    identificador=execucao.identificador,
                    ata=execucao.ata,
                    provedor=execucao.provedor_gerador,
                    iniciada_em=execucao.iniciada_em,
                    aprovadas=aprovadas,
                    total_celulas=len(execucao.celulas),
                    pendencias=len(execucao.pendencias),
                )
            )
        return resumos
```

`new_string`:

```python
            resumos.append(_resumo_da_execucao(execucao))
        return resumos
```

Edit 7: as rotas novas, logo depois de `obter_execucao`. `old_string`:

```python
    @app.get("/api/execucoes/{identificador}")
    def obter_execucao(identificador: str) -> Execucao:
        return _execucao_ou_404(identificador)
```

`new_string`:

```python
    @app.get("/api/execucoes/{identificador}")
    def obter_execucao(identificador: str) -> Execucao:
        return _execucao_ou_404(identificador)

    @app.get("/api/execucoes/{identificador}/resumo")
    def obter_resumo(identificador: str) -> ExecucaoResumo:
        return _resumo_da_execucao(_execucao_ou_404(identificador))

    @app.patch("/api/execucoes/{identificador}")
    def renomear_execucao(identificador: str, corpo: Renomeacao) -> ExecucaoResumo:
        nome = corpo.nome.strip()
        if not nome:
            raise HTTPException(422, "o nome não pode ficar vazio")
        if len(nome) > NOME_MAXIMO:
            raise HTTPException(422, f"o nome passa de {NOME_MAXIMO} caracteres")
        with trava_de_escrita:
            execucao = _execucao_ou_404(identificador)
            execucao.nome = nome
            gravar_execucao(execucao, pasta_execucoes)
            return _resumo_da_execucao(execucao)

    @app.post("/api/execucoes/{identificador}/celulas/{audiencia}/{formato}/decisao")
    def registrar_decisao(
        identificador: str, audiencia: Audiencia, formato: Formato, corpo: PedidoDeDecisao
    ) -> DecisaoHumana:
        with trava_de_escrita:
            execucao = _execucao_ou_404(identificador)
            try:
                decisao = decidir(
                    execucao,
                    audiencia,
                    formato,
                    corpo.estado,
                    motivo=corpo.motivo,
                    revisor=corpo.revisor,
                )
            except CelulaNaoEncontrada as erro:
                raise HTTPException(404, str(erro)) from None
            except DecisaoBloqueada as erro:
                raise HTTPException(409, str(erro)) from None
            except DecisaoInvalida as erro:
                raise HTTPException(422, str(erro)) from None
            gravar_execucao(execucao, pasta_execucoes)
            return decisao

    @app.get("/api/execucoes/{identificador}/exportar")
    def exportar_execucao(identificador: str, formato: FormatoExportacao) -> Response:
        execucao = _execucao_ou_404(identificador)
        conteudo, media_type, nome_do_arquivo = exportar(
            execucao, pasta_execucoes / identificador, formato
        )
        return Response(
            content=conteudo,
            media_type=media_type,
            headers={"Content-Disposition": f'attachment; filename="{nome_do_arquivo}"'},
        )
```

Edit 8: o fallback no mount da SPA. `old_string`:

```python
        app.mount("/", StaticFiles(directory=PASTA_DA_SPA, html=True), name="spa")
```

`new_string`:

```python
        app.mount("/", _SpaEstatica(directory=PASTA_DA_SPA, html=True), name="spa")
```

- [ ] **Step 6: Rodar e ver passar**

Run: `uv run pytest tests/test_api.py -q`
Expected: todos passam (os antigos e os `16` novos, contando o teste da SPA). Se `test_exportar_json_md_e_zip` falhar com `KeyError` de rótulo, confira que `ROTULO_DA_AUDIENCIA` e `ROTULO_DO_FORMATO` cobrem as três Audiências e os três Formatos.

- [ ] **Step 7: Checkpoint**

Run: `uv run pytest -q -x` → `881 passed`, 0 failed. Vocabulário: mesmo número. Não commite.

---

## Task 6: Contrato OpenAPI e cliente TypeScript regenerado

**Files:**
- Create: `tests/test_contrato_openapi.py`
- Regerar: `web/openapi.json`, `web/src/api/schema.d.ts`

**Interfaces:**
- Produces: `components["schemas"]` em `web/src/api/schema.d.ts` com `PosicaoResumo`, `DecisaoHumana`, `EstadoDecisao`, `FormatoExportacao`, `Renomeacao`, `PedidoDeDecisao`, e `ExecucaoResumo` ampliado. Rotas `/api/execucoes/{identificador}/resumo`, `PATCH /api/execucoes/{identificador}`, `.../decisao` e `.../exportar` em `paths`.

- [ ] **Step 1: Escrever o teste de contrato**

Create `tests/test_contrato_openapi.py`:

```python
"""O ``web/openapi.json`` commitado tem que ser o que a API gera hoje.

Antes deste teste, só o script ``scripts/gerar-cliente`` atualizava o arquivo e nada conferia:
o cliente TypeScript podia divergir do servidor sem aviso (ADR 0005).
"""

from __future__ import annotations

import json
from pathlib import Path

from suno.api.openapi import gerar_schema

CAMINHO = Path(__file__).resolve().parent.parent / "web" / "openapi.json"


def test_openapi_commitado_bate_com_o_que_a_api_gera() -> None:
    commitado = json.loads(CAMINHO.read_text(encoding="utf-8"))

    assert commitado == gerar_schema(), (
        "web/openapi.json está desatualizado: rode scripts/gerar-cliente.ps1 (ou .sh)"
    )
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `uv run pytest tests/test_contrato_openapi.py -q`
Expected: FAIL com a mensagem `web/openapi.json está desatualizado`. (Já estava desatualizado antes de esta mudança: faltavam 11 schemas do trabalho da equipe.)

- [ ] **Step 3: Regerar o `openapi.json` e o cliente**

O script `scripts/gerar-cliente.ps1` baixa o gerador pela rede com `npx --yes`; o `openapi-typescript` já está em `web/node_modules`, então use o binário local. Na raiz:

```bash
PYTHONIOENCODING=utf-8 uv run python -c "import json, pathlib; from suno.api.openapi import gerar_schema; pathlib.Path('web/openapi.json').write_text(json.dumps(gerar_schema(), ensure_ascii=False, indent=2) + '\n', encoding='utf-8')"
cd web && npx openapi-typescript openapi.json -o src/api/schema.d.ts
```

Expected: `openapi-typescript` imprime `✨ openapi-typescript ... openapi.json → src/api/schema.d.ts`.

- [ ] **Step 4: Conferir o resultado**

Run: `grep -c "PosicaoResumo\|PedidoDeDecisao\|FormatoExportacao" web/src/api/schema.d.ts`
Expected: um número maior que 0.

Run: `uv run pytest tests/test_contrato_openapi.py -q`
Expected: `1 passed`.

Run (em `web/`): `npx tsc --noEmit -p tsconfig.app.json`
Expected: sem erros. (As páginas antigas só usam tipos que continuam existindo.)

- [ ] **Step 5: Checkpoint**

Run: `uv run pytest -q -x` → `882 passed`, 0 failed. Não commite. Se um dia o contrato divergir, o teste acima diz como regerar.

---

## Task 7: Tema escuro e Vitest

**Files:**
- Modify: `web/package.json`, `web/vite.config.ts`, `web/index.html`
- Rewrite: `web/src/estilos/global.css`

**Interfaces:**
- Produces: utilidades Tailwind de cor `bg-fundo`, `bg-lateral`, `bg-cartao`, `bg-cartao-2`, `border-linha`, `text-texto`, `text-suave`, `bg-suno`/`text-suno`/`border-suno` (aceitam `/15`, `/45`), `text-ok`/`bg-ok`/`border-ok`, `text-alerta`/`bg-alerta`/`border-alerta`; `npm test` roda o Vitest sobre `src/**/*.test.ts`.

- [ ] **Step 1: Instalar o Vitest**

Run (em `web/`): `npm install --save-exact --save-dev vitest`
Expected: `package.json` ganha `"vitest": "<versão exata>"` em `devDependencies`. Se o npm recusar por conflito de peer com o Vite 8 (`ERESOLVE`), rode `npm view vitest@latest peerDependencies` e instale a versão mais nova cuja faixa de `vite` inclua a versão do projeto; não use `--force`.

- [ ] **Step 2: Script de teste**

Em `web/package.json`, use Edit. `old_string`:

```json
    "preview": "vite preview"
```

`new_string`:

```json
    "preview": "vite preview",
    "test": "vitest run"
```

- [ ] **Step 3: Configuração do Vitest e cores do manifesto**

Em `web/vite.config.ts`, Edit 1. `old_string`:

```ts
/// <reference types="vite/client" />
```

`new_string`:

```ts
/// <reference types="vite/client" />
/// <reference types="vitest/config" />
```

Edit 2. `old_string`:

```ts
        description: "Matriz de Células, Laudos e filas humanas do Suno Content.",
        theme_color: "#0f172a",
        background_color: "#0f172a",
```

`new_string`:

```ts
        description: "Painel de revisão do conteúdo gerado pelo Suno Content.",
        theme_color: "#0e0e0f",
        background_color: "#0e0e0f",
```

Edit 3. `old_string`:

```ts
  server: {
    proxy: {
```

`new_string`:

```ts
  test: {
    environment: "node",
    include: ["src/**/*.test.ts"],
  },
  server: {
    proxy: {
```

- [ ] **Step 4: `index.html`**

Em `web/index.html`, Edit 1. `old_string`:

```html
    <meta name="theme-color" content="#0f172a" />
    <meta
      name="description"
      content="Suno Content: a Matriz de Células, o Laudo de cada uma e as filas humanas H3, H4 e H5."
    />
```

`new_string`:

```html
    <meta name="theme-color" content="#0e0e0f" />
    <meta
      name="description"
      content="Suno Content: painel de revisão do conteúdo gerado. Fontes, curadoria e saídas."
    />
```

- [ ] **Step 5: Reescrever `global.css`**

Rewrite `web/src/estilos/global.css`:

```css
@import "tailwindcss";

/* Tema só escuro, com as cores da Suno. O vermelho foi estimado de uma captura de tela do
   app deles: o hex oficial substitui `--color-suno` quando existir. Cada `--color-*` vira
   utilidade do Tailwind (`bg-fundo`, `text-suave`, `border-suno/45`...). */
@theme {
  --color-fundo: #0e0e0f;
  --color-lateral: #141415;
  --color-cartao: #1c1c1e;
  --color-cartao-2: #242427;
  --color-linha: #2c2c30;
  --color-texto: #f3f3f4;
  --color-suave: #8d8d93;
  --color-suno: #ef4b3f;
  --color-ok: #3ecf8e;
  --color-alerta: #f5b042;
  --font-sans:
    system-ui, -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
}

:root {
  color-scheme: dark;
}

html,
body,
#raiz {
  height: 100%;
}

body {
  background: var(--color-fundo);
  color: var(--color-texto);
  font-family: var(--font-sans);
}

/* Estilo mínimo para o Texto analítico renderizado em Markdown (react-markdown),
   sem depender de um plugin de tipografia. */
.markdown :is(h1, h2, h3) {
  font-weight: 600;
  margin-top: 1rem;
  margin-bottom: 0.5rem;
}

.markdown p {
  margin-bottom: 0.75rem;
  line-height: 1.7;
}

.markdown ul {
  list-style: disc;
  list-style-position: inside;
  margin-bottom: 0.75rem;
}

.markdown strong {
  font-weight: 600;
}
```

- [ ] **Step 6: Verificar**

Run (em `web/`): `npx vitest run --passWithNoTests`
Expected: `No test files found, exiting with code 0` ou equivalente, sem erro de configuração.

Run (em `web/`): `npx tsc --noEmit -p tsconfig.app.json && npx tsc --noEmit -p tsconfig.node.json`
Expected: sem erros. (As páginas antigas ainda usam classes `dark:`/`slate`; ficam feias até serem trocadas nas próximas tarefas, e isso é esperado.)

- [ ] **Step 7: Checkpoint**

Rode `npm run build` em `web/`. Expected: build conclui. Não commite.

---

## Task 8: Lógica pura da Matriz (`lib/matriz.ts`) e nome do revisor

**Files:**
- Create: `web/src/lib/matriz.ts`
- Create: `web/src/lib/matriz.test.ts`
- Create: `web/src/lib/revisor.ts`

**Interfaces:**
- Produces (todas em `web/src/lib/matriz.ts`):
  - tipos `EstadoPosicao = "aprovada" | "aguardando" | "revisao" | "reprovada"`, `TomChip = "neutro" | "forte" | "ok" | "alerta" | "ruim"`, `FiltroDeStatus = "todas" | "aguardando_revisao" | "concluida"`, `PosicaoParaTela`, `ChipsDaPosicao`, `ContagemDaSaida`;
  - `chaveDaPosicao(audiencia, formato): string` (`"audiencia:formato"`);
  - `estadoDaPosicao(posicao): EstadoPosicao`;
  - `chipsDaPosicao(posicao): { laudo: {texto, tom}; decisao: {texto, tom} }`;
  - `contarPosicoes(posicoes): { total, laudoOk, emRevisao, bloqueadas, aprovadasPorVoce, aguardando }`;
  - `contarAguardando(saidas): number`;
  - `normalizarBusca(texto): string`;
  - `filtrarSaidas(saidas, { busca, status }): T[]`;
  - `maisRecentesPrimeiro(saidas): T[]`;
  - `larguraDaBarra(medida): number` (0 a 100);
  - `celulaBloqueada(laudo): boolean`;
  - `vizinhas(posicoes, audiencia, formato): { anterior, proxima }`.
- Produces (em `web/src/lib/revisor.ts`): `lerRevisor(): string`, `guardarRevisor(nome: string): void`.

- [ ] **Step 1: Escrever os testes que falham**

Create `web/src/lib/matriz.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import {
  celulaBloqueada,
  chaveDaPosicao,
  chipsDaPosicao,
  contarAguardando,
  contarPosicoes,
  estadoDaPosicao,
  filtrarSaidas,
  larguraDaBarra,
  maisRecentesPrimeiro,
  normalizarBusca,
  vizinhas,
  type PosicaoParaTela,
} from "./matriz";

function posicao(parcial: Partial<PosicaoParaTela> = {}): PosicaoParaTela {
  return {
    audiencia: "iniciante",
    formato: "carrossel",
    destino: "aprovado",
    decisao: null,
    bloqueada: false,
    sem_conteudo: false,
    revisao_comite: false,
    ...parcial,
  };
}

describe("estadoDaPosicao", () => {
  it("decisão de aprovar pinta de verde", () => {
    expect(estadoDaPosicao(posicao({ decisao: "aprovada" }))).toBe("aprovada");
  });

  it("decisão de reprovar, bloqueio e falta de conteúdo pintam de vermelho", () => {
    expect(estadoDaPosicao(posicao({ decisao: "reprovada" }))).toBe("reprovada");
    expect(estadoDaPosicao(posicao({ bloqueada: true }))).toBe("reprovada");
    expect(
      estadoDaPosicao(posicao({ sem_conteudo: true, destino: "reprovado_revisao_humana" })),
    ).toBe("reprovada");
  });

  it("revisão humana pelo Laudo ou pelo comitê pinta de âmbar", () => {
    expect(estadoDaPosicao(posicao({ destino: "reprovado_revisao_humana" }))).toBe("revisao");
    expect(estadoDaPosicao(posicao({ revisao_comite: true }))).toBe("revisao");
  });

  it("Laudo ok sem decisão espera a decisão", () => {
    expect(estadoDaPosicao(posicao())).toBe("aguardando");
  });

  it("a decisão humana vale mais que a revisão pedida pelo Laudo", () => {
    expect(
      estadoDaPosicao(posicao({ destino: "reprovado_revisao_humana", decisao: "aprovada" })),
    ).toBe("aprovada");
  });
});

describe("chipsDaPosicao", () => {
  it("Célula limpa e pendente", () => {
    expect(chipsDaPosicao(posicao())).toEqual({
      laudo: { texto: "Laudo ok", tom: "ok" },
      decisao: { texto: "Pendente", tom: "neutro" },
    });
  });

  it("Célula bloqueada mostra Compliance e Bloqueada", () => {
    expect(chipsDaPosicao(posicao({ bloqueada: true, destino: "reprovado_revisao_humana" }))).toEqual({
      laudo: { texto: "Compliance", tom: "ruim" },
      decisao: { texto: "Bloqueada", tom: "ruim" },
    });
  });

  it("revisão humana e comitê aparecem em âmbar", () => {
    expect(chipsDaPosicao(posicao({ destino: "reprovado_revisao_humana" })).laudo).toEqual({
      texto: "Revisão humana",
      tom: "alerta",
    });
    expect(chipsDaPosicao(posicao({ revisao_comite: true })).laudo).toEqual({
      texto: "Revisão: comitê",
      tom: "alerta",
    });
  });

  it("decisões humanas aparecem no segundo chip", () => {
    expect(chipsDaPosicao(posicao({ decisao: "aprovada" })).decisao).toEqual({
      texto: "Você aprovou",
      tom: "forte",
    });
    expect(chipsDaPosicao(posicao({ decisao: "reprovada" })).decisao).toEqual({
      texto: "Você reprovou",
      tom: "ruim",
    });
  });

  it("sem conteúdo mostra que a geração parou", () => {
    expect(
      chipsDaPosicao(posicao({ sem_conteudo: true, destino: "reprovado_revisao_humana" })),
    ).toEqual({
      laudo: { texto: "Sem conteúdo", tom: "ruim" },
      decisao: { texto: "Parou", tom: "ruim" },
    });
  });

  it("Célula em correção aparece em âmbar", () => {
    expect(chipsDaPosicao(posicao({ destino: "reprovado_corrigivel" })).laudo).toEqual({
      texto: "Em correção",
      tom: "alerta",
    });
  });
});

describe("contarPosicoes", () => {
  it("reproduz o exemplo do mockup: 5 Células, 3 com Laudo ok, 1 em revisão, 1 bloqueada, 1 aprovada por você", () => {
    const posicoes = [
      posicao({ audiencia: "iniciante", formato: "texto_analitico", decisao: "aprovada" }),
      posicao({ audiencia: "iniciante", formato: "carrossel" }),
      posicao({
        audiencia: "intermediario",
        formato: "texto_analitico",
        destino: "reprovado_revisao_humana",
      }),
      posicao({ audiencia: "intermediario", formato: "roteiro" }),
      posicao({
        audiencia: "avancado",
        formato: "carrossel",
        destino: "reprovado_revisao_humana",
        bloqueada: true,
      }),
    ];

    expect(contarPosicoes(posicoes)).toEqual({
      total: 5,
      laudoOk: 3,
      emRevisao: 1,
      bloqueadas: 1,
      aprovadasPorVoce: 1,
      aguardando: 3,
    });
  });

  it("lista vazia zera tudo", () => {
    expect(contarPosicoes([])).toEqual({
      total: 0,
      laudoOk: 0,
      emRevisao: 0,
      bloqueadas: 0,
      aprovadasPorVoce: 0,
      aguardando: 0,
    });
  });
});

describe("saídas: contagem, filtro e ordem", () => {
  const saidas = [
    {
      nome: "Copom 280 · pauta juros",
      identificador: "copom-280-gemini-20261009",
      ata: "copom-280-2026-08-05",
      status: "aguardando_revisao",
      iniciada_em: "2026-10-09T14:32:00Z",
    },
    {
      nome: "Empresa Exemplo · aquisição",
      identificador: "cvm-001",
      ata: "fato-relevante-001",
      status: "concluida",
      iniciada_em: "2026-10-08T10:05:00Z",
    },
    {
      nome: "Demo Copom 280 · Matriz completa",
      identificador: "demo-copom-280",
      ata: "copom-280-2026-08-05",
      status: "aguardando_revisao",
      iniciada_em: "2026-09-18T12:51:00Z",
    },
  ];

  it("conta as Saídas aguardando revisão", () => {
    expect(contarAguardando(saidas)).toBe(2);
  });

  it("filtra por status", () => {
    const resultado = filtrarSaidas(saidas, { busca: "", status: "concluida" });
    expect(resultado.map((s) => s.identificador)).toEqual(["cvm-001"]);
  });

  it("busca sem diferenciar acento nem caixa, no nome, no identificador e na Ata", () => {
    expect(filtrarSaidas(saidas, { busca: "AQUISICAO", status: "todas" })).toHaveLength(1);
    expect(filtrarSaidas(saidas, { busca: "demo-copom", status: "todas" })).toHaveLength(1);
    expect(filtrarSaidas(saidas, { busca: "copom-280-2026", status: "todas" })).toHaveLength(2);
  });

  it("busca e status se combinam", () => {
    const resultado = filtrarSaidas(saidas, { busca: "copom", status: "aguardando_revisao" });
    expect(resultado).toHaveLength(2);
    expect(filtrarSaidas(saidas, { busca: "copom", status: "concluida" })).toHaveLength(0);
  });

  it("normalizarBusca tira acento e espaços nas pontas", () => {
    expect(normalizarBusca("  Aquisição  ")).toBe("aquisicao");
  });

  it("ordena da mais recente para a mais antiga sem mudar o original", () => {
    const ordenadas = maisRecentesPrimeiro([saidas[2], saidas[1], saidas[0]]);
    expect(ordenadas.map((s) => s.identificador)).toEqual([
      "copom-280-gemini-20261009",
      "cvm-001",
      "demo-copom-280",
    ]);
  });
});

describe("larguraDaBarra", () => {
  it("Flesch-BR já está em 0 a 100", () => {
    expect(larguraDaBarra({ metrica: "flesch_br", valor: 89.15 })).toBeCloseTo(89.15);
  });

  it("as demais métricas estão em 0 a 1", () => {
    expect(larguraDaBarra({ metrica: "densidade", valor: 0.0288 })).toBeCloseTo(2.88);
    expect(larguraDaBarra({ metrica: "aderencia", valor: 1 })).toBe(100);
  });

  it("valor ausente fica em zero e nunca passa de 0 a 100", () => {
    expect(larguraDaBarra({ metrica: "aderencia", valor: null })).toBe(0);
    expect(larguraDaBarra({ metrica: "aderencia" })).toBe(0);
    expect(larguraDaBarra({ metrica: "flesch_br", valor: 150 })).toBe(100);
    expect(larguraDaBarra({ metrica: "flesch_br", valor: -10 })).toBe(0);
  });
});

describe("celulaBloqueada", () => {
  it("só Recomendação no Laudo bloqueia", () => {
    expect(celulaBloqueada({ motivos: ["recomendacao"] })).toBe(true);
    expect(celulaBloqueada({ motivos: ["flesch_br"] })).toBe(false);
    expect(celulaBloqueada({ motivos: [] })).toBe(false);
    expect(celulaBloqueada(null)).toBe(false);
    expect(celulaBloqueada(undefined)).toBe(false);
  });
});

describe("vizinhas e chaveDaPosicao", () => {
  const pedidas = [
    { audiencia: "iniciante", formato: "texto_analitico" },
    { audiencia: "iniciante", formato: "carrossel" },
    { audiencia: "avancado", formato: "roteiro" },
  ];

  it("acha a anterior e a próxima na ordem pedida", () => {
    const resultado = vizinhas(pedidas, "iniciante", "carrossel");
    expect(resultado.anterior).toEqual(pedidas[0]);
    expect(resultado.proxima).toEqual(pedidas[2]);
  });

  it("a primeira não tem anterior e a última não tem próxima", () => {
    expect(vizinhas(pedidas, "iniciante", "texto_analitico").anterior).toBeNull();
    expect(vizinhas(pedidas, "avancado", "roteiro").proxima).toBeNull();
  });

  it("posição que não foi pedida não tem vizinhas", () => {
    expect(vizinhas(pedidas, "avancado", "texto_analitico")).toEqual({
      anterior: null,
      proxima: null,
    });
  });

  it("a chave junta Audiência e Formato", () => {
    expect(chaveDaPosicao("iniciante", "carrossel")).toBe("iniciante:carrossel");
  });
});
```

- [ ] **Step 2: Rodar e ver falhar**

Run (em `web/`): `npx vitest run`
Expected: falha de importação (`Failed to resolve import "./matriz"`).

- [ ] **Step 3: Implementar `lib/matriz.ts`**

Create `web/src/lib/matriz.ts`:

```ts
// Lógica pura da Matriz e das Saídas: nada aqui toca React nem a rede, por isso é a parte do
// front que o Vitest cobre. A regra de verdade (quem pode aprovar o quê) mora no servidor, em
// src/suno/revisao.py; aqui só se decide como a tela mostra o que o servidor já resumiu.

export type EstadoPosicao = "aprovada" | "aguardando" | "revisao" | "reprovada";
export type TomChip = "neutro" | "forte" | "ok" | "alerta" | "ruim";
export type FiltroDeStatus = "todas" | "aguardando_revisao" | "concluida";

/** O mínimo de uma posição da Matriz. É o `PosicaoResumo` do servidor, sem depender do schema. */
export interface PosicaoParaTela {
  audiencia: string;
  formato: string;
  destino: string;
  decisao: string | null;
  bloqueada: boolean;
  sem_conteudo: boolean;
  revisao_comite: boolean;
}

export interface ChipsDaPosicao {
  laudo: { texto: string; tom: TomChip };
  decisao: { texto: string; tom: TomChip };
}

export interface ContagemDaSaida {
  total: number;
  laudoOk: number;
  emRevisao: number;
  bloqueadas: number;
  aprovadasPorVoce: number;
  aguardando: number;
}

export function chaveDaPosicao(audiencia: string, formato: string): string {
  return `${audiencia}:${formato}`;
}

export function estadoDaPosicao(posicao: PosicaoParaTela): EstadoPosicao {
  if (posicao.decisao === "aprovada") return "aprovada";
  if (posicao.decisao === "reprovada" || posicao.bloqueada || posicao.sem_conteudo) {
    return "reprovada";
  }
  if (posicao.destino === "reprovado_revisao_humana" || posicao.revisao_comite) return "revisao";
  return "aguardando";
}

export function chipsDaPosicao(posicao: PosicaoParaTela): ChipsDaPosicao {
  let laudo: ChipsDaPosicao["laudo"];
  if (posicao.sem_conteudo) laudo = { texto: "Sem conteúdo", tom: "ruim" };
  else if (posicao.bloqueada) laudo = { texto: "Compliance", tom: "ruim" };
  else if (posicao.destino === "reprovado_revisao_humana") {
    laudo = { texto: "Revisão humana", tom: "alerta" };
  } else if (posicao.revisao_comite) laudo = { texto: "Revisão: comitê", tom: "alerta" };
  else if (posicao.destino === "reprovado_corrigivel") {
    laudo = { texto: "Em correção", tom: "alerta" };
  } else if (posicao.destino === "aprovado") laudo = { texto: "Laudo ok", tom: "ok" };
  else laudo = { texto: "Sem Laudo", tom: "neutro" };

  let decisao: ChipsDaPosicao["decisao"];
  if (posicao.decisao === "aprovada") decisao = { texto: "Você aprovou", tom: "forte" };
  else if (posicao.decisao === "reprovada") decisao = { texto: "Você reprovou", tom: "ruim" };
  else if (posicao.sem_conteudo) decisao = { texto: "Parou", tom: "ruim" };
  else if (posicao.bloqueada) decisao = { texto: "Bloqueada", tom: "ruim" };
  else decisao = { texto: "Pendente", tom: "neutro" };

  return { laudo, decisao };
}

function precisaDeDecisao(posicao: PosicaoParaTela): boolean {
  return posicao.decisao === null && !posicao.bloqueada && !posicao.sem_conteudo;
}

export function contarPosicoes(posicoes: readonly PosicaoParaTela[]): ContagemDaSaida {
  const contagem: ContagemDaSaida = {
    total: posicoes.length,
    laudoOk: 0,
    emRevisao: 0,
    bloqueadas: 0,
    aprovadasPorVoce: 0,
    aguardando: 0,
  };
  for (const posicao of posicoes) {
    if (posicao.destino === "aprovado" && !posicao.bloqueada) contagem.laudoOk += 1;
    if (posicao.bloqueada) contagem.bloqueadas += 1;
    const estado = estadoDaPosicao(posicao);
    if (estado === "aprovada") contagem.aprovadasPorVoce += 1;
    if (estado === "revisao") contagem.emRevisao += 1;
    if (precisaDeDecisao(posicao)) contagem.aguardando += 1;
  }
  return contagem;
}

export function contarAguardando(saidas: readonly { status: string }[]): number {
  return saidas.filter((saida) => saida.status === "aguardando_revisao").length;
}

export function normalizarBusca(texto: string): string {
  return texto
    .normalize("NFD")
    .replace(/\p{Diacritic}/gu, "")
    .toLowerCase()
    .trim();
}

export interface SaidaParaFiltro {
  nome: string;
  identificador: string;
  ata: string;
  status: string;
}

export function filtrarSaidas<T extends SaidaParaFiltro>(
  saidas: readonly T[],
  filtro: { busca: string; status: FiltroDeStatus },
): T[] {
  const termo = normalizarBusca(filtro.busca);
  return saidas.filter((saida) => {
    if (filtro.status !== "todas" && saida.status !== filtro.status) return false;
    if (termo === "") return true;
    return normalizarBusca(`${saida.nome} ${saida.identificador} ${saida.ata}`).includes(termo);
  });
}

export function maisRecentesPrimeiro<T extends { iniciada_em: string }>(
  saidas: readonly T[],
): T[] {
  return [...saidas].sort((a, b) => b.iniciada_em.localeCompare(a.iniciada_em));
}

/** Largura da barra de uma métrica, de 0 a 100. Flesch-BR já vem em 0 a 100; as demais, em 0 a 1. */
export function larguraDaBarra(medida: { metrica: string; valor?: number | null }): number {
  if (medida.valor === null || medida.valor === undefined) return 0;
  const percentual = medida.metrica === "flesch_br" ? medida.valor : medida.valor * 100;
  return Math.min(100, Math.max(0, percentual));
}

/** Só espelha a regra do servidor, para a tela desabilitar o botão com o motivo à vista. */
export function celulaBloqueada(
  laudo: { motivos?: readonly string[] | null } | null | undefined,
): boolean {
  return laudo?.motivos?.includes("recomendacao") ?? false;
}

export function vizinhas<T extends { audiencia: string; formato: string }>(
  posicoes: readonly T[],
  audiencia: string,
  formato: string,
): { anterior: T | null; proxima: T | null } {
  const indice = posicoes.findIndex((p) => p.audiencia === audiencia && p.formato === formato);
  if (indice === -1) return { anterior: null, proxima: null };
  return { anterior: posicoes[indice - 1] ?? null, proxima: posicoes[indice + 1] ?? null };
}
```

- [ ] **Step 4: Implementar `lib/revisor.ts`**

Create `web/src/lib/revisor.ts`:

```ts
// O nome de quem está revisando, guardado só neste navegador (não há login). Sem
// armazenamento (janela privada, dados bloqueados), o nome vale só para esta sessão.

const CHAVE = "suno.revisor";

export function lerRevisor(): string {
  try {
    return window.localStorage.getItem(CHAVE) ?? "";
  } catch {
    return "";
  }
}

export function guardarRevisor(nome: string): void {
  try {
    window.localStorage.setItem(CHAVE, nome);
  } catch {
    // sem armazenamento: o nome não persiste, e a decisão segue valendo
  }
}
```

- [ ] **Step 5: Rodar e ver passar**

Run (em `web/`): `npx vitest run`
Expected: todos os testes de `matriz.test.ts` passam (`27 passed`, contando os `it`).

Run (em `web/`): `npx tsc --noEmit -p tsconfig.app.json`
Expected: sem erros.

- [ ] **Step 6: Checkpoint**

Run (na raiz): `uv run python scripts/vocabulario.py | tail -1` → mesmo número da Tarefa 1. Não commite.

---

## Task 9: Camada de dados, rótulos e componentes compartilhados no tema escuro

**Files:**
- Modify: `web/src/dados/cliente.ts`
- Rewrite: `web/src/texto/rotulos.ts`, `web/src/componentes/EstadoRequisicao.tsx`, `web/src/componentes/VereditoCartao.tsx`, `web/src/componentes/Reprovacao.tsx`, `web/src/componentes/Ancoras.tsx`
- Create: `web/src/componentes/Chip.tsx`

**Interfaces:**
- Consumes: `lib/matriz.ts` (`TomChip`); tipos gerados da Tarefa 6.
- Produces (`dados/cliente.ts`): tipos `PosicaoResumo`, `DecisaoHumana`, `EstadoDecisao`, `FormatoExportacao`, `StatusSaida`; `obterResumo(id): Promise<ExecucaoResumo>`; `renomearExecucao(id, nome): Promise<ExecucaoResumo>`; `registrarDecisao(id, audiencia, formato, { estado, motivo, revisor }): Promise<DecisaoHumana>`; `urlDeExportacao(id, formato): string`. Erros de API passam a trazer o `detail` do servidor como mensagem.
- Produces (`texto/rotulos.ts`): os já existentes (`rotuloMetrica`, `descreverMedida`, `rotuloDestino`, `corDestino`, `rotuloMotivo`, `rotuloAudiencia`, `rotuloFormato`, `formatarNumero`) mais `descreverFaixa(faixa)`, `resumirFaixa(faixa)`, `rotuloModo(modo)`, `rotuloProvedor(provedor)`, `formatarDataCurta(iso)`, `pluralizar(n, singular, plural)`.
- Produces (componentes): `Chip({ tom?, children })` com `tom: TomChip`; `Carregando`, `MensagemErro`, `VereditoCartao`, `Reprovacao`, `Ancoras` com as mesmas props de antes.

- [ ] **Step 1: Mensagem de erro com o `detail` do servidor, tipos e funções novas**

Em `web/src/dados/cliente.ts`, Edit 1. `old_string`:

```ts
  const detalhe =
    resultado.error !== undefined && resultado.error !== null
      ? JSON.stringify(resultado.error)
      : resultado.response.statusText;
  throw new ErroApi(resultado.response.status, detalhe);
}
```

`new_string`:

```ts
  throw new ErroApi(
    resultado.response.status,
    detalheDoErro(resultado.error, resultado.response.statusText),
  );
}

/** O FastAPI responde `{"detail": "..."}`: a tela mostra a frase, não o JSON. */
function detalheDoErro(erro: unknown, alternativa: string): string {
  if (erro && typeof erro === "object" && "detail" in erro) {
    const detalhe = (erro as { detail: unknown }).detail;
    if (typeof detalhe === "string") return detalhe;
  }
  return erro === undefined || erro === null ? alternativa : JSON.stringify(erro);
}
```

Edit 2. `old_string`:

```ts
export type Saude = components["schemas"]["Saude"];
```

`new_string`:

```ts
export type Saude = components["schemas"]["Saude"];
export type PosicaoResumo = components["schemas"]["PosicaoResumo"];
export type DecisaoHumana = components["schemas"]["DecisaoHumana"];
export type EstadoDecisao = components["schemas"]["EstadoDecisao"];
export type FormatoExportacao = components["schemas"]["FormatoExportacao"];
export type StatusSaida = ExecucaoResumo["status"];
```

Edit 3: acrescente ao fim do arquivo (depois de `urlDoArquivo`). `old_string`:

```ts
  return `/api/execucoes/${encodeURIComponent(identificador)}/arquivos/${relativo}`;
}
```

`new_string`:

```ts
  return `/api/execucoes/${encodeURIComponent(identificador)}/arquivos/${relativo}`;
}

export function obterResumo(identificador: string): Promise<ExecucaoResumo> {
  return extrair(
    api.GET("/api/execucoes/{identificador}/resumo", { params: { path: { identificador } } }),
  );
}

export function renomearExecucao(identificador: string, nome: string): Promise<ExecucaoResumo> {
  return extrair(
    api.PATCH("/api/execucoes/{identificador}", {
      params: { path: { identificador } },
      body: { nome },
    }),
  );
}

export function registrarDecisao(
  identificador: string,
  audiencia: Audiencia,
  formato: Formato,
  corpo: { estado: EstadoDecisao; motivo: string | null; revisor: string | null },
): Promise<DecisaoHumana> {
  return extrair(
    api.POST("/api/execucoes/{identificador}/celulas/{audiencia}/{formato}/decisao", {
      params: { path: { identificador, audiencia, formato } },
      body: corpo,
    }),
  );
}

/** Endereço do download; o navegador baixa direto, sem passar pelo cliente tipado. */
export function urlDeExportacao(identificador: string, formato: FormatoExportacao): string {
  return `/api/execucoes/${encodeURIComponent(identificador)}/exportar?formato=${formato}`;
}
```

- [ ] **Step 2: Reescrever `rotulos.ts`**

Rewrite `web/src/texto/rotulos.ts`:

```ts
// Traduz os valores do domínio (dominio.py, via o schema gerado) para o rótulo em
// palavras que a tela mostra ao lado do número — ver docs/ARQUITETURA.md, seção "A interface".
import type {
  Audiencia,
  Destino,
  Faixa,
  Formato,
  Medida,
  Metrica,
  MotivoReprovacao,
} from "../dados/cliente";

const NUMERO = new Intl.NumberFormat("pt-BR", {
  maximumFractionDigits: 2,
  minimumFractionDigits: 0,
});

export function formatarNumero(valor: number | null | undefined): string {
  return valor === null || valor === undefined ? "—" : NUMERO.format(valor);
}

/** "09/10 · 14:32". */
export function formatarDataCurta(iso: string): string {
  const data = new Date(iso);
  const dia = data.toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" });
  const hora = data.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
  return `${dia} · ${hora}`;
}

export function pluralizar(quantidade: number, singular: string, plural: string): string {
  return `${quantidade} ${quantidade === 1 ? singular : plural}`;
}

export function rotuloMetrica(metrica: Metrica): string {
  switch (metrica) {
    case "flesch_br":
      return "Flesch-BR";
    case "densidade":
      return "Densidade";
    case "aderencia":
      return "Aderência";
    case "recomendacao":
      return "Recomendação";
    case "integridade":
      return "Integridade da extração";
  }
}

/** O veredito em palavras; o número ao lado é responsabilidade de quem exibe (VereditoCartao). */
export function descreverMedida(medida: Medida): string {
  if (medida.estado === "ausente") {
    return "sem base para medir";
  }
  if (medida.estado === "revisao_humana") {
    return "aguardando desempate (H3)";
  }
  const positivo = medida.atingiu === true;
  switch (medida.metrica) {
    case "flesch_br":
      return positivo ? "Flesch-BR na faixa" : "Flesch-BR fora da faixa";
    case "densidade":
      return positivo ? "Densidade adequada ao Léxico" : "Densidade abaixo do Limiar";
    case "aderencia":
      return positivo ? "Alta aderência factual" : "Aderência abaixo do Limiar";
    case "recomendacao":
      return positivo ? "Sem Recomendação ✓" : "Recomendação detectada";
    case "integridade":
      return positivo ? "Extração íntegra" : "Falha de extração";
  }
}

/** A faixa por extenso: "a partir de 50", "até 1", "entre 10 e 20". */
export function descreverFaixa(faixa: Faixa | null | undefined): string {
  const minimo = faixa?.minimo ?? null;
  const maximo = faixa?.maximo ?? null;
  if (minimo === null && maximo === null) return "sem Limiar definido";
  if (minimo !== null && maximo !== null) {
    return `entre ${formatarNumero(minimo)} e ${formatarNumero(maximo)}`;
  }
  if (minimo !== null) return `a partir de ${formatarNumero(minimo)}`;
  return `até ${formatarNumero(maximo)}`;
}

/** A faixa em poucos caracteres, para ficar ao lado do valor: "≥ 50", "≤ 1". */
export function resumirFaixa(faixa: Faixa | null | undefined): string {
  const minimo = faixa?.minimo ?? null;
  const maximo = faixa?.maximo ?? null;
  if (minimo === null && maximo === null) return "";
  if (minimo !== null && maximo !== null) {
    return `${formatarNumero(minimo)}–${formatarNumero(maximo)}`;
  }
  if (minimo !== null) return `≥ ${formatarNumero(minimo)}`;
  return `≤ ${formatarNumero(maximo)}`;
}

export function rotuloDestino(destino: Destino): string {
  switch (destino) {
    case "aprovado":
      return "Aprovado";
    case "reprovado_corrigivel":
      return "Reprovado · correção possível";
    case "reprovado_revisao_humana":
      return "Reprovado · revisão humana";
  }
}

export function corDestino(destino: Destino): string {
  switch (destino) {
    case "aprovado":
      return "border-ok/40 bg-ok/10 text-texto";
    case "reprovado_corrigivel":
      return "border-alerta/40 bg-alerta/10 text-texto";
    case "reprovado_revisao_humana":
      return "border-suno/45 bg-suno/10 text-texto";
  }
}

export function rotuloMotivo(motivo: MotivoReprovacao): string {
  switch (motivo) {
    case "flesch_br":
      return "Flesch-BR fora da faixa";
    case "densidade":
      return "Densidade abaixo do Limiar";
    case "aderencia":
      return "Aderência abaixo do Limiar";
    case "recomendacao":
      return "Recomendação detectada";
    case "falha_de_extracao":
      return "Falha de extração";
  }
}

export function rotuloAudiencia(audiencia: Audiencia | string): string {
  switch (audiencia) {
    case "iniciante":
      return "Iniciante";
    case "intermediario":
      return "Intermediário";
    case "avancado":
      return "Avançado";
    default:
      return audiencia;
  }
}

export function rotuloFormato(formato: Formato | string): string {
  switch (formato) {
    case "texto_analitico":
      return "Texto analítico";
    case "carrossel":
      return "Carrossel";
    case "roteiro":
      return "Roteiro";
    default:
      return formato;
  }
}

/** Como a curadoria escolheu o que entrou: um destaque ou vários itens unidos. */
export function rotuloModo(modo: string | null | undefined): string | null {
  switch (modo) {
    case "separada":
      return "Destaque único";
    case "unida":
      return "Visão unida";
    default:
      return null;
  }
}

/** `falso` é a demo sem rede; qualquer outro é provedor de verdade. */
export function rotuloProvedor(provedor: string): string {
  return provedor === "falso" ? "Demo" : `Real · ${provedor}`;
}
```

- [ ] **Step 3: `Chip`**

Create `web/src/componentes/Chip.tsx`:

```tsx
// O selo pequeno que acompanha quase tudo na tela: estado do Laudo, decisão, fonte, modo.
import type { ReactNode } from "react";
import type { TomChip } from "../lib/matriz";

const BORDA_E_TEXTO: Record<TomChip, string> = {
  neutro: "border-linha text-suave",
  forte: "border-transparent bg-cartao-2 text-texto",
  ok: "border-linha text-suave",
  alerta: "border-linha text-suave",
  ruim: "border-suno/45 text-[#ff8b82]",
};

const PONTO: Partial<Record<TomChip, string>> = {
  ok: "bg-ok",
  alerta: "bg-alerta",
  ruim: "bg-suno",
};

export default function Chip({ tom = "neutro", children }: { tom?: TomChip; children: ReactNode }) {
  const ponto = PONTO[tom];
  return (
    <span
      className={`inline-flex items-center gap-1.5 whitespace-nowrap rounded-full border px-2 py-px text-[10.5px] ${BORDA_E_TEXTO[tom]}`}
    >
      {ponto && <span className={`h-1.5 w-1.5 rounded-full ${ponto}`} />}
      {children}
    </span>
  );
}
```

- [ ] **Step 4: Componentes compartilhados no tema escuro**

Rewrite `web/src/componentes/EstadoRequisicao.tsx`:

```tsx
// Estados de carregando/erro reutilizados em toda página — nada quebra sem rede ou sem dado.
export function Carregando({ rotulo = "Carregando…" }: { rotulo?: string }) {
  return (
    <div className="flex items-center gap-2 px-5 py-8 text-sm text-suave">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-linha border-t-texto" />
      {rotulo}
    </div>
  );
}

export function MensagemErro({ erro }: { erro: Error }) {
  return (
    <div className="m-5 rounded-xl border border-suno/45 bg-suno/10 px-4 py-3 text-sm text-[#ffb3ad]">
      Não foi possível carregar: {erro.message}
    </div>
  );
}
```

Rewrite `web/src/componentes/VereditoCartao.tsx`:

```tsx
// O veredito em palavras, com o número ao lado — a marca da tela (ver ARQUITETURA.md,
// seção "A interface"). Destaque visual reservado à dimensão de Recomendação: é a linha
// que não se cruza (CLAUDE.md).
import type { Medida } from "../dados/cliente";
import { descreverMedida, formatarNumero, rotuloMetrica } from "../texto/rotulos";

export default function VereditoCartao({ medida }: { medida: Medida }) {
  const destaque = medida.metrica === "recomendacao";
  return (
    <div
      className={`flex items-center justify-between gap-3 rounded-lg border px-3 py-2 text-sm ${
        destaque ? "border-suno/60 bg-suno/10 font-medium" : "border-linha bg-cartao"
      }`}
    >
      <span>
        <span className="text-suave">{rotuloMetrica(medida.metrica)}: </span>
        {descreverMedida(medida)}
      </span>
      <span className="shrink-0 font-mono tabular-nums text-suave">
        {formatarNumero(medida.valor)}
      </span>
    </div>
  );
}
```

Rewrite `web/src/componentes/Reprovacao.tsx`:

```tsx
// A reprovação como view de primeira classe (ADR 0013): para cada motivo, a métrica, o
// Limiar (Faixa), o valor medido e a distância, mais as observações e a instrução de
// Correcao que o Gerador recebeu. Medida `ausente` nunca aparece como zero.
import type { Laudo } from "../dados/cliente";
import {
  descreverFaixa,
  formatarNumero,
  rotuloMetrica,
  rotuloMotivo,
} from "../texto/rotulos";

export default function Reprovacao({ laudo }: { laudo: Laudo }) {
  if (laudo.destino === "aprovado") {
    return null;
  }

  const motivos = laudo.motivos ?? [];
  const correcoes = laudo.correcoes ?? [];

  return (
    <section className="rounded-2xl border border-suno/45 bg-suno/10 p-4">
      <h3 className="text-base font-semibold text-[#ffb3ad]">Por que reprovou</h3>
      <ul className="mt-2 flex flex-wrap gap-2">
        {motivos.map((motivo) => (
          <li
            key={motivo}
            className="rounded-full bg-suno/25 px-2.5 py-1 text-xs font-medium text-[#ffd0cc]"
          >
            {rotuloMotivo(motivo)}
          </li>
        ))}
      </ul>

      <div className="mt-4 space-y-3">
        {laudo.medidas
          .filter((medida) => medida.atingiu === false || medida.estado !== "medida")
          .map((medida) => (
            <div key={medida.metrica} className="rounded-lg bg-cartao p-3 text-sm">
              <p className="font-medium">{rotuloMetrica(medida.metrica)}</p>
              {medida.estado === "ausente" && <p>sem base para medir</p>}
              {medida.estado === "revisao_humana" && <p>aguardando desempate (H3)</p>}
              {medida.estado === "medida" && (
                <p>
                  Limiar: {descreverFaixa(medida.faixa)} · valor medido:{" "}
                  {formatarNumero(medida.valor)}
                </p>
              )}
              {medida.observacoes && medida.observacoes.length > 0 && (
                <ul className="mt-1 list-inside list-disc text-suave">
                  {medida.observacoes.map((observacao, indice) => (
                    <li key={indice}>{observacao}</li>
                  ))}
                </ul>
              )}
            </div>
          ))}
      </div>

      {correcoes.length > 0 && (
        <div className="mt-4 space-y-2">
          <p className="text-sm font-medium text-[#ffb3ad]">Instrução para a correção</p>
          {correcoes.map((correcao) => (
            <div key={correcao.metrica} className="rounded-lg bg-cartao p-3 text-sm">
              <p>{correcao.instrucao}</p>
              {correcao.distancia !== null && correcao.distancia !== undefined && (
                <p className="text-suave">
                  distância até o Limiar: {formatarNumero(correcao.distancia)}
                </p>
              )}
            </div>
          ))}
        </div>
      )}

      {laudo.destino === "reprovado_revisao_humana" && (
        <p className="mt-3 text-sm text-[#ffb3ad]">
          Foi para a revisão humana: duas rodadas de correção não resolveram, ou a extração
          falhou.
        </p>
      )}
    </section>
  );
}
```

Rewrite `web/src/componentes/Ancoras.tsx`:

```tsx
// As Âncoras ao lado da Célula: chave, rótulo, valor citado e o trecho da Ata de origem.
import type { AncoraNumerica } from "../dados/cliente";

export default function Ancoras({ ancoras }: { ancoras: AncoraNumerica[] }) {
  if (ancoras.length === 0) {
    return <p className="text-sm text-suave">Nenhuma Âncora citada.</p>;
  }
  return (
    <ul>
      {ancoras.map((ancora) => (
        <li key={ancora.chave} className="border-t border-linha py-2 text-[12px] first:border-t-0">
          <div className="flex items-baseline justify-between gap-2">
            <span className="font-semibold">{ancora.rotulo}</span>
            <span className="whitespace-nowrap font-mono font-bold">
              {ancora.valor_literal} {ancora.unidade}
            </span>
          </div>
          <p className="mt-0.5 text-suave">&ldquo;{ancora.trecho}&rdquo;</p>
        </li>
      ))}
    </ul>
  );
}
```

- [ ] **Step 5: Verificar**

Run (em `web/`): `npx tsc --noEmit -p tsconfig.app.json`
Expected: sem erros. Se `descreverFaixa`/`resumirFaixa` reclamarem do tipo de `faixa` (`Faixa` vem de `dados/cliente`), confira que `Faixa` está exportado lá (está: `export type Faixa = components["schemas"]["Faixa"]`).

Run (em `web/`): `npx vitest run`
Expected: `matriz.test.ts` continua verde.

- [ ] **Step 6: Checkpoint**

Run (na raiz): `uv run python scripts/vocabulario.py | tail -1` → mesmo número. Não commite.

---

## Task 10: Casca nova, guia Saídas e as guias em construção

**Files:**
- Rewrite: `web/src/componentes/Layout.tsx`, `web/src/App.tsx`
- Create: `web/src/componentes/MiniMatriz.tsx`, `web/src/componentes/LinksDeExportacao.tsx`, `web/src/componentes/MenuDoCartao.tsx`, `web/src/componentes/CartaoSaida.tsx`, `web/src/componentes/EmConstrucao.tsx`
- Create: `web/src/paginas/Saidas.tsx`, `web/src/paginas/Fontes.tsx`, `web/src/paginas/Curadoria.tsx`

**Interfaces:**
- Consumes: `listarExecucoes`, `renomearExecucao`, `urlDeExportacao`, `ExecucaoResumo`, `PosicaoResumo`, `AUDIENCIAS`, `FORMATOS` de `dados/cliente`; `estadoDaPosicao`, `chaveDaPosicao`, `contarPosicoes`, `contarAguardando`, `filtrarSaidas`, `maisRecentesPrimeiro`, `FiltroDeStatus` de `lib/matriz`; `Chip`, `Carregando`, `MensagemErro`; `formatarDataCurta`, `pluralizar`, `rotuloModo`, `rotuloProvedor`.
- Produces: `MiniMatriz({ posicoes })` e `LegendaMiniMatriz()` (em `MiniMatriz.tsx`); `LinksDeExportacao({ identificador })`; `MenuDoCartao({ identificador, nome, onRenomeada })`; `CartaoSaida({ saida, onAlterada })`; `EmConstrucao({ titulo, descricao })`; páginas `Saidas`, `Fontes`, `Curadoria` (export default). Rotas `/` (redireciona para `/saidas`), `/fontes`, `/curadoria`, `/saidas`.

- [ ] **Step 1: `MiniMatriz` e a legenda**

Create `web/src/componentes/MiniMatriz.tsx`:

```tsx
// A Matriz 3×3 em miniatura: a posição do quadradinho é a posição da Célula (Audiências nas
// linhas, Formatos nas colunas). Dá, num relance, o que foi pedido e como está cada Célula.
import { AUDIENCIAS, FORMATOS, type PosicaoResumo } from "../dados/cliente";
import { chaveDaPosicao, estadoDaPosicao, type EstadoPosicao } from "../lib/matriz";

const COR_DO_QUADRADO: Record<EstadoPosicao, string> = {
  aprovada: "border-ok bg-ok",
  aguardando: "border-[#5a5a60] bg-[#5a5a60]",
  revisao: "border-alerta bg-alerta",
  reprovada: "border-suno bg-suno",
};

const TEXTO_DO_ESTADO: Record<EstadoPosicao, string> = {
  aprovada: "você aprovou",
  aguardando: "espera a sua decisão",
  revisao: "revisão humana",
  reprovada: "reprovada ou parou",
};

export default function MiniMatriz({ posicoes }: { posicoes: PosicaoResumo[] }) {
  const porPosicao = new Map(posicoes.map((p) => [chaveDaPosicao(p.audiencia, p.formato), p]));
  return (
    <div
      className="grid shrink-0 grid-cols-3 grid-rows-3 gap-1"
      role="img"
      aria-label={`Matriz: ${posicoes.length} de 9 Células pedidas`}
    >
      {AUDIENCIAS.flatMap((audiencia) =>
        FORMATOS.map((formato) => {
          const posicao = porPosicao.get(chaveDaPosicao(audiencia, formato));
          const classe = posicao
            ? COR_DO_QUADRADO[estadoDaPosicao(posicao)]
            : "border-dashed border-[#3b3b40]";
          const titulo = posicao ? TEXTO_DO_ESTADO[estadoDaPosicao(posicao)] : "não pedida";
          return (
            <span
              key={`${audiencia}:${formato}`}
              title={titulo}
              className={`block h-[17px] w-[17px] rounded border-[1.5px] ${classe}`}
            />
          );
        }),
      )}
    </div>
  );
}

export function LegendaMiniMatriz() {
  const itens: ReadonlyArray<{ classe: string; texto: string }> = [
    { classe: "border-ok bg-ok", texto: "você aprovou" },
    { classe: "border-[#5a5a60] bg-[#5a5a60]", texto: "espera a sua decisão" },
    { classe: "border-alerta bg-alerta", texto: "revisão humana" },
    { classe: "border-suno bg-suno", texto: "reprovada ou parou" },
    { classe: "border-dashed border-[#3b3b40]", texto: "não pedida" },
  ];
  return (
    <div className="mt-5 flex flex-wrap items-center gap-x-4 gap-y-1.5 border-t border-linha pt-3 text-[11px] text-suave">
      <span>Mini-Matriz:</span>
      {itens.map((entrada) => (
        <span key={entrada.texto} className="flex items-center gap-1.5">
          <span className={`inline-block h-[11px] w-[11px] rounded-[3px] border-[1.5px] ${entrada.classe}`} />
          {entrada.texto}
        </span>
      ))}
    </div>
  );
}
```

- [ ] **Step 2: Links de exportação e menu do cartão**

Create `web/src/componentes/LinksDeExportacao.tsx`:

```tsx
// Os três formatos de exportação de uma Saída. O navegador baixa direto da API.
import { urlDeExportacao, type FormatoExportacao } from "../dados/cliente";

const OPCOES: ReadonlyArray<{ formato: FormatoExportacao; rotulo: string }> = [
  { formato: "json", rotulo: "JSON (dados completos)" },
  { formato: "md", rotulo: "Markdown (para ler)" },
  { formato: "zip", rotulo: "ZIP (tudo, com o Pacote)" },
];

export default function LinksDeExportacao({ identificador }: { identificador: string }) {
  return (
    <ul className="space-y-1">
      {OPCOES.map((opcao) => (
        <li key={opcao.formato}>
          <a
            href={urlDeExportacao(identificador, opcao.formato)}
            download
            className="text-sm text-texto underline-offset-2 hover:underline"
          >
            {opcao.rotulo}
          </a>
        </li>
      ))}
    </ul>
  );
}
```

Create `web/src/componentes/MenuDoCartao.tsx`:

```tsx
// O menu "···" do cartão de uma Saída: renomear e exportar.
import { useState, type FormEvent } from "react";
import { renomearExecucao } from "../dados/cliente";
import LinksDeExportacao from "./LinksDeExportacao";

export default function MenuDoCartao({
  identificador,
  nome,
  onRenomeada,
}: {
  identificador: string;
  nome: string;
  onRenomeada: () => void;
}) {
  const [novoNome, definirNovoNome] = useState(nome);
  const [enviando, definirEnviando] = useState(false);
  const [erro, definirErro] = useState<string | null>(null);

  function salvar(evento: FormEvent) {
    evento.preventDefault();
    definirEnviando(true);
    definirErro(null);
    renomearExecucao(identificador, novoNome)
      .then(onRenomeada)
      .catch((falha: unknown) => {
        definirErro(falha instanceof Error ? falha.message : String(falha));
      })
      .finally(() => definirEnviando(false));
  }

  return (
    <details className="relative z-10">
      <summary
        aria-label="Mais ações"
        className="cursor-pointer list-none px-1 tracking-[2px] text-suave [&::-webkit-details-marker]:hidden"
      >
        ···
      </summary>
      <div className="absolute right-0 top-6 z-20 w-64 space-y-3 rounded-xl border border-linha bg-cartao-2 p-3 shadow-xl">
        <form onSubmit={salvar} className="space-y-2">
          <label
            htmlFor={`nome-${identificador}`}
            className="block text-[10.5px] font-bold uppercase tracking-wider text-suave"
          >
            Renomear
          </label>
          <input
            id={`nome-${identificador}`}
            value={novoNome}
            onChange={(evento) => definirNovoNome(evento.target.value)}
            className="w-full rounded-lg border border-linha bg-fundo px-2.5 py-1.5 text-sm"
          />
          <button
            type="submit"
            disabled={enviando}
            className="rounded-full bg-suno px-3.5 py-1.5 text-xs font-bold text-white disabled:opacity-50"
          >
            Salvar nome
          </button>
          {erro && <p className="text-xs text-[#ffb3ad]">{erro}</p>}
        </form>
        <div>
          <p className="mb-1 text-[10.5px] font-bold uppercase tracking-wider text-suave">
            Exportar
          </p>
          <LinksDeExportacao identificador={identificador} />
        </div>
      </div>
    </details>
  );
}
```

- [ ] **Step 3: `CartaoSaida`**

Create `web/src/componentes/CartaoSaida.tsx`:

```tsx
// Uma Saída na lista: nome, fonte, modo, provedor, mini-Matriz e estado. O cartão inteiro é
// clicável por um link esticado no título; o menu "···" fica acima dele.
import { Link } from "react-router-dom";
import type { ExecucaoResumo } from "../dados/cliente";
import { contarPosicoes } from "../lib/matriz";
import { formatarDataCurta, pluralizar, rotuloModo, rotuloProvedor } from "../texto/rotulos";
import Chip from "./Chip";
import MenuDoCartao from "./MenuDoCartao";
import MiniMatriz from "./MiniMatriz";

export default function CartaoSaida({
  saida,
  onAlterada,
}: {
  saida: ExecucaoResumo;
  onAlterada: () => void;
}) {
  const contagem = contarPosicoes(saida.posicoes);
  const detalhes = [`você aprovou ${contagem.aprovadasPorVoce}`];
  if (contagem.aguardando > 0) {
    detalhes.push(`${contagem.aguardando} ${contagem.aguardando === 1 ? "espera" : "esperam"}`);
  }
  if (contagem.bloqueadas > 0) {
    detalhes.push(`${contagem.bloqueadas} ${contagem.bloqueadas === 1 ? "bloqueada" : "bloqueadas"}`);
  }
  const modo = rotuloModo(saida.modo);

  return (
    <article className="relative flex min-w-0 flex-col gap-2 rounded-2xl border border-transparent bg-cartao p-3.5 transition hover:border-suno/45">
      <div className="flex items-start gap-2">
        <h2 className="text-[13.5px] font-bold leading-snug">
          <Link
            to={`/saidas/${encodeURIComponent(saida.identificador)}`}
            className="after:absolute after:inset-0 after:content-['']"
          >
            {saida.nome}
          </Link>
        </h2>
        <div className="ml-auto">
          <MenuDoCartao
            identificador={saida.identificador}
            nome={saida.nome}
            onRenomeada={onAlterada}
          />
        </div>
      </div>
      <div className="flex flex-wrap gap-1.5">
        <Chip tom="forte">{saida.ata}</Chip>
        {modo && <Chip>{modo}</Chip>}
        <Chip>{rotuloProvedor(saida.provedor)}</Chip>
      </div>
      <div className="my-0.5 flex items-center gap-3.5">
        <MiniMatriz posicoes={saida.posicoes} />
        <p className="text-[11.5px] leading-relaxed text-suave">
          <b className="text-texto">{pluralizar(contagem.total, "Célula", "Células")}</b>
          <br />
          {detalhes.join(" · ")}
        </p>
      </div>
      <div className="mt-auto flex items-center gap-2 pt-1">
        {saida.status === "aguardando_revisao" ? (
          <Chip tom="alerta">Aguardando revisão</Chip>
        ) : (
          <Chip tom="ok">Concluída</Chip>
        )}
        <span className="ml-auto text-[11px] text-suave">{formatarDataCurta(saida.iniciada_em)}</span>
      </div>
    </article>
  );
}
```

- [ ] **Step 4: `EmConstrucao` e as páginas das guias**

Create `web/src/componentes/EmConstrucao.tsx`:

```tsx
// Guia que ainda não tem conteúdo: avisa e diz o que vai fazer.
export default function EmConstrucao({
  titulo,
  descricao,
}: {
  titulo: string;
  descricao: string;
}) {
  return (
    <div className="px-5 py-4">
      <h1 className="text-[17px] font-bold">{titulo}</h1>
      <div className="mt-4 rounded-2xl border border-dashed border-linha p-6 text-sm text-suave">
        <p className="font-semibold text-texto">Esta guia chega em breve.</p>
        <p className="mt-1">{descricao}</p>
      </div>
    </div>
  );
}
```

Create `web/src/paginas/Fontes.tsx`:

```tsx
// A guia Fontes ("/fontes"): os documentos de onde o conteúdo nasce. Ainda sem conteúdo.
import EmConstrucao from "../componentes/EmConstrucao";

export default function Fontes() {
  return (
    <EmConstrucao
      titulo="Fontes"
      descricao="Aqui vão ficar as Atas do Copom, os Fatos Relevantes da CVM e os documentos que você importar, em fileiras de cartões."
    />
  );
}
```

Create `web/src/paginas/Curadoria.tsx`:

```tsx
// A guia Curadoria ("/curadoria"): escolher o que entra, configurar e gerar. Ainda sem conteúdo.
import EmConstrucao from "../componentes/EmConstrucao";

export default function Curadoria() {
  return (
    <EmConstrucao
      titulo="Curadoria"
      descricao="Aqui você vai escolher o destaque ou a visão unida, marcar as Células na Matriz e acompanhar a geração."
    />
  );
}
```

- [ ] **Step 5: A página `Saidas`**

Create `web/src/paginas/Saidas.tsx`:

```tsx
// A guia Saídas ("/saidas"): as Saídas registradas, cada uma com nome, fonte, estado e a
// mini-Matriz. O conteúdo só aparece ao abrir a Saída (spec do front, seção 4.3).
import { useMemo, useState } from "react";
import { listarExecucoes } from "../dados/cliente";
import { usarRequisicao } from "../ganchos/usarRequisicao";
import { Carregando, MensagemErro } from "../componentes/EstadoRequisicao";
import CartaoSaida from "../componentes/CartaoSaida";
import { LegendaMiniMatriz } from "../componentes/MiniMatriz";
import {
  contarAguardando,
  filtrarSaidas,
  maisRecentesPrimeiro,
  type FiltroDeStatus,
} from "../lib/matriz";

const FILTROS: ReadonlyArray<{ valor: FiltroDeStatus; rotulo: string }> = [
  { valor: "todas", rotulo: "Todas" },
  { valor: "aguardando_revisao", rotulo: "Aguardando revisão" },
  { valor: "concluida", rotulo: "Concluídas" },
];

export default function Saidas() {
  const [recarga, recarregar] = useState(0);
  const estado = usarRequisicao(listarExecucoes, [recarga]);
  const [busca, definirBusca] = useState("");
  const [filtro, definirFiltro] = useState<FiltroDeStatus>("todas");

  const saidas = useMemo(() => (estado.situacao === "pronto" ? estado.dados : []), [estado]);
  const visiveis = useMemo(
    () => maisRecentesPrimeiro(filtrarSaidas(saidas, { busca, status: filtro })),
    [saidas, busca, filtro],
  );

  if (estado.situacao === "carregando") return <Carregando rotulo="Carregando Saídas…" />;
  if (estado.situacao === "erro") return <MensagemErro erro={estado.erro} />;

  if (saidas.length === 0) {
    return (
      <div className="px-5 py-4">
        <h1 className="text-[17px] font-bold">Saídas</h1>
        <p className="mt-3 text-sm text-suave">
          Nenhuma Saída registrada em <code>data/execucoes/</code>.
        </p>
      </div>
    );
  }

  const aguardando = contarAguardando(saidas);

  return (
    <div className="px-5 py-4">
      <div className="mb-3 flex items-baseline gap-3">
        <h1 className="text-[17px] font-bold">Saídas</h1>
        <span className="text-sm text-suave">
          {saidas.length} {saidas.length === 1 ? "registrada" : "registradas"}
        </span>
      </div>

      <div className="mb-4 flex flex-wrap items-center gap-2">
        <input
          type="search"
          value={busca}
          onChange={(evento) => definirBusca(evento.target.value)}
          placeholder="Buscar pelo nome…"
          className="w-full max-w-xs rounded-[10px] border border-linha bg-cartao px-3 py-1.5 text-sm placeholder:text-suave"
        />
        {FILTROS.map((opcao) => (
          <button
            key={opcao.valor}
            type="button"
            onClick={() => definirFiltro(opcao.valor)}
            className={`rounded-[10px] border px-3 py-1.5 text-xs ${
              filtro === opcao.valor ? "border-suno bg-suno/15" : "border-linha"
            }`}
          >
            {opcao.rotulo}
            {opcao.valor === "aguardando_revisao" && aguardando > 0 && (
              <b className="ml-1 text-suno">{aguardando}</b>
            )}
          </button>
        ))}
      </div>

      {visiveis.length === 0 ? (
        <p className="text-sm text-suave">Nenhuma Saída com esse filtro.</p>
      ) : (
        <div className="grid gap-3.5 sm:grid-cols-2 xl:grid-cols-3">
          {visiveis.map((saida) => (
            <CartaoSaida
              key={saida.identificador}
              saida={saida}
              onAlterada={() => recarregar((atual) => atual + 1)}
            />
          ))}
        </div>
      )}

      <LegendaMiniMatriz />
    </div>
  );
}
```

- [ ] **Step 6: `Layout` com menu lateral e `App` com as rotas novas**

Rewrite `web/src/componentes/Layout.tsx`:

```tsx
// A casca: menu lateral com as três guias (Fontes, Curadoria, Saídas) e a área de conteúdo.
// O número vermelho em Saídas conta as Saídas aguardando revisão e se atualiza a cada
// navegação.
import type { ReactNode } from "react";
import { NavLink, useLocation } from "react-router-dom";
import { listarExecucoes } from "../dados/cliente";
import { usarRequisicao } from "../ganchos/usarRequisicao";
import { contarAguardando } from "../lib/matriz";

const GUIAS = [
  { para: "/fontes", rotulo: "Fontes" },
  { para: "/curadoria", rotulo: "Curadoria" },
  { para: "/saidas", rotulo: "Saídas" },
] as const;

export default function Layout({ children }: { children: ReactNode }) {
  const { pathname } = useLocation();
  const estado = usarRequisicao(listarExecucoes, [pathname]);
  const aguardando = estado.situacao === "pronto" ? contarAguardando(estado.dados) : 0;

  return (
    <div className="flex min-h-screen bg-fundo text-texto">
      <aside className="sticky top-0 flex h-screen w-[172px] shrink-0 flex-col gap-1 border-r border-linha bg-lateral px-2.5 py-3.5">
        <div className="px-2 pb-4 pt-1 text-[15px] font-bold tracking-[0.28em]">
          <span className="font-normal text-suno">(</span> SUNO{" "}
          <span className="font-normal text-suno">)</span>
        </div>
        {GUIAS.map((guia) => (
          <NavLink
            key={guia.para}
            to={guia.para}
            className={({ isActive }) =>
              `flex items-center gap-2.5 rounded-[9px] px-2.5 py-2 text-[13px] ${
                isActive ? "bg-suno/15 font-semibold text-texto" : "text-suave hover:text-texto"
              }`
            }
          >
            {({ isActive }) => (
              <>
                <span
                  className={`h-1.5 w-1.5 rounded-full ${isActive ? "bg-suno" : "bg-linha"}`}
                />
                {guia.rotulo}
                {guia.para === "/saidas" && aguardando > 0 && (
                  <b className="ml-auto rounded-full bg-suno px-1.5 text-[10px] font-semibold text-white">
                    {aguardando}
                  </b>
                )}
              </>
            )}
          </NavLink>
        ))}
      </aside>
      <main className="min-w-0 flex-1">{children}</main>
    </div>
  );
}
```

Rewrite `web/src/App.tsx` (as páginas `SaidaAberta` e `CelulaAberta` entram nas Tarefas 11 e 12; por ora as rotas antigas de execução continuam apontando para as páginas antigas):

```tsx
import { Link, Navigate, Route, Routes } from "react-router-dom";
import Layout from "./componentes/Layout";
import Curadoria from "./paginas/Curadoria";
import Fontes from "./paginas/Fontes";
import Saidas from "./paginas/Saidas";
import Execucoes from "./paginas/Execucoes";
import Matriz from "./paginas/Matriz";
import CelulaVista from "./paginas/CelulaVista";
import Filas from "./paginas/Filas";
import Pacotes from "./paginas/Pacotes";

function NaoEncontrada() {
  return (
    <div className="px-5 py-12 text-center">
      <p className="text-lg font-medium">Página não encontrada.</p>
      <Link to="/saidas" className="mt-2 inline-block text-suno hover:underline">
        Voltar para as Saídas
      </Link>
    </div>
  );
}

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Navigate to="/saidas" replace />} />
        <Route path="/fontes" element={<Fontes />} />
        <Route path="/curadoria" element={<Curadoria />} />
        <Route path="/saidas" element={<Saidas />} />
        {/* Rotas antigas, removidas na Tarefa 13. */}
        <Route path="/execucoes" element={<Execucoes />} />
        <Route path="/execucoes/:id" element={<Matriz />} />
        <Route path="/execucoes/:id/celulas/:audiencia/:formato" element={<CelulaVista />} />
        <Route path="/execucoes/:id/filas" element={<Filas />} />
        <Route path="/execucoes/:id/pacotes" element={<Pacotes />} />
        <Route path="*" element={<NaoEncontrada />} />
      </Routes>
    </Layout>
  );
}
```

- [ ] **Step 7: Verificar**

Run (em `web/`): `npx tsc --noEmit -p tsconfig.app.json`
Expected: sem erros.

Run (em `web/`): `npx vitest run`
Expected: verde.

Run (em `web/`): `npm run build`
Expected: conclui sem erro.

- [ ] **Step 8: Checkpoint**

Run (na raiz): `uv run python scripts/vocabulario.py | tail -1` → mesmo número da Tarefa 1; e `uv run python scripts/vocabulario.py | grep -E "web.src.(lib|componentes|paginas)"` não imprime nada. Não commite.

---

## Task 11: Saída aberta (a Matriz 3×3)

**Files:**
- Create: `web/src/componentes/CelulaDaMatriz.tsx`, `web/src/paginas/SaidaAberta.tsx`
- Modify: `web/src/App.tsx`

**Interfaces:**
- Consumes: `obterResumo`, `renomearExecucao`, `ExecucaoResumo`, `PosicaoResumo`, `AUDIENCIAS`, `FORMATOS`; `chaveDaPosicao`, `chipsDaPosicao`, `contarPosicoes`; `Chip`, `LinksDeExportacao`, `Carregando`, `MensagemErro`; `pluralizar`, `rotuloAudiencia`, `rotuloFormato`, `rotuloModo`, `rotuloProvedor`, `formatarDataCurta`.
- Produces: `CelulaDaMatriz({ identificador, posicao })`; página `SaidaAberta` na rota `/saidas/:id`.

- [ ] **Step 1: `CelulaDaMatriz`**

Create `web/src/componentes/CelulaDaMatriz.tsx`:

```tsx
// Um cartão da Matriz da Saída aberta: só o estado (chip do Laudo e chip da decisão humana).
// O conteúdo mora na Célula aberta, um clique adiante.
import { Link } from "react-router-dom";
import type { PosicaoResumo } from "../dados/cliente";
import { chipsDaPosicao } from "../lib/matriz";
import { rotuloAudiencia, rotuloFormato } from "../texto/rotulos";
import Chip from "./Chip";

export default function CelulaDaMatriz({
  identificador,
  posicao,
}: {
  identificador: string;
  posicao: PosicaoResumo;
}) {
  const chips = chipsDaPosicao(posicao);
  return (
    <Link
      to={`/saidas/${encodeURIComponent(identificador)}/celulas/${posicao.audiencia}/${posicao.formato}`}
      className="flex min-h-[64px] flex-col justify-center gap-1.5 rounded-xl bg-cartao p-3 transition hover:ring-1 hover:ring-suno/50"
    >
      <span className="sr-only">
        {rotuloAudiencia(posicao.audiencia)} · {rotuloFormato(posicao.formato)}
      </span>
      <span className="flex flex-wrap gap-1">
        <Chip tom={chips.laudo.tom}>{chips.laudo.texto}</Chip>
      </span>
      <span className="flex flex-wrap gap-1">
        <Chip tom={chips.decisao.tom}>{chips.decisao.texto}</Chip>
      </span>
    </Link>
  );
}
```

- [ ] **Step 2: A página `SaidaAberta`**

Create `web/src/paginas/SaidaAberta.tsx`:

```tsx
// A Saída aberta ("/saidas/:id"): nome editável, exportar, o resumo de estados e a Matriz
// 3×3 (Audiências nas linhas, Formatos nas colunas). Células não pedidas ficam tracejadas
// (spec do front, seção 4.4, opção A).
import { Fragment, useState, type FormEvent } from "react";
import { Link, useParams } from "react-router-dom";
import { AUDIENCIAS, FORMATOS, obterResumo, renomearExecucao } from "../dados/cliente";
import { usarRequisicao } from "../ganchos/usarRequisicao";
import { Carregando, MensagemErro } from "../componentes/EstadoRequisicao";
import CelulaDaMatriz from "../componentes/CelulaDaMatriz";
import Chip from "../componentes/Chip";
import LinksDeExportacao from "../componentes/LinksDeExportacao";
import { chaveDaPosicao, contarPosicoes } from "../lib/matriz";
import {
  formatarDataCurta,
  pluralizar,
  rotuloAudiencia,
  rotuloFormato,
  rotuloModo,
  rotuloProvedor,
} from "../texto/rotulos";

export default function SaidaAberta() {
  const { id } = useParams<{ id: string }>();
  const identificador = id ?? "";
  const [recarga, recarregar] = useState(0);
  const estado = usarRequisicao(() => obterResumo(identificador), [identificador, recarga]);
  const [editando, definirEditando] = useState(false);
  const [novoNome, definirNovoNome] = useState("");
  const [enviando, definirEnviando] = useState(false);
  const [erroDoNome, definirErroDoNome] = useState<string | null>(null);

  if (estado.situacao === "carregando") return <Carregando rotulo="Carregando Saída…" />;
  if (estado.situacao === "erro") return <MensagemErro erro={estado.erro} />;

  const resumo = estado.dados;
  const contagem = contarPosicoes(resumo.posicoes);
  const porPosicao = new Map(resumo.posicoes.map((p) => [chaveDaPosicao(p.audiencia, p.formato), p]));
  const modo = rotuloModo(resumo.modo);

  function comecarEdicao() {
    definirNovoNome(resumo.nome);
    definirErroDoNome(null);
    definirEditando(true);
  }

  function salvarNome(evento: FormEvent) {
    evento.preventDefault();
    definirEnviando(true);
    definirErroDoNome(null);
    renomearExecucao(identificador, novoNome)
      .then(() => {
        definirEditando(false);
        recarregar((atual) => atual + 1);
      })
      .catch((falha: unknown) => {
        definirErroDoNome(falha instanceof Error ? falha.message : String(falha));
      })
      .finally(() => definirEnviando(false));
  }

  return (
    <div className="px-5 py-4">
      <nav className="mb-1 text-[11.5px] text-suave">
        <Link to="/saidas" className="hover:text-texto">
          Saídas
        </Link>{" "}
        › {resumo.nome}
      </nav>

      <div className="flex flex-wrap items-center gap-2.5">
        {editando ? (
          <form onSubmit={salvarNome} className="flex flex-wrap items-center gap-2">
            <input
              value={novoNome}
              onChange={(evento) => definirNovoNome(evento.target.value)}
              aria-label="Novo nome da Saída"
              className="w-72 rounded-lg border border-linha bg-cartao px-2.5 py-1.5 text-sm"
            />
            <button
              type="submit"
              disabled={enviando}
              className="rounded-full bg-suno px-3.5 py-1.5 text-xs font-bold text-white disabled:opacity-50"
            >
              Salvar
            </button>
            <button
              type="button"
              onClick={() => definirEditando(false)}
              className="rounded-full border border-[#55555b] px-3.5 py-1.5 text-xs font-semibold"
            >
              Cancelar
            </button>
            {erroDoNome && <span className="text-xs text-[#ffb3ad]">{erroDoNome}</span>}
          </form>
        ) : (
          <>
            <h1 className="text-[17px] font-bold">{resumo.nome}</h1>
            <button
              type="button"
              onClick={comecarEdicao}
              className="rounded-lg border border-linha px-2 text-[11px] text-suave hover:text-texto"
            >
              renomear
            </button>
          </>
        )}
        <div className="flex-1" />
        <details className="relative">
          <summary className="cursor-pointer list-none rounded-full border border-[#55555b] px-4 py-1.5 text-xs font-semibold [&::-webkit-details-marker]:hidden">
            Exportar
          </summary>
          <div className="absolute right-0 z-20 mt-1 w-56 rounded-xl border border-linha bg-cartao-2 p-3 shadow-xl">
            <LinksDeExportacao identificador={identificador} />
          </div>
        </details>
      </div>

      <div className="mt-2 flex flex-wrap gap-1.5">
        <Chip tom="forte">{resumo.ata}</Chip>
        {modo && <Chip>{modo}</Chip>}
        <Chip>{rotuloProvedor(resumo.provedor)}</Chip>
        <Chip>{formatarDataCurta(resumo.iniciada_em)}</Chip>
      </div>

      <p className="my-3 flex flex-wrap gap-x-4 gap-y-1 text-sm text-suave">
        <span>
          <b className="text-texto">{contagem.total}</b>{" "}
          {contagem.total === 1 ? "Célula" : "Células"}
        </span>
        <span>
          <b className="text-texto">{contagem.laudoOk}</b>{" "}
          {contagem.laudoOk === 1 ? "aprovada" : "aprovadas"} pelo Laudo
        </span>
        <span>
          <b className="text-texto">{contagem.emRevisao}</b> em revisão
        </span>
        <span>
          <b className="text-texto">{contagem.bloqueadas}</b>{" "}
          {contagem.bloqueadas === 1 ? "bloqueada" : "bloqueadas"}
        </span>
        <span>
          você aprovou <b className="text-texto">{contagem.aprovadasPorVoce}</b> de{" "}
          {contagem.total}
        </span>
      </p>

      <div className="grid grid-cols-[84px_repeat(3,minmax(0,1fr))] gap-2.5">
        <div />
        {FORMATOS.map((formato) => (
          <div
            key={formato}
            className="px-0.5 text-[10.5px] font-bold uppercase tracking-wider text-suave"
          >
            {rotuloFormato(formato)}
          </div>
        ))}
        {AUDIENCIAS.map((audiencia) => (
          <Fragment key={audiencia}>
            <div className="flex items-center text-xs font-bold">{rotuloAudiencia(audiencia)}</div>
            {FORMATOS.map((formato) => {
              const posicao = porPosicao.get(chaveDaPosicao(audiencia, formato));
              return posicao ? (
                <CelulaDaMatriz
                  key={`${audiencia}:${formato}`}
                  identificador={identificador}
                  posicao={posicao}
                />
              ) : (
                <div
                  key={`${audiencia}:${formato}`}
                  className="flex min-h-[64px] items-center justify-center rounded-xl border border-dashed border-linha text-[11px] text-[#5d5d63]"
                >
                  não pedida
                </div>
              );
            })}
          </Fragment>
        ))}
      </div>

      <p className="mt-3 text-[11px] text-suave">
        {pluralizar(contagem.total, "Célula pedida", "Células pedidas")} de 9 possíveis. Clique
        numa Célula para ler o conteúdo, conferir o Laudo e decidir.
      </p>
    </div>
  );
}
```

- [ ] **Step 3: Rota nova**

Em `web/src/App.tsx`, Edit 1. `old_string`:

```tsx
import Saidas from "./paginas/Saidas";
```

`new_string`:

```tsx
import Saidas from "./paginas/Saidas";
import SaidaAberta from "./paginas/SaidaAberta";
```

Edit 2. `old_string`:

```tsx
        <Route path="/saidas" element={<Saidas />} />
```

`new_string`:

```tsx
        <Route path="/saidas" element={<Saidas />} />
        <Route path="/saidas/:id" element={<SaidaAberta />} />
```

- [ ] **Step 4: Verificar**

Run (em `web/`): `npx tsc --noEmit -p tsconfig.app.json && npx vitest run`
Expected: sem erros de tipo; testes verdes.

- [ ] **Step 5: Checkpoint**

Run (na raiz): `uv run python scripts/vocabulario.py | tail -1` → mesmo número. Não commite.

---

## Task 12: Célula aberta (duas colunas e a barra de decisão)

**Files:**
- Create: `web/src/componentes/ConteudoCelula.tsx`, `web/src/componentes/SecaoLaudo.tsx`, `web/src/componentes/SecaoAncoras.tsx`, `web/src/componentes/SecaoPacote.tsx`, `web/src/componentes/BarraDecisao.tsx`, `web/src/paginas/CelulaAberta.tsx`
- Modify: `web/src/App.tsx`

**Interfaces:**
- Consumes: `obterExecucao`, `obterAncorasDaCelula`, `listarPacotes`, `aprovarPacote`, `registrarDecisao`, `urlDoArquivo`, `Conteudo`, `Laudo`, `PacotePublicacao`, `DecisaoHumana`, `Audiencia`, `Formato`; `larguraDaBarra`, `celulaBloqueada`, `vizinhas`, `chaveDaPosicao`, `chipsDaPosicao`; `lerRevisor`, `guardarRevisor`; `Chip`, `Ancoras`, `Reprovacao`, `VereditoCartao`, `Carregando`, `MensagemErro`; `formatarNumero`, `resumirFaixa`, `rotuloMetrica`, `rotuloDestino`, `rotuloAudiencia`, `rotuloFormato`, `formatarDataCurta`.
- Produces: `ConteudoCelula({ conteudo })`; `SecaoLaudo({ laudo })`; `SecaoAncoras({ ancoras })`; `SecaoPacote({ identificador, audiencia, formato, pacote, onAtualizado })`; `BarraDecisao({ bloqueada, decisao, enviando, erro, onDecidir })` com `onDecidir(estado: "aprovada" | "reprovada", motivo: string | null, revisor: string)`; página `CelulaAberta` na rota `/saidas/:id/celulas/:audiencia/:formato`.

- [ ] **Step 1: `ConteudoCelula`**

Create `web/src/componentes/ConteudoCelula.tsx`:

```tsx
// O conteúdo de uma Célula, por Formato: Markdown, slides de carrossel ou blocos de roteiro.
// Cada slide mostra a chave da Âncora que ele cita (`dado`).
import ReactMarkdown from "react-markdown";
import type { Conteudo } from "../dados/cliente";
import Chip from "./Chip";

export default function ConteudoCelula({ conteudo }: { conteudo: Conteudo }) {
  if (conteudo.formato === "texto_analitico") {
    return (
      <article className="markdown rounded-2xl bg-cartao p-4">
        <ReactMarkdown>{conteudo.texto ?? ""}</ReactMarkdown>
      </article>
    );
  }

  if (conteudo.formato === "carrossel") {
    const slides = conteudo.slides ?? [];
    return (
      <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
        {slides.map((slide, indice) => (
          <div
            key={indice}
            className="flex min-h-[158px] flex-col gap-1 rounded-xl border border-[#3a2323] bg-linear-to-br from-[#34191a] to-[#1b1011] p-3"
          >
            <span className="text-[9.5px] font-bold tracking-wider text-[#c98f8a]">
              {indice + 1} / {slides.length}
            </span>
            <strong className="text-[12.5px] leading-tight">{slide.titulo}</strong>
            <p className="text-[11px] leading-snug text-[#d6c3c1]">{slide.corpo}</p>
            {slide.dado && (
              <span className="mt-auto self-start">
                <Chip tom="ruim">{slide.dado}</Chip>
              </span>
            )}
          </div>
        ))}
      </div>
    );
  }

  return (
    <ol className="space-y-2">
      {(conteudo.blocos ?? []).map((bloco, indice) => (
        <li key={indice} className="rounded-xl bg-cartao p-3">
          <p className="text-xs font-semibold text-suave">
            {bloco.inicio_s.toFixed(1)}s – {bloco.fim_s.toFixed(1)}s
          </p>
          <p className="mt-1 text-sm">{bloco.fala}</p>
          {bloco.tela && <p className="mt-1 text-xs italic text-suave">{bloco.tela}</p>}
        </li>
      ))}
    </ol>
  );
}
```

- [ ] **Step 2: `SecaoLaudo` e `SecaoAncoras`**

Create `web/src/componentes/SecaoLaudo.tsx`:

```tsx
// O Laudo ao lado do conteúdo: cada métrica com barra, valor medido e a faixa do Limiar.
// A barra fica vermelha quando a métrica não atingiu; cinza quando não há base para medir.
import type { Laudo } from "../dados/cliente";
import { larguraDaBarra } from "../lib/matriz";
import { formatarNumero, resumirFaixa, rotuloDestino, rotuloMetrica } from "../texto/rotulos";
import Chip from "./Chip";

function corDaBarra(atingiu: boolean | null | undefined): string {
  if (atingiu === true) return "bg-ok";
  if (atingiu === false) return "bg-suno";
  return "bg-suave";
}

export default function SecaoLaudo({ laudo }: { laudo: Laudo }) {
  const aprovado = laudo.destino === "aprovado";
  return (
    <section className="rounded-2xl bg-cartao p-3.5">
      <h2 className="mb-2 flex items-center gap-2 text-[12.5px] font-bold">
        Laudo
        <Chip tom={aprovado ? "ok" : "alerta"}>
          {aprovado ? "aprovada" : rotuloDestino(laudo.destino)}
        </Chip>
      </h2>
      <ul>
        {laudo.medidas.map((medida) => (
          <li
            key={medida.metrica}
            className="grid grid-cols-[110px_1fr_auto] items-center gap-2 border-t border-linha py-1.5 text-[11.5px] first:border-t-0"
          >
            <span>{rotuloMetrica(medida.metrica)}</span>
            <span className="relative h-1.5 rounded-full bg-cartao-2">
              <span
                className={`absolute inset-y-0 left-0 rounded-full ${corDaBarra(medida.atingiu)}`}
                style={{ width: `${larguraDaBarra(medida)}%` }}
              />
            </span>
            <span className="text-right font-mono tabular-nums">
              {formatarNumero(medida.valor)}{" "}
              <span className="text-suave">{resumirFaixa(medida.faixa)}</span>
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}
```

Create `web/src/componentes/SecaoAncoras.tsx`:

```tsx
// As Âncoras citadas pela Célula, sempre visíveis ao lado do conteúdo.
import type { AncoraNumerica } from "../dados/cliente";
import Ancoras from "./Ancoras";
import Chip from "./Chip";

export default function SecaoAncoras({ ancoras }: { ancoras: AncoraNumerica[] }) {
  return (
    <section className="rounded-2xl bg-cartao p-3.5">
      <h2 className="mb-2 flex items-center gap-2 text-[12.5px] font-bold">
        Âncoras citadas <Chip>{ancoras.length}</Chip>
      </h2>
      <Ancoras ancoras={ancoras} />
    </section>
  );
}
```

- [ ] **Step 3: `SecaoPacote`**

Create `web/src/componentes/SecaoPacote.tsx`:

```tsx
// O Pacote de publicação da Célula: imagens, vídeo, legenda, hashtags e a conferência visual.
// Aprovar o Pacote (H5) é uma decisão à parte de aprovar o conteúdo. Ainda não há botão para
// montar o Pacote pela tela: ele sai pelo terminal.
import { useState } from "react";
import {
  aprovarPacote,
  urlDoArquivo,
  type Audiencia,
  type Formato,
  type PacotePublicacao,
} from "../dados/cliente";
import Chip from "./Chip";

export default function SecaoPacote({
  identificador,
  audiencia,
  formato,
  pacote,
  onAtualizado,
}: {
  identificador: string;
  audiencia: Audiencia;
  formato: Formato;
  pacote: PacotePublicacao | null;
  onAtualizado: () => void;
}) {
  const [enviando, definirEnviando] = useState(false);
  const [erro, definirErro] = useState<string | null>(null);

  if (pacote === null) {
    return (
      <section className="rounded-2xl bg-cartao p-3.5">
        <div className="flex flex-wrap items-center gap-3">
          <h2 className="text-[12.5px] font-bold">Pacote de publicação</h2>
          <span className="text-xs text-suave">vídeo · legenda · hashtags · imagens</span>
          <Chip>não montado</Chip>
        </div>
        <p className="mt-2 text-xs text-suave">
          Só Célula aprovada gera Pacote. Ele sai pelo terminal:{" "}
          <code className="rounded bg-cartao-2 px-1.5 py-0.5">
            uv run python -m suno.cli pacote --execucao {identificador}
          </code>
        </p>
      </section>
    );
  }

  const defeitos = (pacote.conferencia?.medicoes ?? []).filter(
    (medicao) => medicao.defeito !== null && medicao.defeito !== undefined,
  );

  function aprovar() {
    definirEnviando(true);
    definirErro(null);
    aprovarPacote(identificador, audiencia, formato)
      .then(onAtualizado)
      .catch((falha: unknown) => {
        definirErro(falha instanceof Error ? falha.message : String(falha));
      })
      .finally(() => definirEnviando(false));
  }

  return (
    <section className="rounded-2xl bg-cartao p-3.5">
      <div className="flex flex-wrap items-center gap-3">
        <h2 className="text-[12.5px] font-bold">Pacote de publicação</h2>
        <Chip tom={pacote.aprovado_por_humano ? "ok" : "alerta"}>
          {pacote.aprovado_por_humano ? "aprovado (H5)" : "aguardando aprovação (H5)"}
        </Chip>
        <div className="flex-1" />
        {!pacote.aprovado_por_humano && (
          <button
            type="button"
            disabled={enviando}
            onClick={aprovar}
            className="rounded-full border border-[#55555b] px-3.5 py-1 text-xs font-semibold disabled:opacity-50"
          >
            Aprovar Pacote
          </button>
        )}
      </div>
      {erro && <p className="mt-2 text-xs text-[#ffb3ad]">{erro}</p>}

      {pacote.imagens && pacote.imagens.length > 0 && (
        <div className="mt-3 grid grid-cols-3 gap-2 sm:grid-cols-6">
          {pacote.imagens.map((imagem) => (
            <img
              key={imagem.indice}
              src={urlDoArquivo(pacote.execucao, imagem.caminho)}
              alt={`Slide ${imagem.indice + 1}`}
              className="rounded-md border border-linha"
            />
          ))}
        </div>
      )}

      {pacote.video && (
        <video
          controls
          className="mt-3 max-h-96 rounded-md border border-linha"
          src={urlDoArquivo(pacote.execucao, pacote.video)}
        />
      )}

      <p className="mt-3 whitespace-pre-wrap text-sm">{pacote.legenda}</p>
      <div className="mt-2 flex flex-wrap gap-1">
        {(pacote.hashtags ?? []).map((hashtag) => (
          <span key={hashtag} className="rounded-full bg-cartao-2 px-2 py-0.5 text-xs text-suave">
            {hashtag}
          </span>
        ))}
      </div>

      {defeitos.length > 0 ? (
        <ul className="mt-3 list-inside list-disc text-xs text-alerta">
          {defeitos.map((medicao, indice) => (
            <li key={indice}>
              {medicao.artefato}: {medicao.defeito} {medicao.detalhe && `— ${medicao.detalhe}`}
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-3 text-xs text-suave">Nenhum defeito de render encontrado.</p>
      )}
      {pacote.conferencia?.juiz_visao && (
        <p className="mt-1 text-xs text-suave">
          Juiz de visão:{" "}
          {pacote.conferencia.juiz_visao.parece_quebrado ? "parece quebrado" : "sem suspeita"}
        </p>
      )}
    </section>
  );
}
```

- [ ] **Step 4: `BarraDecisao`**

Create `web/src/componentes/BarraDecisao.tsx`:

```tsx
// A barra fixa no rodapé da Célula aberta: Compliance, a decisão registrada, o nome do
// revisor e os botões Reprovar… (pede motivo) e Aprovar. Aprovar fica desabilitado, com o
// motivo à vista, quando o Laudo detectou Recomendação; o servidor também recusa (409).
import { useState, type FormEvent } from "react";
import type { DecisaoHumana } from "../dados/cliente";
import { lerRevisor } from "../lib/revisor";
import { formatarDataCurta } from "../texto/rotulos";
import Chip from "./Chip";

export interface PropriedadesDaBarra {
  bloqueada: boolean;
  decisao: DecisaoHumana | null;
  enviando: boolean;
  erro: string | null;
  onDecidir: (estado: "aprovada" | "reprovada", motivo: string | null, revisor: string) => void;
}

function resumoDaDecisao(decisao: DecisaoHumana): string {
  const quem = decisao.revisor ? ` · ${decisao.revisor}` : "";
  const motivo = decisao.motivo ? ` — ${decisao.motivo}` : "";
  const quando = decisao.em ? ` · ${formatarDataCurta(decisao.em)}` : "";
  const acao = decisao.estado === "aprovada" ? "Você aprovou" : "Você reprovou";
  return `${acao}${quem}${quando}${motivo}`;
}

export default function BarraDecisao({
  bloqueada,
  decisao,
  enviando,
  erro,
  onDecidir,
}: PropriedadesDaBarra) {
  const [reprovando, definirReprovando] = useState(false);
  const [motivo, definirMotivo] = useState("");
  const [revisor, definirRevisor] = useState(lerRevisor);

  function confirmarReprovacao(evento: FormEvent) {
    evento.preventDefault();
    if (motivo.trim() === "") return;
    onDecidir("reprovada", motivo.trim(), revisor.trim());
    definirReprovando(false);
    definirMotivo("");
  }

  return (
    <div className="sticky bottom-0 z-20 border-t border-linha bg-lateral px-5 py-2.5">
      {reprovando && (
        <form onSubmit={confirmarReprovacao} className="mb-2.5 flex flex-wrap items-start gap-2">
          <label htmlFor="motivo-da-reprovacao" className="sr-only">
            Motivo da reprovação
          </label>
          <textarea
            id="motivo-da-reprovacao"
            value={motivo}
            onChange={(evento) => definirMotivo(evento.target.value)}
            placeholder="Por que esta Célula não serve? O motivo fica registrado."
            rows={2}
            className="min-w-[280px] flex-1 rounded-lg border border-linha bg-cartao px-3 py-2 text-sm"
          />
          <button
            type="submit"
            disabled={enviando || motivo.trim() === ""}
            className="rounded-full bg-suno px-4 py-2 text-xs font-bold tracking-wide text-white disabled:cursor-not-allowed disabled:opacity-40"
          >
            CONFIRMAR REPROVAÇÃO
          </button>
          <button
            type="button"
            onClick={() => definirReprovando(false)}
            className="rounded-full border border-[#55555b] px-4 py-2 text-xs font-semibold"
          >
            Cancelar
          </button>
        </form>
      )}

      <div className="flex flex-wrap items-center gap-3">
        {bloqueada ? (
          <Chip tom="ruim">Bloqueada: o Laudo detectou Recomendação</Chip>
        ) : (
          <Chip tom="ok">Compliance ok · sem Recomendação</Chip>
        )}
        {decisao && <span className="text-xs text-suave">{resumoDaDecisao(decisao)}</span>}
        {erro && <span className="text-xs text-[#ffb3ad]">{erro}</span>}
        <div className="flex-1" />
        <label className="flex items-center gap-2 text-xs text-suave">
          Revisor
          <input
            value={revisor}
            onChange={(evento) => definirRevisor(evento.target.value)}
            placeholder="seu nome"
            className="w-36 rounded-lg border border-linha bg-cartao px-2.5 py-1 text-sm text-texto"
          />
        </label>
        <button
          type="button"
          disabled={enviando}
          onClick={() => definirReprovando(true)}
          className="rounded-full border border-[#55555b] px-[18px] py-2 text-xs font-semibold disabled:opacity-40"
        >
          Reprovar…
        </button>
        <button
          type="button"
          disabled={enviando || bloqueada}
          title={
            bloqueada
              ? "O Laudo detectou Recomendação: esta Célula não pode ser aprovada."
              : undefined
          }
          onClick={() => onDecidir("aprovada", null, revisor.trim())}
          className="rounded-full bg-suno px-[18px] py-2 text-xs font-bold tracking-wide text-white disabled:cursor-not-allowed disabled:opacity-40"
        >
          APROVAR
        </button>
      </div>
    </div>
  );
}
```

- [ ] **Step 5: A página `CelulaAberta`**

Create `web/src/paginas/CelulaAberta.tsx`:

```tsx
// A Célula aberta ("/saidas/:id/celulas/:audiencia/:formato"): conteúdo à esquerda; Laudo e
// Âncoras à direita, sempre visíveis; Pacote embaixo; barra Aprovar/Reprovar fixa no rodapé
// (spec do front, seção 4.5, opção B).
import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  listarPacotes,
  obterAncorasDaCelula,
  obterExecucao,
  registrarDecisao,
  type Audiencia,
  type DecisaoHumana,
  type Formato,
} from "../dados/cliente";
import { usarRequisicao } from "../ganchos/usarRequisicao";
import { Carregando, MensagemErro } from "../componentes/EstadoRequisicao";
import BarraDecisao from "../componentes/BarraDecisao";
import Chip from "../componentes/Chip";
import ConteudoCelula from "../componentes/ConteudoCelula";
import SecaoAncoras from "../componentes/SecaoAncoras";
import SecaoLaudo from "../componentes/SecaoLaudo";
import SecaoPacote from "../componentes/SecaoPacote";
import Reprovacao from "../componentes/Reprovacao";
import VereditoCartao from "../componentes/VereditoCartao";
import { celulaBloqueada, chaveDaPosicao, vizinhas } from "../lib/matriz";
import { guardarRevisor } from "../lib/revisor";
import { rotuloAudiencia, rotuloFormato } from "../texto/rotulos";

export default function CelulaAberta() {
  const parametros = useParams<{ id: string; audiencia: string; formato: string }>();
  const id = parametros.id ?? "";
  const audiencia = parametros.audiencia as Audiencia;
  const formato = parametros.formato as Formato;

  const [recarga, recarregar] = useState(0);
  const [enviando, definirEnviando] = useState(false);
  const [erroDaDecisao, definirErroDaDecisao] = useState<string | null>(null);
  const [registrada, definirRegistrada] = useState<{
    chave: string;
    decisao: DecisaoHumana;
  } | null>(null);

  const estadoExecucao = usarRequisicao(() => obterExecucao(id), [id]);
  const estadoAncoras = usarRequisicao(
    () => obterAncorasDaCelula(id, audiencia, formato),
    [id, audiencia, formato],
  );
  const estadoPacotes = usarRequisicao(() => listarPacotes(id), [id, recarga]);

  if (estadoExecucao.situacao === "carregando") return <Carregando rotulo="Carregando Célula…" />;
  if (estadoExecucao.situacao === "erro") return <MensagemErro erro={estadoExecucao.erro} />;

  const execucao = estadoExecucao.dados;
  const chave = `${id}:${chaveDaPosicao(audiencia, formato)}`;
  const historico = (execucao.celulas ?? []).find(
    (h) => h.audiencia === audiencia && h.formato === formato,
  );
  const tentativas = historico?.tentativas ?? [];
  const ultima = tentativas.at(-1);
  const bloqueada = celulaBloqueada(ultima?.laudo);
  const decisaoLocal = registrada?.chave === chave ? registrada.decisao : null;
  const decisao =
    decisaoLocal ??
    (execucao.decisoes ?? []).find((d) => d.audiencia === audiencia && d.formato === formato) ??
    null;
  const pedidas = (execucao.celulas ?? []).map((h) => ({
    audiencia: h.audiencia,
    formato: h.formato,
  }));
  const { anterior, proxima } = vizinhas(pedidas, audiencia, formato);
  const pacote =
    estadoPacotes.situacao === "pronto"
      ? (estadoPacotes.dados.find((p) => p.audiencia === audiencia && p.formato === formato) ??
        null)
      : null;

  function decidir(estado: "aprovada" | "reprovada", motivo: string | null, revisor: string) {
    definirEnviando(true);
    definirErroDaDecisao(null);
    guardarRevisor(revisor);
    registrarDecisao(id, audiencia, formato, {
      estado,
      motivo,
      revisor: revisor === "" ? null : revisor,
    })
      .then((nova) => definirRegistrada({ chave, decisao: nova }))
      .catch((falha: unknown) => {
        definirErroDaDecisao(falha instanceof Error ? falha.message : String(falha));
      })
      .finally(() => definirEnviando(false));
  }

  function linkDaVizinha(destino: { audiencia: string; formato: string } | null, rotulo: string) {
    if (destino === null) {
      return <span className="text-[#5d5d63]">{rotulo}</span>;
    }
    return (
      <Link
        to={`/saidas/${encodeURIComponent(id)}/celulas/${destino.audiencia}/${destino.formato}`}
        className="hover:text-texto"
      >
        {rotulo}
      </Link>
    );
  }

  return (
    <div className="flex min-h-screen flex-col">
      <header className="px-5 pb-2.5 pt-3">
        <nav className="mb-1 text-[11.5px] text-suave">
          <Link to="/saidas" className="hover:text-texto">
            Saídas
          </Link>{" "}
          ›{" "}
          <Link to={`/saidas/${encodeURIComponent(id)}`} className="hover:text-texto">
            {execucao.nome}
          </Link>{" "}
          › {rotuloAudiencia(audiencia)} · {rotuloFormato(formato)}
        </nav>
        <div className="flex flex-wrap items-center gap-2.5">
          <h1 className="text-[17px] font-bold">
            {rotuloAudiencia(audiencia)} · {rotuloFormato(formato)}
          </h1>
          {ultima && (
            <Chip tom={ultima.laudo.destino === "aprovado" ? "ok" : "alerta"}>
              {ultima.laudo.destino === "aprovado" ? "Laudo: aprovada" : "Laudo: não aprovada"}
            </Chip>
          )}
          {tentativas.length > 0 && (
            <Chip>
              {tentativas.length} {tentativas.length === 1 ? "rodada" : "rodadas"}
            </Chip>
          )}
          <div className="flex-1" />
          <span className="flex gap-3 text-xs text-suave">
            {linkDaVizinha(anterior, "‹ Célula anterior")}
            {linkDaVizinha(proxima, "próxima ›")}
          </span>
        </div>
      </header>

      {tentativas.length === 0 && (
        <p className="px-5 text-sm text-suave">
          Esta posição da Matriz não tem Célula gerada
          {historico?.falha ? `: ${historico.falha}` : "."}
        </p>
      )}

      {ultima && (
        <div className="grid flex-1 gap-4 px-5 pb-4 lg:grid-cols-[1.25fr_1fr]">
          <div className="min-w-0 space-y-3">
            <section className="rounded-2xl bg-cartao p-3.5">
              <h2 className="mb-2 text-[12.5px] font-bold">Conteúdo</h2>
              <ConteudoCelula conteudo={ultima.celula.conteudo} />
            </section>
            <Reprovacao laudo={ultima.laudo} />
            <SecaoPacote
              identificador={id}
              audiencia={audiencia}
              formato={formato}
              pacote={pacote}
              onAtualizado={() => recarregar((atual) => atual + 1)}
            />
            {tentativas.length > 1 && (
              <details className="rounded-2xl bg-cartao p-3.5">
                <summary className="cursor-pointer text-[12.5px] font-bold">
                  Histórico de tentativas ({tentativas.length})
                </summary>
                <ol className="mt-3 space-y-3">
                  {tentativas.map((tentativa) => (
                    <li key={tentativa.rodada} className="rounded-xl border border-linha p-3">
                      <p className="mb-2 text-xs font-bold uppercase tracking-wide text-suave">
                        Rodada {tentativa.rodada}
                      </p>
                      <div className="space-y-1">
                        {tentativa.laudo.medidas.map((medida) => (
                          <VereditoCartao key={medida.metrica} medida={medida} />
                        ))}
                      </div>
                    </li>
                  ))}
                </ol>
              </details>
            )}
          </div>

          <div className="min-w-0 space-y-3">
            <SecaoLaudo laudo={ultima.laudo} />
            {estadoAncoras.situacao === "carregando" && <Carregando />}
            {estadoAncoras.situacao === "erro" && <MensagemErro erro={estadoAncoras.erro} />}
            {estadoAncoras.situacao === "pronto" && <SecaoAncoras ancoras={estadoAncoras.dados} />}
          </div>
        </div>
      )}

      {ultima && (
        <BarraDecisao
          bloqueada={bloqueada}
          decisao={decisao}
          enviando={enviando}
          erro={erroDaDecisao}
          onDecidir={decidir}
        />
      )}
    </div>
  );
}
```

- [ ] **Step 6: Rota nova**

Em `web/src/App.tsx`, Edit 1. `old_string`:

```tsx
import SaidaAberta from "./paginas/SaidaAberta";
```

`new_string`:

```tsx
import SaidaAberta from "./paginas/SaidaAberta";
import CelulaAberta from "./paginas/CelulaAberta";
```

Edit 2. `old_string`:

```tsx
        <Route path="/saidas/:id" element={<SaidaAberta />} />
```

`new_string`:

```tsx
        <Route path="/saidas/:id" element={<SaidaAberta />} />
        <Route
          path="/saidas/:id/celulas/:audiencia/:formato"
          element={<CelulaAberta />}
        />
```

- [ ] **Step 7: Verificar**

Run (em `web/`): `npx tsc --noEmit -p tsconfig.app.json && npx vitest run`
Expected: sem erros. Se o `tsc` apontar que um campo (por exemplo `execucao.decisoes`, `pacote.conferencia`) é de outro tipo que o esperado, abra o trecho correspondente em `web/src/api/schema.d.ts` e ajuste **só o acesso** (`?? []`, `?? null`), sem alterar o contrato.

- [ ] **Step 8: Checkpoint**

Run (na raiz): `uv run python scripts/vocabulario.py | tail -1` → mesmo número. Não commite.

---

## Task 13: Limpeza das páginas antigas

**Files:**
- Delete: `web/src/paginas/Execucoes.tsx`, `web/src/paginas/Matriz.tsx`, `web/src/paginas/CelulaVista.tsx`, `web/src/paginas/Filas.tsx`, `web/src/paginas/Pacotes.tsx`
- Modify: `web/src/App.tsx`

**Interfaces:**
- Consumes: nada novo.
- Produces: o app só com as rotas `/`, `/fontes`, `/curadoria`, `/saidas`, `/saidas/:id`, `/saidas/:id/celulas/:audiencia/:formato`.

- [ ] **Step 1: Remover as páginas e as rotas antigas**

Run (na raiz):

```bash
rm web/src/paginas/Execucoes.tsx web/src/paginas/Matriz.tsx web/src/paginas/CelulaVista.tsx web/src/paginas/Filas.tsx web/src/paginas/Pacotes.tsx
```

Em `web/src/App.tsx`, Edit 1. `old_string`:

```tsx
import Execucoes from "./paginas/Execucoes";
import Matriz from "./paginas/Matriz";
import CelulaVista from "./paginas/CelulaVista";
import Filas from "./paginas/Filas";
import Pacotes from "./paginas/Pacotes";
```

`new_string`:

```tsx
```

(vazio: apague essas cinco linhas.)

Edit 2. `old_string`:

```tsx
        {/* Rotas antigas, removidas na Tarefa 13. */}
        <Route path="/execucoes" element={<Execucoes />} />
        <Route path="/execucoes/:id" element={<Matriz />} />
        <Route path="/execucoes/:id/celulas/:audiencia/:formato" element={<CelulaVista />} />
        <Route path="/execucoes/:id/filas" element={<Filas />} />
        <Route path="/execucoes/:id/pacotes" element={<Pacotes />} />
```

`new_string`:

```tsx
```

(vazio: apague essas seis linhas.)

- [ ] **Step 2: Remover o que ficou sem uso**

Run (na raiz): `grep -rn "corDestino\|obterFilas\|resolverH4\|listarAtas\|obterAta\b" web/src --include=*.ts --include=*.tsx`
Expected: aparecem só as **definições** (em `rotulos.ts` e `dados/cliente.ts`). `corDestino` agora não tem nenhum uso: apague a função inteira de `web/src/texto/rotulos.ts`. Deixe `obterFilas`, `resolverH4`, `listarAtas` e `obterAta` em `dados/cliente.ts`: ainda são rotas da API, e a fila H3/H4 volta como estado da Célula e a Curadoria vai usar as Atas.

- [ ] **Step 3: Verificar**

Run (em `web/`): `npm run build && npx vitest run`
Expected: build conclui (inclui `tsc --noEmit`); testes verdes.

- [ ] **Step 4: Checkpoint**

Run (na raiz): `uv run pytest -q -x` → tudo verde (`882 passed`). `uv run python scripts/vocabulario.py | tail -1` → mesmo número da Tarefa 1. Não commite.

---

## Task 14: Documentação e verificação no app rodando

**Files:**
- Create: `docs/adr/0017-api-dispara-a-geracao-em-segundo-plano.md`
- Modify: `CONTEXT.md` (acrescentar uma seção no fim), `web/README.md`

**Interfaces:**
- Consumes: tudo das tarefas anteriores.
- Produces: ADR 0017, termos novos no CONTEXT.md e o README do front atualizado.

- [ ] **Step 1: ADR 0017**

Create `docs/adr/0017-api-dispara-a-geracao-em-segundo-plano.md`:

```markdown
# A API dispara a geração em segundo plano, um job por vez

Até aqui a API só lia do disco. O docstring de `src/suno/api/app.py` diz que `executar` e
`montar_pacote` são comando de terminal e nunca uma rota. O painel novo (spec em
`docs/superpowers/specs/2026-10-09-front-suno-design.md`) muda isso: a pessoa marca quais
Células quer e a interface precisa iniciar a geração, acompanhar e registrar o resultado.

Decidimos que a API **inicia o pipeline em segundo plano** por `POST /api/execucoes`, grava o
andamento em `andamento.json` ao lado de `execucao.json` e roda **um job por vez**. Os demais
ficam em fila. No boot do servidor, um job que ficou "gerando" vira "interrompida".

O disco continua sendo a única fonte de verdade: a interface lê o mesmo `execucao.json` que o
pytest lê e o relatório cita ([ADR 0006](0006-atas-do-copom-como-documento-fonte-principal.md)).

## Por que um job por vez

O tier gratuito dos provedores tem cota ([ADR 0007](0007-roteador-de-provedores-distingue-tipo-de-429.md)).
Dois jobs juntos multiplicam os 429 sem ganho: as Células de uma Saída já geram em paralelo
dentro do job.

## Alternativas recusadas

- **Fila externa (Celery, Redis).** Infraestrutura demais para um case de 2 pessoas em 2 semanas.
- **Subprocesso do CLI por geração.** Duplicaria o estado e dificultaria o andamento por Célula.
- **Manter só o terminal.** Não atende a quem precisa escolher e gerar pela interface.

## Consequências

A demo continua sem rede: o provedor falso responde por rótulo (`celula:<aud>:<fmt>:<rodada>`) e
só existe para as Atas que têm `data/respostas_prontas/<id>.json`, hoje só o Copom 280. O modo
Real gasta cota gratuita. A suíte de testes cobre a fila e o andamento sem rede.

Este ADR registra a decisão. A implementação do job entra na Fase 2 do plano do front; as
Fases 0 e 1 só acrescentam rotas de leitura e de decisão humana.
```

- [ ] **Step 2: Termos novos no `CONTEXT.md`**

Acrescente **no fim** de `CONTEXT.md` (use Edit sobre a última linha do arquivo, `_Avoid_: post, bundle, export, entrega`, repetindo-a no `old_string` e colocando-a de volta no `new_string` seguida do texto novo):

`old_string`:

```markdown
_Avoid_: post, bundle, export, entrega
```

`new_string`:

```markdown
_Avoid_: post, bundle, export, entrega

### A interface

**Saída**:
Uma execução vista pela interface: tem um nome dado pelo usuário, registra quais Células
foram pedidas e o que foi decidido sobre cada uma. No código é a `Execucao`; "Saída" é só o
rótulo de tela.

**Decisão humana**:
Aprovar ou reprovar uma Célula, registrada com motivo (obrigatório ao reprovar) e o nome do
revisor. Não vale para a Célula cujo Laudo detectou Recomendação: essa não pode ser aprovada.
```

(Não adicione linha `_Avoid_:` aos termos novos: `scripts/vocabulario.py` leria essas palavras e passaria a barrá-las nos identificadores do código.)

- [ ] **Step 3: README do front**

Rewrite `web/README.md` (o bloco abaixo usa quatro crases porque o conteúdo tem blocos de código dentro):

````markdown
# Suno Content — interface

React + Vite + Tailwind sobre FastAPI (ADR 0005). Painel escuro, em preto e vermelho da Suno,
com três guias: **Fontes**, **Curadoria** e **Saídas**. Fontes e Curadoria ainda são páginas
"em breve"; a guia Saídas já lista as execuções, abre a Matriz 3×3, mostra cada Célula com o
Laudo e as Âncoras ao lado, e deixa aprovar, reprovar, renomear e exportar.

O desenho completo está em `docs/superpowers/specs/2026-10-09-front-suno-design.md`, com os
mockups em `docs/superpowers/specs/mockups-2026-10-09/`.

## Rodar em dev

Em dois terminais, na raiz do repositório:

```bash
uv run python -m suno.cli servir
```

```bash
cd web
npm install
npm run dev
```

O `vite.config.ts` faz proxy de `/api` para `http://127.0.0.1:8000`, então a SPA em
`http://localhost:5173` fala com a API sem configurar CORS à mão.

Aprovar e reprovar **gravam** no `execucao.json` da execução. Para testar sem sujar a demo
versionada, copie a pasta e aponte a API para a cópia:

```bash
cp -r data/execucoes/demo-copom-280 /tmp/suno-execucoes/
SUNO_EXECUCOES=/tmp/suno-execucoes uv run python -m suno.cli servir
```

## Construir para o FastAPI servir

```bash
cd web
npm install
npm run build
```

Isso roda `tsc --noEmit` e depois `vite build`, gerando `web/dist/`. O `criar_app` do
`src/suno/api/app.py` serve essa pasta como estático em `/`, com fallback para `index.html` em
qualquer rota que não seja da API (atualizar a página em `/saidas/abc` funciona), quando
`web/dist/index.html` existe.

## Testes

```bash
cd web
npm test
```

Vitest, só para a lógica pura em `src/lib/` (estado e cor de cada posição da Matriz, contagens,
filtro). Os componentes são conferidos por `tsc` e olhando o app rodando.

## Cliente da API

`npm run dev`/`npm run build` não regeram o cliente: `web/openapi.json` e
`web/src/api/schema.d.ts` são gerados a partir de `src/suno/api/app.py`. Para regerar sem rede:

```bash
uv run python -c "import json, pathlib; from suno.api.openapi import gerar_schema; pathlib.Path('web/openapi.json').write_text(json.dumps(gerar_schema(), ensure_ascii=False, indent=2) + '\n', encoding='utf-8')"
cd web && npx openapi-typescript openapi.json -o src/api/schema.d.ts
```

`tests/test_contrato_openapi.py` falha quando `web/openapi.json` diverge da API. Todo acesso à
API na SPA passa por `web/src/dados/cliente.ts`; nenhum outro arquivo chama `fetch`.
````

- [ ] **Step 4: Verificação no app rodando**

Copie a demo para uma pasta temporária, para não sujar o `execucao.json` versionado, e suba o servidor com o front construído. Na raiz:

```bash
mkdir -p "$TEMP/suno-execucoes" && cp -r data/execucoes/demo-copom-280 "$TEMP/suno-execucoes/"
(cd web && npm run build)
SUNO_EXECUCOES="$TEMP/suno-execucoes" uv run python -m suno.cli servir --porta 8765
```

Rode o servidor em segundo plano (`run_in_background`). Depois:

```bash
curl -s http://127.0.0.1:8765/api/execucoes | python -c "import json,sys; d=json.load(sys.stdin); print(d[0]['nome'], d[0]['status'], len(d[0]['posicoes']))"
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8765/saidas/demo-copom-280
curl -s -o /dev/null -w "%{http_code}\n" "http://127.0.0.1:8765/api/execucoes/demo-copom-280/exportar?formato=zip"
```

Expected: a primeira imprime `demo-copom-280 aguardando_revisao 9`; as outras duas imprimem `200`.

Capture as telas com o Edge sem janela e leia as imagens:

```bash
mkdir -p "$TEMP/suno-capturas"
EDGE="/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"
for rota in saidas saidas/demo-copom-280 saidas/demo-copom-280/celulas/iniciante/carrossel fontes; do
  nome=$(echo "$rota" | tr '/' '_')
  "$EDGE" --headless=new --disable-gpu --window-size=1440,1000 --virtual-time-budget=8000 --screenshot="$(cygpath -w "$TEMP/suno-capturas/$nome.png")" "http://127.0.0.1:8765/$rota"
done
ls "$TEMP/suno-capturas"
```

Abra cada PNG com a ferramenta Read e confira, contra os mockups:
- `saidas.png`: menu lateral escuro com as três guias, o cartão "demo-copom-280" com a mini-Matriz 3×3 (8 quadrados cinza e 1 âmbar, ou conforme a demo), chip "Aguardando revisão", legenda embaixo.
- `saidas_demo-copom-280.png`: nome no topo, botão Exportar, a faixa de contagens e a Matriz 3×3 com chips "Laudo ok" e "Pendente", e a posição Intermediário × Roteiro em âmbar ("Revisão humana").
- `saidas_demo-copom-280_celulas_iniciante_carrossel.png`: slides à esquerda, Laudo com barras e Âncoras à direita, barra "APROVAR / Reprovar…" no rodapé.
- `fontes.png`: a página "Esta guia chega em breve".

Se o Edge não estiver nesse caminho, localize-o com `ls "/c/Program Files/Microsoft/Edge/Application/"` (ou `where msedge`). Se as classes de cor não aparecerem (página branca ou sem cor), o `@theme` do `global.css` não foi aplicado: confirme `@import "tailwindcss";` na primeira linha e rode o `npm run build` de novo. Se o fundo dos slides ficar sem gradiente, troque `bg-linear-to-br` por `bg-gradient-to-br` em `ConteudoCelula.tsx` (o nome da utilidade mudou entre versões do Tailwind) e reconstrua.

Pare o servidor ao final (encerre a tarefa em segundo plano) e apague `$TEMP/suno-execucoes` e `$TEMP/suno-capturas`.

- [ ] **Step 5: Verificação final**

Run (na raiz):

```bash
uv run pytest -q
uv run python scripts/vocabulario.py | tail -1
(cd web && npm run build && npm test)
git status --short
```

Expected:
- `pytest`: tudo verde (`882 passed`, 0 failed).
- vocabulário: o mesmo número de achados anotado na Tarefa 1 (os 16 do trabalho da equipe) e nenhuma linha dos arquivos novos.
- `npm run build` e `npm test` verdes.
- `git status --short` mostra os arquivos novos e modificados deste plano **mais** o que já estava pendente da equipe; confira que `data/execucoes/demo-copom-280/execucao.json` **não** aparece como modificado. Não commite.

---

## Self-review

**Cobertura da spec (fases 0 e 1).**
- Seção 4.1 e 4.2 (Fontes e Curadoria): ficam como páginas "em breve" (Tarefa 10). Entram nas Fases 3 e 2, fora deste plano.
- 4.3 Lista de Saídas: Tarefas 10 (cartões, mini-Matriz, filtros, legenda, menu `···`, número no menu). O estado "Gerando" e "Interrompida" dependem do job e entram na Fase 2.
- 4.4 Saída aberta (opção A): Tarefa 11.
- 4.5 Célula aberta (opção B): Tarefa 12, com Laudo, Âncoras, Pacote, barra de decisão, vizinhas e histórico de tentativas.
- 4.6 O que acontece com o front atual: Tarefas 10 a 13 (Execucoes, Matriz, CelulaVista, Filas, Pacotes trocadas; Layout reescrito). H3, H4 e H5 viram estados da Célula: H3 pelo chip "Revisão: comitê", H4 pelo chip "Revisão humana" resolvida pela decisão (Tarefa 2), H5 na `SecaoPacote`.
- 5 Tokens: Tarefa 7.
- 6.2 Domínio novo: `nome`, `decisoes`, `DecisaoHumana` (Tarefa 1). `pedido`, `Fonte`, `ItemDeFonte` e `Andamento` ficam para as Fases 2 e 3.
- 6.3 Rotas: `resumo`, `PATCH`, `decisao` e `exportar` (Tarefa 5). As demais rotas (fontes, curadoria, `POST /api/execucoes`, andamento) são das Fases 2 e 3.
- 6.6 Regras de decisão: todas na Tarefa 2 (sem conteúdo, Compliance bloqueia com 409, aprovar `aprovado` ou `reprovado_revisao_humana`, reprovar exige motivo, resolve H4, rota antiga mantida, Pacote separado).
- 6.7 Exportar: Tarefa 3.
- Fase 0: ADR 0017 e termos (Tarefa 14), tokens e casca (Tarefas 7 e 10), cliente regerado (Tarefa 6). "Combinar com a equipe" é ação humana, registrada em Global Constraints.
- Testes (spec seção 8): `avaliar_matriz` por posições, job e fontes são das Fases 2 e 3. Cobertos aqui: `Execucao` com os campos novos e execução antiga, decisão (inclui o 409), exportar json, md e zip, contrato do OpenAPI e a lógica pura do front.

**Fora do plano de propósito:** API aberta `/v1`; `pedido` e o job em segundo plano; fontes, CVM e upload; Visão unida; botão Montar Pacote; o filtro por fonte e a escolha de ordem da lista de Saídas (a spec os desenha, mas só fazem sentido com mais de uma fonte, na Fase 3; por ora a lista ordena da mais recente para a mais antiga).

## Registro da execução (2026-10-09)

As 14 tarefas foram executadas. Resultado final: `882 passed` no pytest, `27 passed` no Vitest,
`npm run build` verde e `scripts/vocabulario.py` nos mesmos 16 achados da linha de base, nenhum
em arquivo novo. As telas foram conferidas com o app rodando (Edge sem janela) sobre uma cópia
da demo. Onde o código final difere dos blocos acima, **o código do repositório é a referência**:

- **Tarefa 3:** o teste e a implementação foram escritos juntos, sem rodar o "ver falhar" intermediário.
- **Tarefa 5:** o fallback da SPA tinha um bug no Windows. O Starlette entrega o caminho com barra
  invertida (`api\nao-existe`), e `startswith("api/")` não pegava, então rota de API inexistente
  devolvia `index.html` com 200. O teste antigo `test_arquivo_com_travessia_de_pasta...` quebrou
  por isso e achou o bug. Corrigido no bloco da Tarefa 5 e no código.
- **Tarefa 12:** `DecisaoHumana.em` é opcional no schema gerado (tem valor padrão no servidor);
  `BarraDecisao` só mostra a data quando ela existe.
- **Tarefa 14, achado da verificação visual:** o Laudo da última rodada pode dizer "correção possível"
  quando o teto de rodadas já mandou a Célula para a revisão humana. `SecaoLaudo` e `Reprovacao`
  passaram a receber `destinoFinal` (o `destino_final` do histórico), e o chip do cabeçalho da
  Célula usa o mesmo valor, de modo que a Célula aberta concorda com a Matriz.
- **Teste manual de `curl`:** o `curl.exe` do Windows recusou um corpo com acento com 400. A rota está
  correta (o cliente Python e o `curl` com corpo ASCII respondem 200); não é defeito da API.
- **Arquivos de terceiros:** durante a execução apareceram modificados arquivos que este plano não
  toca (`cli.py`, `gerador/ciclo.py`, `gerador/moldes.py`, `pacote/__init__.py`, `tests/test_pacote.py`,
  `avaliador/juiz_transversal.py`). Há mais alguém editando a mesma pasta.

**Conferência de nomes e tipos entre tarefas.**
- `PosicaoResumo` (Python, Tarefa 4) tem `audiencia, formato, destino, decisao, bloqueada, sem_conteudo, revisao_comite`; `PosicaoParaTela` (TypeScript, Tarefa 8) tem exatamente os mesmos campos; `MiniMatriz` e `CelulaDaMatriz` passam o `PosicaoResumo` gerado, que é atribuível a `PosicaoParaTela`.
- `ExecucaoResumo` (Tarefa 5) tem `nome, modo, aprovadas_humano, status, posicoes`; `Saidas`, `CartaoSaida` e `SaidaAberta` usam `nome`, `modo`, `status`, `posicoes`. `filtrarSaidas` exige `nome, identificador, ata, status`, todos presentes em `ExecucaoResumo`.
- `decidir(...)` (Tarefa 2) é chamada igual em `app.py` (Tarefa 5) e nos testes de `exportacao` e `resumo`.
- `exportar(execucao, pasta, formato)` (Tarefa 3) é chamada igual em `app.py`.
- `registrarDecisao(id, audiencia, formato, { estado, motivo, revisor })` (Tarefa 9) é chamada igual em `CelulaAberta`; `BarraDecisao.onDecidir` passa `(estado, motivo, revisor)` e `CelulaAberta.decidir` recebe os mesmos três.
- `TomChip` é definido em `lib/matriz.ts` e importado por `Chip.tsx`.
- Contagens de teste citadas (`843`, `854`, `858`, `865`, `881`, `882`) somam 6 + 11 + 4 + 7 + 16 + 1 sobre 837; se a contagem real divergir por um arquivo de teste a mais ou a menos, o que importa é `0 failed`.

**Varredura de placeholders.** Nenhum "TBD", "TODO" nem "similar à Tarefa N". Os dois pontos condicionais (Tarefa 7 Step 1, o conflito de peer do Vitest; Tarefa 14 Step 4, o caminho do Edge e o nome da utilidade de gradiente) trazem o comando de diagnóstico e a ação para cada ramo.
