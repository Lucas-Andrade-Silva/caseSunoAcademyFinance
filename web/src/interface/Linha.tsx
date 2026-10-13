// A linha de cartão do editor de referência: quadrado colorido com ícone, título, subtítulo
// opcional e, na ponta, a seta (abre) ou o mais (adiciona). 70 px de altura, raio 8, 10 px de
// espaço entre uma e outra.
import type { ReactNode } from "react";
import { IconeMais, IconeSeta } from "./Icones";

export type CorDoQuadrado = "azul" | "marinho" | "roxo" | "amarelo" | "coral" | "verde" | "cinza";

const COR: Record<CorDoQuadrado, string> = {
  azul: "bg-azul text-white",
  marinho: "bg-marinho text-white",
  roxo: "bg-roxo text-white",
  amarelo: "bg-amarelo text-ilha",
  coral: "bg-coral text-white",
  verde: "bg-verde text-ilha",
  cinza: "bg-superficie-alta text-claro",
};

export function Quadrado({
  cor,
  children,
  tamanho = 40,
}: {
  cor: CorDoQuadrado;
  children: ReactNode;
  tamanho?: number;
}) {
  return (
    <span
      className={`grid shrink-0 place-items-center rounded-[5px] ${COR[cor]}`}
      style={{ width: tamanho, height: tamanho }}
    >
      {children}
    </span>
  );
}

interface Propriedades {
  cor: CorDoQuadrado;
  icone: ReactNode;
  titulo: string;
  subtitulo?: string;
  /** "coral" pinta o subtítulo como o aviso "Add Payment Provider" da referência. */
  tomDoSubtitulo?: "mudo" | "coral";
  fim?: "seta" | "mais" | ReactNode | null;
  selecionada?: boolean;
  desabilitada?: boolean;
  onClick?: () => void;
}

export default function Linha({
  cor,
  icone,
  titulo,
  subtitulo,
  tomDoSubtitulo = "mudo",
  fim = "seta",
  selecionada = false,
  desabilitada = false,
  onClick,
}: Propriedades) {
  const pontaPadrao = fim === "seta" ? <IconeSeta size={20} className="text-claro" /> : fim === "mais" ? <IconeMais size={20} className="text-claro" /> : fim;
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={desabilitada}
      aria-pressed={onClick ? selecionada : undefined}
      className={`group flex h-[70px] w-full items-center gap-4 rounded-lg px-[21px] text-left transition-colors duration-150 ${
        selecionada ? "bg-superficie-alta" : "bg-superficie hover:bg-superficie-alta"
      } ${desabilitada ? "cursor-not-allowed opacity-50 hover:bg-superficie" : ""}`}
    >
      <Quadrado cor={cor}>{icone}</Quadrado>
      <span className="min-w-0 flex-1">
        <span className="block truncate text-[17px] leading-tight text-texto">{titulo}</span>
        {subtitulo && (
          <span
            className={`mt-0.5 block truncate text-[13px] leading-tight ${
              tomDoSubtitulo === "coral" ? "text-coral-claro" : "text-etiqueta"
            }`}
          >
            {subtitulo}
          </span>
        )}
      </span>
      {pontaPadrao && <span className="shrink-0 pr-1">{pontaPadrao}</span>}
    </button>
  );
}
