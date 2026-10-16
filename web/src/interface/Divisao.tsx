// O esqueleto de toda guia: coluna de ajustes à esquerda (469 px, centrada entre a barra e a
// metade da tela) e a área de prévia à direita, que é mais escura e tem a barra do topo com a
// pílula de contexto e o botão de ação, como o "URL: bio.site/..." e o UPDATE da referência.
// Cada lado rola sozinho; abaixo de 1024 px os dois se empilham.
import type { ReactNode } from "react";
import { usarNovaGeracao } from "../nucleo/novaGeracao";
import { IconeMais } from "./Icones";

export function Divisao({
  esquerda,
  direita,
  larguraDaColuna = 469,
}: {
  esquerda: ReactNode;
  direita: ReactNode;
  larguraDaColuna?: number;
}) {
  return (
    <div className="grid min-h-full grid-cols-1 lg:h-full lg:grid-cols-2">
      <section
        className="min-h-0 px-5 pb-24 pt-[44px] lg:overflow-y-auto lg:pb-16 lg:pl-[var(--area-da-rail)] lg:pr-0"
      >
        <div className="mx-auto w-full" style={{ maxWidth: larguraDaColuna }}>
          {esquerda}
        </div>
      </section>
      <section className="flex min-h-[70vh] min-w-0 flex-col bg-previa lg:h-full lg:min-h-0">
        {direita}
      </section>
    </div>
  );
}

/** A barra do topo da área de prévia: pílula de contexto à esquerda, ações à direita. */
export function TopoDaPrevia({
  esquerda,
  direita,
}: {
  esquerda?: ReactNode;
  direita?: ReactNode;
}) {
  return (
    <header className="flex shrink-0 flex-wrap items-center justify-between gap-3 px-5 pb-3 pt-10 lg:px-[50px]">
      <div className="flex min-w-0 flex-wrap items-center gap-2">{esquerda}</div>
      <div className="flex flex-wrap items-center gap-3">{direita}</div>
    </header>
  );
}

/** O corpo rolável da área de prévia, abaixo do topo. */
export function CorpoDaPrevia({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div className={`min-h-0 flex-1 overflow-y-auto px-5 pb-10 lg:px-[50px] ${className}`}>
      {children}
    </div>
  );
}

/** O título de página (32 px, leve) e o de seção (24 px). */
export function Titulo({ children }: { children: ReactNode }) {
  return <h1 className="text-[32px] font-normal leading-tight tracking-[-0.005em]">{children}</h1>;
}

/** O título de uma guia que gera, com o "+" de nova geração ao lado (só com uma Saída pronta). */
export function TituloDaGuia({ children }: { children: ReactNode }) {
  const novaGeracao = usarNovaGeracao();
  return (
    <div className="flex items-center gap-3">
      <Titulo>{children}</Titulo>
      {novaGeracao && (
        <button
          type="button"
          onClick={novaGeracao}
          aria-label="Nova geração"
          title="Nova geração"
          className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-superficie text-texto transition-colors duration-150 hover:bg-superficie-alta"
        >
          <IconeMais size={18} />
        </button>
      )}
    </div>
  );
}

export function TituloDeSecao({ children }: { children: ReactNode }) {
  return <h2 className="text-[24px] font-normal leading-tight text-claro">{children}</h2>;
}

/** O rótulo pequeno em caixa alta que agrupa linhas ("SELL" na referência). */
export function Rotulo({ children }: { children: ReactNode }) {
  return <h3 className="text-[12px] font-medium uppercase tracking-[0.02em] text-texto">{children}</h3>;
}

/** A pílula escura de contexto (a "URL" da referência). */
export function Ilha({ children }: { children: ReactNode }) {
  return (
    <span className="inline-flex h-[50px] items-center rounded-[25px] bg-ilha px-[27px] text-[15px] font-medium">
      {children}
    </span>
  );
}
