// O Laudo ao lado do conteúdo: cada métrica com barra, valor medido e a faixa do Limiar.
// A barra fica vermelha quando a métrica não atingiu; cinza quando não há base para medir.
import type { Destino, Laudo } from "../dados/cliente";
import { larguraDaBarra } from "../lib/matriz";
import { formatarNumero, resumirFaixa, rotuloDestino, rotuloMetrica } from "../texto/rotulos";
import Chip from "./Chip";

function corDaBarra(atingiu: boolean | null | undefined): string {
  if (atingiu === true) return "bg-ok";
  if (atingiu === false) return "bg-suno";
  return "bg-suave";
}

/**
 * `destinoFinal` é o destino da Célula depois do Ciclo de correção. O Laudo da última rodada
 * ainda pode dizer "correção possível" quando o teto de rodadas já mandou a Célula para a
 * revisão humana; o chip mostra o destino final, que é o que a Matriz também mostra.
 */
export default function SecaoLaudo({
  laudo,
  destinoFinal,
}: {
  laudo: Laudo;
  destinoFinal: Destino;
}) {
  const aprovado = destinoFinal === "aprovado";
  return (
    <section className="rounded-2xl bg-cartao p-3.5">
      <h2 className="mb-2 flex items-center gap-2 text-[12.5px] font-bold">
        Laudo
        <Chip tom={aprovado ? "ok" : "alerta"}>
          {aprovado ? "aprovada" : rotuloDestino(destinoFinal)}
        </Chip>
      </h2>
      <ul>
        {laudo.medidas.map((medida) => (
          <li
            key={medida.metrica}
            className="grid grid-cols-[110px_1fr_auto] items-center gap-2 border-t border-linha py-1.5 text-[11.5px] first:border-t-0"
          >
            <span>{rotuloMetrica(medida.metrica)}</span>
            <span className="relative h-1.5 rounded-full bg-cartao-2">
              <span
                className={`absolute inset-y-0 left-0 rounded-full ${corDaBarra(medida.atingiu)}`}
                style={{ width: `${larguraDaBarra(medida)}%` }}
              />
            </span>
            <span className="text-right font-mono tabular-nums">
              {formatarNumero(medida.valor)}{" "}
              <span className="text-suave">{resumirFaixa(medida.faixa)}</span>
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}
