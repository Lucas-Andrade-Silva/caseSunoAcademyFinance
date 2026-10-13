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
  DuracaoDoVideo,
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
  const dia = data.toLocaleDateString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
  });
  const hora = data.toLocaleTimeString("pt-BR", {
    hour: "2-digit",
    minute: "2-digit",
  });
  return `${dia} · ${hora}`;
}

/** "05/08/2026", para uma data sem hora (a data de referência de uma Ata). */
export function formatarDataDoDia(dataIso: string): string {
  return new Date(`${dataIso}T12:00:00`).toLocaleDateString("pt-BR");
}

export function pluralizar(
  quantidade: number,
  singular: string,
  plural: string,
): string {
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

/** O que cada métrica do Laudo mede, em uma ou duas frases, para quem clica na linha. */
export function descricaoDaMetrica(metrica: Metrica): string {
  switch (metrica) {
    case "integridade":
      return "Confere se o sistema leu a Ata direito: a data da reunião e a decisão principal precisam ter sido encontradas no texto. Sem isso, nada que vem depois é confiável.";
    case "flesch_br":
      return "Facilidade de leitura em português, de 0 a 100: quanto maior, mais fácil. Depende do tamanho das frases e das palavras. Cada Audiência tem uma faixa: o Iniciante pede texto fácil, o Avançado aceita texto difícil.";
    case "densidade":
      return "Proporção de termos técnicos (o Léxico) no texto. Para o Iniciante, todo termo precisa vir explicado na primeira vez que aparece; para o Intermediário, os fora do vocabulário básico. O Avançado não exige explicação.";
    case "aderencia":
      return "Todo número do texto precisa vir de uma Âncora, um valor tirado literalmente da Ata. Número que não está na Ata, ou com valor trocado, reprova.";
    case "recomendacao":
      return "Conta trechos que mandam ou sugerem comprar, vender ou manter um investimento. O conteúdo informa e educa, nunca recomenda: o limite é zero.";
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
      return positivo
        ? "Densidade adequada ao Léxico"
        : "Densidade abaixo do Limiar";
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

/** O que identifica a origem de uma Saída: o id da Ata, ou "N Atas" na Visão unida. */
export function rotuloDasAtas(
  modo: string | null | undefined,
  ata: string,
  atas: readonly string[] | undefined,
): string {
  return modo === "unida" ? `${atas?.length ?? 0} Atas` : ata;
}

/** `falso` é a demo sem rede; qualquer outro é provedor de verdade. */
export function rotuloProvedor(provedor: string): string {
  return provedor === "falso" ? "Demo" : `Real · ${provedor}`;
}

/** Onde a execução inteira está, em uma frase para a barra de progresso. */
export function rotuloFase(fase: string | null | undefined): string {
  switch (fase) {
    case "extraindo_ancoras":
      return "Lendo a Ata e extraindo as Âncoras…";
    case "gerando_celulas":
      return "Gerando as Células…";
    case "avaliando_matriz":
      return "Avaliando a Matriz…";
    case "gravando":
      return "Gravando a Saída…";
    default:
      return "Esperando a vez na fila…";
  }
}

/** A Célula ao vivo: o título e o detalhe pequeno embaixo. `parou` = a Saída foi interrompida. */
export function rotuloEtapa(
  etapa: string,
  rodada: number,
  parou: boolean,
): { titulo: string; detalhe: string } {
  const rodadas = pluralizar(rodada + 1, "rodada", "rodadas");
  switch (etapa) {
    case "aprovada":
      return { titulo: "Aprovada", detalhe: rodadas };
    case "revisao_humana":
      return { titulo: "Revisão humana", detalhe: rodadas };
    case "gerando":
      return parou
        ? { titulo: "Parou", detalhe: `na rodada ${rodada + 1}` }
        : { titulo: "Gerando…", detalhe: `rodada ${rodada + 1}` };
    case "corrigindo":
      return parou
        ? { titulo: "Parou", detalhe: `na rodada ${rodada + 1}` }
        : { titulo: "Corrigindo…", detalhe: `rodada ${rodada + 1}` };
    default:
      return parou
        ? { titulo: "Não começou", detalhe: "" }
        : { titulo: "Na fila", detalhe: "" };
  }
}

/** As durações que a pessoa escolhe para o vídeo, na ordem, com o rótulo que a tela mostra. */
export const DURACOES: readonly { valor: DuracaoDoVideo; rotulo: string }[] = [
  { valor: "40", rotulo: "40 s" },
  { valor: "60", rotulo: "1 min" },
  { valor: "90", rotulo: "1 min 30" },
  { valor: "120", rotulo: "2 min" },
  { valor: "180", rotulo: "3 min" },
];

/** "1 min 30" para 90 s; cai em "N s" se a duração não é uma das cinco. */
export function rotuloDaDuracao(segundos: number | null | undefined): string {
  if (segundos === null || segundos === undefined) return "—";
  return (
    DURACOES.find((d) => Number(d.valor) === segundos)?.rotulo ??
    `${segundos} s`
  );
}

/** O nome do catálogo de direção de cena, sem sublinhado: "deslizar_cima" vira "deslizar cima". */
export function rotuloDaDirecao(nome: string): string {
  return nome.replace(/_/g, " ");
}
