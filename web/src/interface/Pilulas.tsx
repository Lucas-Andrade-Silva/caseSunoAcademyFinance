// As pílulas de filtro do editor de referência (ALL · 1D · 7D · 30D): a ativa é branca com texto
// escuro; as outras são só texto. Serve para escolha única (`valor`) e para múltipla
// (`marcados`).
import type { ReactNode } from "react";

interface Opcao<V extends string> {
  valor: V;
  rotulo: ReactNode;
  desabilitada?: boolean;
}

interface Base<V extends string> {
  opcoes: readonly Opcao<V>[];
  rotuloAcessivel: string;
  className?: string;
}

interface Unica<V extends string> extends Base<V> {
  valor: V;
  onMudar: (valor: V) => void;
}

interface Multipla<V extends string> extends Base<V> {
  marcados: readonly V[];
  onAlternar: (valor: V) => void;
}

function Botao({
  ativa,
  desabilitada,
  onClick,
  children,
}: {
  ativa: boolean;
  desabilitada?: boolean;
  onClick: () => void;
  children: ReactNode;
}) {
  return (
    <button
      type="button"
      aria-pressed={ativa}
      disabled={desabilitada}
      onClick={onClick}
      className={`h-9 shrink-0 rounded-full px-5 text-[14px] font-bold uppercase tracking-[0.01em] transition-colors duration-150 disabled:cursor-not-allowed disabled:opacity-40 ${
        ativa ? "bg-white text-ilha" : "text-texto hover:bg-superficie"
      }`}
    >
      {children}
    </button>
  );
}

export function Pilulas<V extends string>({
  opcoes,
  valor,
  onMudar,
  rotuloAcessivel,
  className = "",
}: Unica<V>) {
  return (
    <div role="group" aria-label={rotuloAcessivel} className={`flex flex-wrap items-center gap-1 ${className}`}>
      {opcoes.map((opcao) => (
        <Botao
          key={opcao.valor}
          ativa={opcao.valor === valor}
          desabilitada={opcao.desabilitada}
          onClick={() => onMudar(opcao.valor)}
        >
          {opcao.rotulo}
        </Botao>
      ))}
    </div>
  );
}

export function PilulasMultiplas<V extends string>({
  opcoes,
  marcados,
  onAlternar,
  rotuloAcessivel,
  className = "",
}: Multipla<V>) {
  return (
    <div role="group" aria-label={rotuloAcessivel} className={`flex flex-wrap items-center gap-1 ${className}`}>
      {opcoes.map((opcao) => (
        <Botao
          key={opcao.valor}
          ativa={marcados.includes(opcao.valor)}
          desabilitada={opcao.desabilitada}
          onClick={() => onAlternar(opcao.valor)}
        >
          {opcao.rotulo}
        </Botao>
      ))}
    </div>
  );
}
