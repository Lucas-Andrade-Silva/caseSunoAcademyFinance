// O prompt do roteiro: o texto em português que a pessoa cola numa ferramenta de vídeo com avatar
// (HeyGen, Veo e parecidas). Função pura (Vitest cobre). Tudo o que é conteúdo vem do roteiro e
// entra literal: a fala, a rubrica da tela, os números. Aqui só se escreve a instrução em volta.
// A fala nunca é reescrita, porque o Flesch-BR do Laudo vale sobre ela.
import type { BlocoFala } from "../../dados/cliente";
import {
  animacaoPorExtenso,
  efeitoPorExtenso,
  entradaPorExtenso,
  layoutDaCena,
  nomeDaCena,
  nomeDoIcone,
} from "./direcao";
import type { ClimaDoNarrador, RitmoDoNarrador } from "./jeitos";
import {
  duracaoDoRoteiro,
  duracaoPorExtenso,
  formatarIntervalo,
  formatarSegundos,
} from "./tempo";

export interface EntradaDoPrompt {
  blocos: readonly BlocoFala[];
  clima: ClimaDoNarrador | null;
  ritmo: RitmoDoNarrador | null;
}

interface JeitoEscrito {
  narrador: string;
  edicao: string;
}

const DO_CLIMA: Record<ClimaDoNarrador, JeitoEscrito> = {
  descontraido: {
    narrador:
      "descontraído. Fale como numa conversa leve, com sorriso discreto, olhar direto para a câmera e voz calorosa.",
    edicao: "Visual limpo e leve, sem solenidade.",
  },
  serio: {
    narrador:
      "sério. Postura firme, expressão neutra e confiante, voz grave e calma.",
    edicao: "Visual sóbrio, sem brincadeiras visuais.",
  },
  engracado: {
    narrador:
      "engraçado. Bom humor leve, com expressões divertidas e naturais, sem piada com o dado, com a decisão ou com o dinheiro das pessoas.",
    edicao: "Visual leve. O humor fica na interpretação do narrador, nunca nos números nem no texto da tela.",
  },
};

const DO_RITMO: Record<RitmoDoNarrador, JeitoEscrito> = {
  devagar: {
    narrador: "devagar. Cerca de 130 palavras por minuto, com pausas curtas entre as ideias.",
    edicao: "Cenas com tempo para respirar, transições suaves e o texto da tela entrando sem pressa.",
  },
  rapido: {
    narrador: "rápido. Cerca de 170 palavras por minuto, sem pausas longas.",
    edicao:
      "Cortes mais curtos e dinâmicos, transições rápidas e o texto da tela entrando logo no começo da cena.",
  },
};

// O que vale quando a pessoa não escolheu nada: o ritmo é o do próprio roteiro (2,5 palavras por segundo).
const CLIMA_NEUTRO = "natural e claro, com voz firme e sem exageros.";
const RITMO_NEUTRO = "natural, cerca de 150 palavras por minuto.";
const EDICAO_NEUTRA = "Edição sóbria, de mercado financeiro: pouco efeito.";

const REGRAS: readonly string[] = [
  "Leia a fala de cada cena exatamente como está escrita, sem trocar, resumir nem acrescentar palavras. Os tempos são a referência: se a fala não couber, ajuste a pausa ou a velocidade da voz, nunca o texto.",
  "Escreva e fale os números exatamente como estão, sem arredondar, converter nem acrescentar dados.",
  "Não prometa retorno, não faça projeções e não recomende comprar, vender ou manter nenhum investimento.",
  "Legendas embutidas no vídeo, sincronizadas com a fala.",
  "Além das legendas, o único texto escrito na tela é o indicado em cada cena.",
  "Sem logotipos, marcas ou imagens de terceiros.",
];

function secao(titulo: string, linhas: readonly string[]): string {
  return [titulo.toUpperCase(), ...linhas].join("\n");
}

/** As partes de uma rubrica de lista ou comparação, que o Roteiro separa com " | ". */
function partesDaTela(tela: string): string[] {
  return tela
    .split("|")
    .map((parte) => parte.trim())
    .filter((parte) => parte !== "");
}

function citar(texto: string): string {
  return `“${texto}”`;
}

function textoDaTela(tela: string, cena: string): string {
  const partes = partesDaTela(tela);
  if (partes.length <= 1) return citar(tela);
  const como = cena === "lista" ? "em sequência" : cena === "comparacao" ? "dois lados" : "em partes";
  return `${como}: ${partes.map(citar).join("; ")}`;
}

function linhasDaCena(bloco: BlocoFala, ordem: number): string[] {
  const linhas = [`Cena ${ordem} · ${formatarIntervalo(bloco.inicio_s, bloco.fim_s)} · ${nomeDaCena(bloco.cena)}`];

  const layout = layoutDaCena(bloco.cena);
  if (layout) linhas.push(`Layout: ${layout}.`);

  linhas.push(`Fala (leia exatamente assim): ${citar(bloco.fala)}`);

  const tela = (bloco.tela ?? "").trim();
  if (tela) {
    const alvo = partesDaTela(tela).length > 1 ? "Na tela, " : "Na tela: ";
    linhas.push(`${alvo}${textoDaTela(tela, bloco.cena)}`);
    const animacao = animacaoPorExtenso(bloco.texto_anima);
    if (animacao) {
      const atraso = bloco.texto_entra_em_s > 0
        ? `, ${formatarSegundos(bloco.texto_entra_em_s)} s depois do início da cena`
        : "";
      linhas.push(`Animação do texto: ${animacao}${atraso}.`);
    }
  }

  const icone = nomeDoIcone(bloco.icone);
  if (icone) linhas.push(`Ícone: ${icone}.`);

  const entrada = entradaPorExtenso(bloco.entrada);
  if (entrada) linhas.push(`Entrada da cena: ${entrada}.`);

  const efeito = efeitoPorExtenso(bloco.efeito);
  if (efeito) linhas.push(`Efeito: ${efeito}.`);

  return linhas;
}

export function montarPrompt({ blocos, clima, ritmo }: EntradaDoPrompt): string {
  if (blocos.length === 0) return "";

  const abertura =
    `Crie um vídeo vertical em formato 9:16, com duração de ${duracaoPorExtenso(duracaoDoRoteiro(blocos))}, ` +
    "em português do Brasil. Um apresentador virtual (avatar) fala para a câmera, cena a cena, " +
    "seguindo o roteiro abaixo.";

  const edicao = [clima ? DO_CLIMA[clima].edicao : null, ritmo ? DO_RITMO[ritmo].edicao : null].filter(
    (linha): linha is string => linha !== null,
  );

  return [
    abertura,
    secao("Narrador", [
      `Tom: ${clima ? DO_CLIMA[clima].narrador : CLIMA_NEUTRO}`,
      `Ritmo: ${ritmo ? DO_RITMO[ritmo].narrador : RITMO_NEUTRO}`,
    ]),
    secao("Edição", [
      ...(edicao.length > 0 ? edicao : [EDICAO_NEUTRA]),
      "Use só os ícones, as transições e os efeitos indicados em cada cena.",
    ]),
    secao("Cenas", [blocos.map((bloco, indice) => linhasDaCena(bloco, indice + 1).join("\n")).join("\n\n")]),
    secao("Regras", REGRAS.map((regra) => `- ${regra}`)),
  ].join("\n\n");
}
