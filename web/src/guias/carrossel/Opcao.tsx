// A opção das escolhas em grade (tipos, paletas, ícones), no jeito das fontes do editor de referência:
// quadrado escuro com o desenho em cima e o nome embaixo; a escolhida fica clara, com texto escuro.
import type { ReactNode } from "react";

interface Propriedades {
  selecionada: boolean;
  rotulo: string;
  onClick: () => void;
  children: ReactNode;
  className?: string;
  /** Por que a opção não vale agora; com ela, a opção fica apagada e não responde ao clique. */
  indisponivel?: string | null;
}

export default function Opcao({ selecionada, rotulo, onClick, children, className = "", indisponivel = null }: Propriedades) {
  return (
    <button
      type="button"
      aria-pressed={selecionada}
      disabled={indisponivel !== null}
      title={indisponivel ?? undefined}
      onClick={onClick}
      className={`group flex flex-col items-center justify-center gap-2.5 rounded-lg px-2 py-3 transition-colors duration-150 disabled:cursor-not-allowed disabled:opacity-40 ${
        selecionada ? "bg-claro text-ilha" : "bg-superficie text-claro enabled:hover:bg-superficie-alta"
      } ${className}`}
    >
      {children}
      <span
        className={`max-w-full truncate text-[13px] leading-tight ${
          selecionada ? "text-ilha" : "text-etiqueta group-hover:text-claro"
        }`}
      >
        {rotulo}
      </span>
      {indisponivel && <span className="max-w-full text-center text-[11px] leading-tight text-etiqueta">{indisponivel}</span>}
    </button>
  );
}

/** A grade que acomoda as opções: de duas colunas no celular a quantas couberem na coluna de ajustes. */
export function Opcoes({
  rotuloAcessivel,
  largura,
  children,
}: {
  rotuloAcessivel: string;
  /** Largura mínima de cada opção, em px. */
  largura: number;
  children: ReactNode;
}) {
  return (
    <div
      role="group"
      aria-label={rotuloAcessivel}
      className="grid gap-2.5"
      style={{ gridTemplateColumns: `repeat(auto-fill, minmax(${largura}px, 1fr))` }}
    >
      {children}
    </div>
  );
}
