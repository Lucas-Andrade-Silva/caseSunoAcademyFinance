// A atuação do avatar que vem do plano do servidor (`/roteiro/plano`): o padrão fixo (olhar,
// postura, gestos), a voz com pausas e pronúncia, as legendas e, por cena, o que a LLM escolheu
// (expressão, gesto, entonação, pausa). Função pura (Vitest cobre): lê o JSON e devolve linhas.

export interface AtuacaoDaCena {
  expressao: string;
  gesto: string;
  entonacao: string;
  pausa_depois_s: number;
}

export interface AtuacaoDoPlano {
  geral: string[];
  voz: string[];
  pronuncia: string[];
  legendas: string[];
  cenas: (AtuacaoDaCena | null)[];
}

const EXPRESSOES: Record<string, string> = {
  serena: "serena",
  acolhedora: "acolhedora, sorriso contido",
  atenta: "atenta",
  seria: "séria",
};
const GESTOS: Record<string, string> = {
  nenhum: "sem gesto",
  minimo: "um gesto curto de mão",
  apontar_para_tela: "aponta para o texto na tela",
  enumerar_nos_dedos: "marca os itens nos dedos",
};
const ENTONACOES: Record<string, string> = {
  firme: "firme, cai no fim",
  ascendente: "sobe no fim (pergunta)",
  descendente: "desacelera e baixa no fim",
  neutra: "neutra",
};

type Objeto = Record<string, unknown>;
const ehObjeto = (v: unknown): v is Objeto => typeof v === "object" && v !== null && !Array.isArray(v);
const texto = (v: unknown): string | null => (typeof v === "string" && v.trim() ? v.trim() : null);
const numero = (v: unknown): number | null => (typeof v === "number" && Number.isFinite(v) ? v : null);
const segundos = (s: number) => `${String(Math.round(s * 100) / 100).replace(".", ",")} s`;

function cenaDe(v: unknown): AtuacaoDaCena | null {
  if (!ehObjeto(v) || !ehObjeto(v.atuacao)) return null;
  const a = v.atuacao;
  const pausa = numero(a.pausa_depois_s);
  if (!texto(a.expressao) || !texto(a.gesto) || !texto(a.entonacao) || pausa === null) return null;
  return { expressao: a.expressao as string, gesto: a.gesto as string, entonacao: a.entonacao as string, pausa_depois_s: pausa };
}

/** Lê o `plano` do servidor; `null` quando ele não traz atuação (plano antigo, versão 1). */
export function lerAtuacao(plano: unknown): AtuacaoDoPlano | null {
  if (!ehObjeto(plano) || !ehObjeto(plano.avatar)) return null;
  const avatar = plano.avatar;
  if (!ehObjeto(avatar.atuacao) || !ehObjeto(avatar.voz)) return null;
  const at = avatar.atuacao;
  const voz = avatar.voz;

  const geral = [
    texto(at.olhar) && `Olhar: ${at.olhar}.`,
    texto(at.postura) && `Postura: ${at.postura}.`,
    texto(at.movimento_da_cabeca) && `Cabeça: ${at.movimento_da_cabeca}.`,
    texto(at.gestos) && `Gestos: ${at.gestos}.`,
    texto(at.expressao_geral) && `Expressão: ${at.expressao_geral}.`,
    texto(at.energia) && `Energia: ${at.energia}.`,
    Array.isArray(at.proibido) && at.proibido.length > 0 && `Evite: ${at.proibido.join("; ")}.`,
  ].filter((l): l is string => typeof l === "string");

  const pausas = ehObjeto(voz.pausas) ? voz.pausas : {};
  const entonacao = ehObjeto(voz.entonacao) ? voz.entonacao : {};
  const vozLinhas = [
    texto(voz.estilo) && `Estilo: ${voz.estilo}.`,
    numero(pausas.entre_ideias_s) !== null &&
      `Pausas: ${segundos(pausas.entre_ideias_s as number)} entre ideias` +
        (numero(pausas.antes_de_numero_s) !== null ? `, ${segundos(pausas.antes_de_numero_s as number)} antes de número` : "") +
        (numero(pausas.depois_de_numero_s) !== null ? `, ${segundos(pausas.depois_de_numero_s as number)} depois de número` : "") +
        (numero(pausas.depois_do_gancho_s) !== null ? `, ${segundos(pausas.depois_do_gancho_s as number)} depois do gancho` : "") +
        ".",
    texto(entonacao.numero) && `Números: ${entonacao.numero}.`,
    texto(entonacao.sigla) && `Siglas: ${entonacao.sigla}.`,
    texto(voz.numeros) && `${voz.numeros}.`,
    texto(voz.se_voz_clonada) && `Se a voz for clonada: ${voz.se_voz_clonada}.`,
  ].filter((l): l is string => typeof l === "string");

  const pronuncia = ehObjeto(voz.pronuncia)
    ? Object.entries(voz.pronuncia)
        .filter(([, como]) => typeof como === "string")
        .map(([termo, como]) => `"${termo}" → ${como}`)
    : [];

  const leg = ehObjeto(plano.legendas) ? plano.legendas : null;
  const legendas = leg
    ? [
        `Posição: faixa inferior, a ${leg.y_px} px do topo, margem lateral de ${leg.margem_lateral_px} px, alinhada à ${leg.alinhamento}.`,
        `Tamanho: ${leg.tamanho_px} px, peso ${leg.peso}, cor ${leg.cor}${ehObjeto(leg.contorno) ? ` com contorno ${leg.contorno.cor} de ${leg.contorno.largura_px} px` : ""}.`,
        `No máximo ${leg.linhas_maximas} linhas, ${leg.palavras_por_linha} palavras por linha; acompanha a fala palavra por palavra.`,
        ...(Array.isArray(leg.regras_de_colisao) ? leg.regras_de_colisao.map((r) => `${r}.`) : []),
      ]
    : [];

  const cenas = Array.isArray(plano.cenas) ? plano.cenas.map(cenaDe) : [];
  return { geral, voz: vozLinhas, pronuncia, legendas, cenas };
}

/** A linha "Atuação" de uma cena. */
export function linhaDaAtuacao(a: AtuacaoDaCena): string {
  const expressao = EXPRESSOES[a.expressao] ?? a.expressao;
  const gesto = GESTOS[a.gesto] ?? a.gesto;
  const entonacao = ENTONACOES[a.entonacao] ?? a.entonacao;
  const pausa = a.pausa_depois_s > 0 ? `; pausa de ${segundos(a.pausa_depois_s)} ao fim` : "";
  return `Atuação: expressão ${expressao}; ${gesto}; entonação ${entonacao}${pausa}.`;
}
