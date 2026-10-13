// Os botões do editor de referência: o retângulo branco de caixa alta (CRIAR AUTOMAÇÃO, na
// referência) e o escuro com texto branco (UPDATE). Um só vocabulário para o app inteiro.
import type { ButtonHTMLAttributes, ReactNode } from "react";

type Aparencia = "claro" | "escuro" | "contorno";
type Tamanho = "grande" | "normal" | "pequeno";

const VARIANTES: Record<Aparencia, string> = {
  claro: "bg-white text-ilha hover:bg-claro disabled:hover:bg-white",
  escuro: "bg-superficie text-texto hover:bg-superficie-alta disabled:hover:bg-superficie",
  contorno: "border border-[#3d3d3d] text-texto hover:bg-superficie disabled:hover:bg-transparent",
};

const TAMANHOS: Record<Tamanho, string> = {
  grande: "h-[70px] w-full rounded-xl px-6 text-[15px]",
  normal: "h-[50px] rounded-lg px-7 text-[15px]",
  pequeno: "h-9 rounded-lg px-4 text-[13px]",
};

interface Propriedades extends ButtonHTMLAttributes<HTMLButtonElement> {
  variante?: Aparencia;
  tamanho?: Tamanho;
  icone?: ReactNode;
}

export default function Botao({
  variante = "escuro",
  tamanho = "normal",
  icone,
  className = "",
  children,
  type = "button",
  ...resto
}: Propriedades) {
  return (
    <button
      type={type}
      className={`inline-flex shrink-0 items-center justify-center gap-2.5 font-semibold uppercase tracking-[0.01em] transition-colors duration-150 disabled:cursor-not-allowed disabled:opacity-40 ${VARIANTES[variante]} ${TAMANHOS[tamanho]} ${className}`}
      {...resto}
    >
      {icone}
      {children}
    </button>
  );
}
