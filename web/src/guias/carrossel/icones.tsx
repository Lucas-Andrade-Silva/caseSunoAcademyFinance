// Os 15 ícones do catálogo do vídeo desenhados em SVG (lucide). O vídeo desenha os dele em Pillow; aqui
// o carrossel usa o mesmo vocabulário de nomes, e a escolha nunca sai do catálogo.
import {
  CalendarDays,
  CircleArrowUp,
  CircleCheck,
  CircleQuestionMark,
  Clock,
  Equal,
  FileText,
  Landmark,
  Percent,
  Scale,
  Search,
  TrendingDown,
  TrendingUp,
  TriangleAlert,
  Wallet,
} from "lucide-react";
import type { ComponentType } from "react";
import { com } from "../../interface/Icones";
import type { IdDoIcone } from "./modelo";

const DESENHOS: Record<IdDoIcone, ReturnType<typeof com>> = {
  juros: com(Percent),
  inflacao: com(CircleArrowUp),
  grafico_alta: com(TrendingUp),
  grafico_queda: com(TrendingDown),
  grafico_estavel: com(Equal),
  calendario: com(CalendarDays),
  banco: com(Landmark),
  bolso: com(Wallet),
  alerta: com(TriangleAlert),
  lupa: com(Search),
  documento: com(FileText),
  balanca: com(Scale),
  relogio: com(Clock),
  pergunta: com(CircleQuestionMark),
  check: com(CircleCheck),
};

export type DesenhoDeIcone = ComponentType<{ size?: number; strokeWidth?: number; className?: string }>;

export function desenhoDoIcone(id: IdDoIcone): DesenhoDeIcone {
  return DESENHOS[id];
}
