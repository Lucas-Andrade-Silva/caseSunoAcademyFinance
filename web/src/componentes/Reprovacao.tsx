// A reprovação como view de primeira classe (ADR 0013): para cada motivo, a métrica, o
// Limiar (Faixa), o valor medido e a distância, mais as observações e a instrução de
// Correcao que o Gerador recebeu. Medida `ausente` nunca aparece como zero.
import type { Destino, Laudo } from "../dados/cliente";
import {
  descreverFaixa,
  formatarNumero,
  rotuloMetrica,
  rotuloMotivo,
} from "../texto/rotulos";

/** `destinoFinal` é o da Célula depois do Ciclo; sem ele, vale o destino do próprio Laudo. */
export default function Reprovacao({
  laudo,
  destinoFinal,
}: {
  laudo: Laudo;
  destinoFinal?: Destino;
}) {
  const destino = destinoFinal ?? laudo.destino;
  if (destino === "aprovado") {
    return null;
  }

  const motivos = laudo.motivos ?? [];
  const correcoes = laudo.correcoes ?? [];

  return (
    <section className="rounded-2xl border border-suno/45 bg-suno/10 p-4">
      <h3 className="text-base font-semibold text-[#ffb3ad]">Por que reprovou</h3>
      <ul className="mt-2 flex flex-wrap gap-2">
        {motivos.map((motivo) => (
          <li
            key={motivo}
            className="rounded-full bg-suno/25 px-2.5 py-1 text-xs font-medium text-[#ffd0cc]"
          >
            {rotuloMotivo(motivo)}
          </li>
        ))}
      </ul>

      <div className="mt-4 space-y-3">
        {laudo.medidas
          .filter((medida) => medida.atingiu === false || medida.estado !== "medida")
          .map((medida) => (
            <div key={medida.metrica} className="rounded-lg bg-cartao p-3 text-sm">
              <p className="font-medium">{rotuloMetrica(medida.metrica)}</p>
              {medida.estado === "ausente" && <p>sem base para medir</p>}
              {medida.estado === "revisao_humana" && <p>aguardando desempate (H3)</p>}
              {medida.estado === "medida" && (
                <p>
                  Limiar: {descreverFaixa(medida.faixa)} · valor medido:{" "}
                  {formatarNumero(medida.valor)}
                </p>
              )}
              {medida.observacoes && medida.observacoes.length > 0 && (
                <ul className="mt-1 list-inside list-disc text-suave">
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
          <p className="text-sm font-medium text-[#ffb3ad]">Instrução para a correção</p>
          {correcoes.map((correcao) => (
            <div key={correcao.metrica} className="rounded-lg bg-cartao p-3 text-sm">
              <p>{correcao.instrucao}</p>
              {correcao.distancia !== null && correcao.distancia !== undefined && (
                <p className="text-suave">
                  distância até o Limiar: {formatarNumero(correcao.distancia)}
                </p>
              )}
            </div>
          ))}
        </div>
      )}

      {destino === "reprovado_revisao_humana" && (
        <p className="mt-3 text-sm text-[#ffb3ad]">
          Foi para a revisão humana: duas rodadas de correção não resolveram, ou a extração
          falhou.
        </p>
      )}
    </section>
  );
}
