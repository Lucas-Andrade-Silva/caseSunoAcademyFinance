// A cara de cada origem na Ingestão: a cor do quadrado e o ícone. Origem desconhecida (nova no
// catálogo do servidor) cai no cinza com o ícone da guia.
import type { ReactNode } from "react";
import {
  IconeArquivoMais,
  IconeBalanca,
  IconeBanco,
  IconeIngestao,
  com,
} from "../../interface/Icones";
import type { CorDoQuadrado } from "../../interface/Linha";
import { ChartLine, FileSpreadsheet, Megaphone, ScrollText } from "lucide-react";

const IconeDemonstracoes = com(FileSpreadsheet);
const IconeRelatorios = com(ChartLine);
const IconeResolucoes = com(ScrollText);
const IconeOficios = com(Megaphone);

interface CaraDaOrigem {
  cor: CorDoQuadrado;
  icone: (tamanho: number) => ReactNode;
}

const CARAS: Record<string, CaraDaOrigem> = {
  copom: { cor: "azul", icone: (t) => <IconeBanco size={t} /> },
  cvm_fatos_relevantes: { cor: "roxo", icone: (t) => <IconeBalanca size={t} /> },
  cvm_demonstracoes: { cor: "marinho", icone: (t) => <IconeDemonstracoes size={t} /> },
  bcb_relatorios: { cor: "verde", icone: (t) => <IconeRelatorios size={t} /> },
  bcb_resolucoes: { cor: "cinza", icone: (t) => <IconeResolucoes size={t} /> },
  b3_oficios: { cor: "amarelo", icone: (t) => <IconeOficios size={t} /> },
  importados: { cor: "coral", icone: (t) => <IconeArquivoMais size={t} /> },
};

// De quanto em quanto tempo cada origem publica. A busca olha só os últimos 30 dias, então
// origens lentas costumam voltar vazias: o texto explica por quê.
const FREQUENCIAS: Record<string, string> = {
  copom: "O Copom publica a ata a cada 45 dias, cerca de 8 vezes por ano.",
  cvm_fatos_relevantes: "Fatos relevantes saem sempre que uma empresa tem novidade: vários por dia.",
  cvm_demonstracoes: "DFP uma vez por ano e ITR a cada trimestre; formulários variam por empresa.",
  bcb_relatorios:
    "O Relatório de Inflação sai a cada trimestre e o de Estabilidade Financeira a cada semestre. Por isso a busca de 30 dias costuma vir vazia.",
  bcb_resolucoes: "O CMN e o BCB publicam resoluções várias vezes por mês.",
  b3_oficios: "A B3 divulga ofícios e comunicados quase todo dia útil.",
  importados: "Só aparece o que você importa.",
};

export function frequenciaDaOrigem(identificador: string): string | null {
  return FREQUENCIAS[identificador] ?? null;
}

export function caraDaOrigem(identificador: string): CaraDaOrigem {
  return CARAS[identificador] ?? { cor: "cinza", icone: (t) => <IconeIngestao size={t} /> };
}
