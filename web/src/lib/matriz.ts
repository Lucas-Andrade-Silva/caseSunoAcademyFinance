// Lógica pura da Matriz e das Saídas: nada aqui toca React nem a rede, por isso é a parte do
// front que o Vitest cobre. A regra de verdade (quem pode aprovar o quê) mora no servidor, em
// src/suno/revisao.py; aqui só se decide como a tela mostra o que o servidor já resumiu.

export type EstadoPosicao =
  | "aprovada"
  | "aguardando"
  | "revisao"
  | "reprovada"
  | "na_fila"
  | "gerando"
  | "corrigindo";
export type TomChip = "neutro" | "forte" | "ok" | "alerta" | "ruim";
export type FiltroDeStatus =
  | "todas"
  | "aguardando_revisao"
  | "concluida"
  | "em_geracao"
  | "com_problema";

/** Os status que o filtro "Em geração" e o "Interrompidas" juntam. */
const GRUPOS_DE_STATUS: Record<string, readonly string[]> = {
  em_geracao: ["na_fila", "gerando"],
  com_problema: ["interrompida", "falhou"],
};

/** O mínimo de uma posição da Matriz. É o `PosicaoResumo` do servidor, sem depender do schema. */
export interface PosicaoParaTela {
  audiencia: string;
  formato: string;
  destino: string | null;
  decisao: string | null;
  bloqueada: boolean;
  sem_conteudo: boolean;
  revisao_comite: boolean;
  /** Só para Saída em geração: onde a Célula está. */
  etapa?: string | null;
}

interface ChipsDaPosicao {
  laudo: { texto: string; tom: TomChip };
  decisao: { texto: string; tom: TomChip };
}

interface ContagemDaSaida {
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

const SAIDA_PAROU = ["interrompida", "falhou"];

/** A Célula de uma Saída que ainda não tem Laudo: o estado vem da etapa do andamento. */
function estadoDaCelulaViva(etapa: string, statusDaSaida: string | undefined): EstadoPosicao {
  const parou = statusDaSaida !== undefined && SAIDA_PAROU.includes(statusDaSaida);
  switch (etapa) {
    case "aguardando":
      return parou ? "reprovada" : "na_fila";
    case "gerando":
      return parou ? "reprovada" : "gerando";
    case "corrigindo":
      return parou ? "reprovada" : "corrigindo";
    case "revisao_humana":
      return "revisao";
    default:
      return "aguardando";
  }
}

/**
 * `statusDaSaida` só importa para Célula ainda sem Laudo: numa Saída interrompida ou que falhou,
 * a que não terminou está parada, não gerando.
 */
export function estadoDaPosicao(posicao: PosicaoParaTela, statusDaSaida?: string): EstadoPosicao {
  if (posicao.destino === null && posicao.etapa) {
    return estadoDaCelulaViva(posicao.etapa, statusDaSaida);
  }
  if (posicao.decisao === "aprovada") return "aprovada";
  if (posicao.decisao === "reprovada" || posicao.bloqueada || posicao.sem_conteudo) {
    return "reprovada";
  }
  if (posicao.destino === "reprovado_revisao_humana" || posicao.revisao_comite) return "revisao";
  return "aguardando";
}

const CHIP_DA_ETAPA: Record<string, { texto: string; tom: TomChip }> = {
  aguardando: { texto: "Na fila", tom: "neutro" },
  gerando: { texto: "Gerando…", tom: "alerta" },
  corrigindo: { texto: "Corrigindo…", tom: "alerta" },
  aprovada: { texto: "Laudo ok", tom: "ok" },
  revisao_humana: { texto: "Revisão humana", tom: "alerta" },
};

export function chipsDaPosicao(posicao: PosicaoParaTela): ChipsDaPosicao {
  const daEtapa = posicao.destino === null && posicao.etapa ? CHIP_DA_ETAPA[posicao.etapa] : null;
  if (daEtapa) {
    return { laudo: daEtapa, decisao: { texto: "Pendente", tom: "neutro" } };
  }
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

interface Progresso {
  terminadas: number;
  total: number;
  percentual: number;
}

const ETAPAS_TERMINADAS = ["aprovada", "revisao_humana"];

/** A barra de progresso da geração: Células que já terminaram (aprovadas ou em revisão humana). */
export function progressoDoAndamento(celulas: readonly { etapa: string }[]): Progresso {
  const terminadas = celulas.filter((celula) => ETAPAS_TERMINADAS.includes(celula.etapa)).length;
  const total = celulas.length;
  return {
    terminadas,
    total,
    percentual: total === 0 ? 0 : Math.round((terminadas / total) * 100),
  };
}

export function normalizarBusca(texto: string): string {
  return texto
    .normalize("NFD")
    .replace(/\p{Diacritic}/gu, "")
    .toLowerCase()
    .trim();
}

interface SaidaParaFiltro {
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
    if (filtro.status !== "todas") {
      const grupo = GRUPOS_DE_STATUS[filtro.status];
      const combina = grupo ? grupo.includes(saida.status) : saida.status === filtro.status;
      if (!combina) return false;
    }
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
