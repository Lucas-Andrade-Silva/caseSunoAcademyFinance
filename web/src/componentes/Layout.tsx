// A casca: menu lateral e a área de conteúdo.
// O número vermelho em Saídas conta as Saídas aguardando revisão e se atualiza a cada
// navegação.
import type { ReactNode } from "react";
import { NavLink, useLocation } from "react-router-dom";
import { listarExecucoes } from "../dados/cliente";
import { usarRequisicao } from "../ganchos/usarRequisicao";
import { contarAguardando } from "../lib/matriz";

const GUIAS = [
  { para: "/fontes", rotulo: "Fontes" },
  { para: "/referencias", rotulo: "Configuração visual" },
  { para: "/saidas", rotulo: "Saídas" },
] as const;

export default function Layout({ children }: { children: ReactNode }) {
  const { pathname } = useLocation();
  // Enquanto alguma Saída é gerada, o contador se atualiza sozinho: ao terminar, ela passa a
  // contar como aguardando revisão sem o usuário precisar navegar.
  const estado = usarRequisicao(listarExecucoes, [pathname], {
    atualizarACada: (dados) =>
      dados.some(
        (saida) => saida.status === "na_fila" || saida.status === "gerando",
      )
        ? 3000
        : null,
  });
  const aguardando =
    estado.situacao === "pronto" ? contarAguardando(estado.dados) : 0;

  return (
    <div className="flex min-h-screen flex-col bg-fundo text-texto md:flex-row">
      <aside className="flex w-full shrink-0 items-center gap-1 overflow-x-auto border-b border-linha bg-lateral px-2.5 py-2 md:sticky md:top-0 md:h-screen md:w-[172px] md:flex-col md:items-stretch md:overflow-visible md:border-b-0 md:border-r md:py-3.5">
        <div className="shrink-0 px-2 text-[15px] font-bold tracking-[0.28em] md:pb-4 md:pt-1">
          <span className="font-normal text-suno">(</span> SUNO{" "}
          <span className="font-normal text-suno">)</span>
        </div>
        {GUIAS.map((guia) => (
          <NavLink
            key={guia.para}
            to={guia.para}
            className={({ isActive: ativaPelaRota }) => {
              const isActive =
                ativaPelaRota ||
                (guia.para === "/fontes" && pathname === "/curadoria");
              return `flex shrink-0 items-center gap-2.5 whitespace-nowrap rounded-[9px] px-2.5 py-2 text-[13px] ${
                isActive
                  ? "bg-suno/15 font-semibold text-texto"
                  : "text-suave hover:text-texto"
              }`;
            }}
          >
            {({ isActive: ativaPelaRota }) => {
              const isActive =
                ativaPelaRota ||
                (guia.para === "/fontes" && pathname === "/curadoria");
              return (
                <>
                  <span
                    className={`h-1.5 w-1.5 rounded-full ${isActive ? "bg-suno" : "bg-linha"}`}
                  />
                  {guia.rotulo}
                  {guia.para === "/saidas" && aguardando > 0 && (
                    <b className="ml-auto rounded-full bg-suno px-1.5 text-[10px] font-semibold text-white">
                      {aguardando}
                    </b>
                  )}
                </>
              );
            }}
          </NavLink>
        ))}
      </aside>
      <main className="min-w-0 flex-1">{children}</main>
    </div>
  );
}
