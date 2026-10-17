import Botao from "./Botao";
import { rotuloMetrica } from "../texto/rotulos";
import type { PontoDaCorrecao } from "../nucleo/correcoes";

interface Propriedades {
  pontos: readonly PontoDaCorrecao[];
  aoEditar?: () => void;
  aoSelecionar?: (indice: number) => void;
}

export default function PainelDeCorrecoes({ pontos, aoEditar, aoSelecionar }: Propriedades) {
  if (pontos.length === 0) return null;
  return (
    <section
      aria-label="Correções necessárias"
      className="rounded-xl border border-coral/40 bg-coral/10 px-4 py-4 text-[14px] leading-relaxed text-claro"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-[16px] font-semibold text-texto">Corrija para liberar</h2>
          <p className="mt-1 text-etiqueta">O Laudo marcou estes pontos na versão que acabou de ser gerada.</p>
        </div>
        {aoEditar && (
          <Botao variante="contorno" tamanho="pequeno" onClick={aoEditar}>Editar agora</Botao>
        )}
      </div>
      <ol className="mt-4 space-y-4">
        {pontos.map((ponto, indice) => (
          <li key={`${ponto.metrica}-${indice}`}>
            <p className="font-semibold text-coral-claro">{rotuloMetrica(ponto.metrica)}</p>
            {ponto.ocorrencias.length > 0 ? (
              <ul className="mt-2 space-y-2">
                {ponto.ocorrencias.map((ocorrencia, ocorrenciaIndice) => (
                  <li key={`${ocorrencia.local}-${ocorrenciaIndice}`}>
                    <button
                      type="button"
                      onClick={() => aoSelecionar?.(ocorrencia.indice)}
                      className="w-full rounded-lg bg-fundo px-3 py-2 text-left transition-colors hover:bg-superficie-alta"
                    >
                      <span className="block text-[12px] font-semibold uppercase tracking-[0.02em] text-coral-claro">
                        {ocorrencia.local}
                      </span>
                      <q className="mt-1 block text-texto">{ocorrencia.trecho}</q>
                    </button>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="mt-1 font-medium text-texto">Onde: conteúdo inteiro.</p>
            )}
            <p className="mt-2 whitespace-pre-line text-etiqueta">{ponto.instrucao}</p>
          </li>
        ))}
      </ol>
      <p className="mt-4 border-t border-coral/25 pt-3 text-etiqueta">
        Depois da edição, use <strong className="text-claro">Salvar texto e reavaliar</strong>. As próximas etapas serão liberadas quando o novo Laudo aprovar esta versão.
      </p>
    </section>
  );
}
