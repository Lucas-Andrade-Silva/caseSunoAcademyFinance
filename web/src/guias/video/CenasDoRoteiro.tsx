// As cenas do roteiro, uma abaixo da outra: o intervalo, a fala, a rubrica da tela em cinza e, em
// letra pequena, o que a Direção de cena escolheu (cena e ícone). Cada cena tem "Editar cena", que
// troca o texto por campos para corrigir a fala e o texto da tela; a edição fina (entrada, efeito)
// fica para o prompt, para a lista não poluir.
import { useEffect, useState } from "react";
import type { BlocoFala } from "../../dados/cliente";
import Botao from "../../interface/Botao";
import CampoDeTexto from "../../interface/CampoDeTexto";
import { direcaoDaCena } from "./direcao";
import { formatarIntervalo } from "./tempo";

export type CamposDaCena = Pick<BlocoFala, "fala" | "tela">;
const SEM_PROBLEMAS: ReadonlySet<number> = new Set();

interface Propriedades {
  blocos: readonly BlocoFala[];
  aoEditar?: (indice: number, campos: Partial<CamposDaCena>) => void;
  indicesComProblema?: ReadonlySet<number>;
}

export default function CenasDoRoteiro({ blocos, aoEditar, indicesComProblema = SEM_PROBLEMAS }: Propriedades) {
  const [editando, definirEditando] = useState<ReadonlySet<number>>(() => new Set());

  useEffect(() => {
    if (indicesComProblema.size === 0) return;
    definirEditando((atuais) => new Set([...atuais, ...indicesComProblema]));
  }, [indicesComProblema]);

  function alternar(indice: number) {
    definirEditando((atuais) => {
      const proximas = new Set(atuais);
      if (proximas.has(indice)) proximas.delete(indice);
      else proximas.add(indice);
      return proximas;
    });
  }

  return (
    <ol className="flex flex-col gap-2.5">
      {blocos.map((bloco, indice) => (
        <li
          key={indice}
          id={`cena-corrigivel-${indice}`}
          className={`surge scroll-mt-6 rounded-lg bg-superficie px-5 py-4 ${indicesComProblema.has(indice) ? "ring-2 ring-coral/70" : ""}`}
          style={{ animationDelay: `${Math.min(indice, 8) * 40}ms` }}
        >
          <div className="flex items-baseline justify-between gap-4 text-[13px] text-etiqueta">
            <span className="shrink-0 tabular-nums">{formatarIntervalo(bloco.inicio_s, bloco.fim_s)}</span>
            <span className="min-w-0 truncate text-right">{direcaoDaCena(bloco)}</span>
          </div>
          {aoEditar && editando.has(indice) ? (
            <div className="mt-3 grid gap-4">
              <CampoDeTexto rotulo="Fala" rows={3} valor={bloco.fala} aoMudar={(fala) => aoEditar(indice, { fala })} />
              <CampoDeTexto
                rotulo="Texto na tela"
                rows={2}
                valor={bloco.tela}
                aoMudar={(tela) => aoEditar(indice, { tela })}
              />
            </div>
          ) : (
            <>
              <p className="mt-2.5 text-[16px] leading-snug">{bloco.fala}</p>
              {bloco.tela && <p className="mt-2 text-[14px] leading-snug text-etiqueta">{bloco.tela}</p>}
            </>
          )}
          {aoEditar && (
            <div className="mt-3">
              <Botao variante="contorno" tamanho="pequeno" aria-pressed={editando.has(indice)} onClick={() => alternar(indice)}>
                {editando.has(indice) ? "Concluir edição" : "Editar cena"}
              </Botao>
            </div>
          )}
        </li>
      ))}
    </ol>
  );
}
