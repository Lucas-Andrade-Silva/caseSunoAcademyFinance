// Traduz os valores do domínio (dominio.py, via o schema gerado) para o rótulo em
// palavras que a tela mostra ao lado do número — ver docs/ARQUITETURA.md, seção "A interface".
import type { Audiencia, Destino, Formato, Medida, Metrica, MotivoReprovacao } from "../dados/cliente";

const NUMERO = new Intl.NumberFormat("pt-BR", {
  maximumFractionDigits: 2,
  minimumFractionDigits: 0,
});

export function formatarNumero(valor: number | null | undefined): string {
  return valor === null || valor === undefined ? "—" : NUMERO.format(valor);
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
      return "border-emerald-300 bg-emerald-50 text-emerald-900 dark:border-emerald-800 dark:bg-emerald-950 dark:text-emerald-100";
    case "reprovado_corrigivel":
      return "border-amber-300 bg-amber-50 text-amber-900 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-100";
    case "reprovado_revisao_humana":
      return "border-rose-300 bg-rose-50 text-rose-900 dark:border-rose-800 dark:bg-rose-950 dark:text-rose-100";
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
