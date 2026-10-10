// A casca: menu lateral com as três guias (Fontes, Curadoria, Saídas) e a área de conteúdo.
// O número vermelho em Saídas conta as Saídas aguardando revisão e se atualiza a cada
// navegação.
import type { ReactNode } from "react";
import { NavLink, useLocation } from "react-router-dom";
import { listarExecucoes } from "../dados/cliente";
import { usarRequisicao } from "../ganchos/usarRequisicao";
import { contarAguardando } from "../lib/matriz";

const GUIAS = [
  { para: "/fontes", rotulo: "Fontes" },
  { para: "/curadoria", rotulo: "Curadoria" },
  { para: "/saidas", rotulo: "Saídas" },
] as const;

export default function Layout({ children }: { children: ReactNode }) {
  const { pathname } = useLocation();
  const estado = usarRequisicao(listarExecucoes, [pathname]);
  const aguardando = estado.situacao === "pronto" ? contarAguardando(estado.dados) : 0;

  return (
    <div className="flex min-h-screen bg-fundo text-texto">
      <aside className="sticky top-0 flex h-screen w-[172px] shrink-0 flex-col gap-1 border-r border-linha bg-lateral px-2.5 py-3.5">
        <div className="px-2 pb-4 pt-1 text-[15px] font-bold tracking-[0.28em]">
          <span className="font-normal text-suno">(</span> SUNO{" "}
          <span className="font-normal text-suno">)</span>
        </div>
        {GUIAS.map((guia) => (
          <NavLink
            key={guia.para}
            to={guia.para}
            className={({ isActive }) =>
              `flex items-center gap-2.5 rounded-[9px] px-2.5 py-2 text-[13px] ${
                isActive ? "bg-suno/15 font-semibold text-texto" : "text-suave hover:text-texto"
              }`
            }
          >
            {({ isActive }) => (
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
            )}
          </NavLink>
        ))}
      </aside>
      <main className="min-w-0 flex-1">{children}</main>
    </div>
  );
}
