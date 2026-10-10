// O selo pequeno que acompanha quase tudo na tela: estado do Laudo, decisão, fonte, modo.
import type { ReactNode } from "react";
import type { TomChip } from "../lib/matriz";

const BORDA_E_TEXTO: Record<TomChip, string> = {
  neutro: "border-linha text-suave",
  forte: "border-transparent bg-cartao-2 text-texto",
  ok: "border-linha text-suave",
  alerta: "border-linha text-suave",
  ruim: "border-suno/45 text-[#ff8b82]",
};

const PONTO: Partial<Record<TomChip, string>> = {
  ok: "bg-ok",
  alerta: "bg-alerta",
  ruim: "bg-suno",
};

export default function Chip({ tom = "neutro", children }: { tom?: TomChip; children: ReactNode }) {
  const ponto = PONTO[tom];
  return (
    <span
      className={`inline-flex items-center gap-1.5 whitespace-nowrap rounded-full border px-2 py-px text-[10.5px] ${BORDA_E_TEXTO[tom]}`}
    >
      {ponto && <span className={`h-1.5 w-1.5 rounded-full ${ponto}`} />}
      {children}
    </span>
  );
}
