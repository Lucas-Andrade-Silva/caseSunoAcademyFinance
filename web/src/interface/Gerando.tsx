// O único carregamento que o app mostra: enquanto o servidor gera. Mostra o que ele está fazendo
// agora (a fase do andamento) e, por Célula, a etapa. Tudo o mais vem do cache pré-carregado.
import type { Andamento, Audiencia } from "../dados/cliente";
import { CAMADAS_DA_AVALIACAO, rotuloAudiencia, rotuloEtapa, rotuloFase } from "../texto/rotulos";

export default function Gerando({
  rotulo,
  andamento,
  audiencias,
}: {
  rotulo: string;
  andamento: Andamento | null;
  audiencias: readonly Audiencia[];
}) {
  const celulas = andamento?.celulas ?? [];
  // A camada de avaliação mais adiantada entre as Células: as anteriores já passaram.
  const camadaAtual = Math.max(
    -1,
    ...celulas.map((c) => CAMADAS_DA_AVALIACAO.findIndex((camada) => camada.etapa === c.etapa)),
  );
  return (
    <div
      role="status"
      aria-live="polite"
      className="surge mx-auto flex w-full max-w-[469px] flex-col items-stretch gap-8 py-16"
    >
      <div>
        <p className="text-[24px] leading-tight">{rotulo}</p>
        <p className="mt-2 text-[15px] text-etiqueta">{rotuloFase(andamento?.fase)}</p>
        {camadaAtual >= 0 && (
          <ul className="mt-3 flex flex-col gap-1 text-[15px]">
            {CAMADAS_DA_AVALIACAO.map((camada, indice) => (
              <li
                key={camada.etapa}
                aria-current={indice === camadaAtual ? "step" : undefined}
                className={
                  indice === camadaAtual
                    ? "text-texto"
                    : indice < camadaAtual
                      ? "text-etiqueta line-through decoration-etiqueta/50"
                      : "text-etiqueta/60"
                }
              >
                {camada.rotulo}
                {indice === camadaAtual && "…"}
              </li>
            ))}
          </ul>
        )}
      </div>
      <div className="flex flex-col gap-3" aria-hidden="true">
        {[100, 92, 96, 64].map((largura, indice) => (
          <span
            key={indice}
            className="pulsa h-3 rounded-full bg-superficie"
            style={{ width: `${largura}%`, animationDelay: `${indice * 160}ms` }}
          />
        ))}
      </div>
      {audiencias.length > 1 && (
        <ul className="flex flex-col gap-2.5">
          {audiencias.map((audiencia) => {
            const celula = celulas.find((c) => c.audiencia === audiencia);
            const etapa = rotuloEtapa(celula?.etapa ?? "aguardando", celula?.rodada ?? 0, false);
            return (
              <li
                key={audiencia}
                className="flex items-center justify-between rounded-lg bg-superficie px-5 py-3.5 text-[15px]"
              >
                <span>{rotuloAudiencia(audiencia)}</span>
                <span className="text-etiqueta">{etapa.titulo}</span>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
