// Monta o corpo do `POST /api/execucoes` a partir do que a pessoa escolheu: as Atas guardadas na
// Ingestão, as Audiências marcadas no popup e o Formato da guia. Lógica pura (Vitest cobre).
import type {
  Audiencia,
  ComposicaoCarrossel,
  DuracaoDoVideo,
  Formato,
  ModoDeGeracao,
  NovaSaida,
  ResumoDaAta,
} from "../dados/cliente";
import { nomePadrao } from "../lib/fontes";
import { rotuloFormato } from "../texto/rotulos";

export const MAXIMO_DA_VISAO_UNIDA = 5;

export interface ExtrasDaGeracao {
  /** Só vale para o Carrossel, e só junto de `referenciaVisual`. */
  composicaoVisual?: ComposicaoCarrossel;
  referenciaVisual?: string;
  duracao?: DuracaoDoVideo;
}

interface Entrada {
  formato: Formato;
  audiencias: readonly Audiencia[];
  atas: readonly ResumoDaAta[];
  modo: ModoDeGeracao;
  extras?: ExtrasDaGeracao;
}

/** O motivo de a geração não poder começar, ou `null`. O servidor confere de novo. */
export function motivoDeRecusa(entrada: Pick<Entrada, "atas" | "modo" | "audiencias">): string | null {
  const { atas, modo, audiencias } = entrada;
  if (atas.length === 0) return "Nenhuma notícia selecionada.";
  if (audiencias.length === 0) return "Escolha ao menos uma audiência.";
  if (atas.length > 1 && modo === "demo") {
    return "Com mais de uma notícia só o modo Real gera.";
  }
  if (modo === "demo" && atas.some((ata) => !ata.demo_disponivel)) {
    return "O modo Demo só tem respostas prontas para o Copom 280. Use o modo Real.";
  }
  if (atas.some((ata) => !ata.extracao_completa)) {
    return "Uma das notícias não tem data e número com unidade no texto.";
  }
  return null;
}

export function corpoDaSaida(entrada: Entrada): NovaSaida {
  const { formato, audiencias, atas, modo, extras } = entrada;
  const titulos = atas.map((ata) => ata.titulo);
  const base = nomePadrao(titulos, 100);
  const corpo: NovaSaida = {
    nome: `${base} · ${rotuloFormato(formato)}`.slice(0, 120),
    modo,
    comite: false,
    duracao: formato === "roteiro" ? (extras?.duracao ?? "60") : "60",
    pedido: audiencias.map((audiencia) => ({ audiencia, formato })),
    ...(atas.length === 1
      ? { ata: atas[0].identificador }
      : { itens: atas.map((ata) => ata.identificador) }),
  };
  if (formato === "carrossel" && extras?.composicaoVisual && extras.referenciaVisual) {
    corpo.composicao_visual = extras.composicaoVisual;
    corpo.referencia_visual = extras.referenciaVisual;
  }
  return corpo;
}
