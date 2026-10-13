// A cara de cada origem na Ingestão: a cor do quadrado e o ícone. Origem desconhecida (nova no
// catálogo do servidor) cai no cinza com o ícone da guia.
import type { ReactNode } from "react";
import {
  IconeArquivoMais,
  IconeBalanca,
  IconeBanco,
  IconeGrafico,
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
  releases_b3: { cor: "amarelo", icone: (t) => <IconeGrafico size={t} /> },
  importados: { cor: "coral", icone: (t) => <IconeArquivoMais size={t} /> },
};

export function caraDaOrigem(identificador: string): CaraDaOrigem {
  return CARAS[identificador] ?? { cor: "cinza", icone: (t) => <IconeIngestao size={t} /> };
}
