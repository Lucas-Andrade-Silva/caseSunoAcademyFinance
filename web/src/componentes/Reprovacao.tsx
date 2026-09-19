// A reprovação como view de primeira classe (ADR 0013): para cada motivo, a métrica, o
// Limiar (Faixa), o valor medido e a distância, mais as observações e a instrução de
// Correcao que o Gerador recebeu. Medida `ausente` nunca aparece como zero.
import type { Faixa, Laudo } from "../dados/cliente";
import { formatarNumero, rotuloMetrica, rotuloMotivo } from "../texto/rotulos";

function faixaTexto(faixa: Faixa | null | undefined): string {
  if (!faixa || (faixa.minimo === null && faixa.maximo === null)) {
    return "sem Limiar definido";
  }
  if (faixa.minimo !== null && faixa.minimo !== undefined && faixa.maximo !== null && faixa.maximo !== undefined) {
    return `entre ${formatarNumero(faixa.minimo)} e ${formatarNumero(faixa.maximo)}`;
  }
  if (faixa.minimo !== null && faixa.minimo !== undefined) {
    return `a partir de ${formatarNumero(faixa.minimo)}`;
  }
  return `até ${formatarNumero(faixa.maximo)}`;
}

export default function Reprovacao({ laudo }: { laudo: Laudo }) {
  if (laudo.destino === "aprovado") {
    return null;
  }

  const motivos = laudo.motivos ?? [];
  const correcoes = laudo.correcoes ?? [];

  return (
    <section className="rounded-xl border-2 border-rose-300 bg-rose-50 p-4 dark:border-rose-800 dark:bg-rose-950">
      <h3 className="text-base font-semibold text-rose-900 dark:text-rose-100">Por que reprovou</h3>
      <ul className="mt-2 flex flex-wrap gap-2">
        {motivos.map((motivo) => (
          <li
            key={motivo}
            className="rounded-full bg-rose-200 px-2.5 py-1 text-xs font-medium text-rose-900 dark:bg-rose-900 dark:text-rose-100"
          >
            {rotuloMotivo(motivo)}
          </li>
        ))}
      </ul>

      <div className="mt-4 space-y-3">
        {laudo.medidas
          .filter((medida) => medida.atingiu === false || medida.estado !== "medida")
          .map((medida) => (
            <div
              key={medida.metrica}
              className="rounded-lg bg-white/70 p-3 text-sm dark:bg-slate-900/60"
            >
              <p className="font-medium">{rotuloMetrica(medida.metrica)}</p>
              {medida.estado === "ausente" && <p>sem base para medir</p>}
              {medida.estado === "revisao_humana" && <p>aguardando desempate (H3)</p>}
              {medida.estado === "medida" && (
                <p>
                  Limiar: {faixaTexto(medida.faixa)} · valor medido: {formatarNumero(medida.valor)}
                </p>
              )}
              {medida.observacoes && medida.observacoes.length > 0 && (
                <ul className="mt-1 list-inside list-disc text-slate-600 dark:text-slate-300">
                  {medida.observacoes.map((observacao, indice) => (
                    <li key={indice}>{observacao}</li>
                  ))}
                </ul>
              )}
            </div>
          ))}
      </div>

      {correcoes.length > 0 && (
        <div className="mt-4 space-y-2">
          <p className="text-sm font-medium text-rose-900 dark:text-rose-100">
            Instrução para a correção
          </p>
          {correcoes.map((correcao) => (
            <div
              key={correcao.metrica}
              className="rounded-lg bg-white/70 p-3 text-sm dark:bg-slate-900/60"
            >
              <p>{correcao.instrucao}</p>
              {correcao.distancia !== null && correcao.distancia !== undefined && (
                <p className="text-slate-500 dark:text-slate-400">
                  distância até o Limiar: {formatarNumero(correcao.distancia)}
                </p>
              )}
            </div>
          ))}
        </div>
      )}

      {laudo.destino === "reprovado_revisao_humana" && (
        <p className="mt-3 text-sm text-rose-800 dark:text-rose-200">
          Foi para a fila de revisão humana (H4): duas rodadas de correção não resolveram, ou a
          extração falhou.
        </p>
      )}
    </section>
  );
}
