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
