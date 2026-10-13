// O Laudo em barras horizontais. A cor diz se atingiu (branco), se não atingiu (coral) ou se não
// há base para medir (cinza); as marcas são os limites do Limiar na escala da métrica.
import type { BarraDoLaudo } from "../nucleo/laudo";

function corDaBarra(atingiu: boolean | null): string {
  if (atingiu === true) return "bg-claro";
  if (atingiu === false) return "bg-coral";
  return "bg-mudo";
}

export default function Barras({ barras }: { barras: readonly BarraDoLaudo[] }) {
  if (barras.length === 0) return null;
  return (
    <ul className="flex flex-col gap-6 rounded-xl bg-superficie p-7">
      {barras.map((barra) => (
        <li key={barra.metrica}>
          <div className="mb-2.5 flex items-baseline justify-between gap-4">
            <span className="text-[17px]">{barra.rotulo}</span>
            <span className="text-[15px] tabular-nums text-claro">
              {barra.valor}
              {barra.faixa && <span className="ml-2 text-etiqueta">{barra.faixa}</span>}
            </span>
          </div>
          <div
            className="relative h-2.5 rounded-full bg-fundo"
            role="meter"
            aria-label={barra.rotulo}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={Math.round(barra.largura)}
          >
            <span
              className={`absolute inset-y-0 left-0 rounded-full transition-[width] duration-700 ease-[var(--ease-saida)] ${corDaBarra(barra.atingiu)}`}
              style={{ width: `${barra.largura}%` }}
            />
            {barra.marcas.map((marca) => (
              <span
                key={marca}
                className="absolute -top-1 h-[18px] w-0.5 rounded-full bg-mudo"
                style={{ left: `${marca}%` }}
              />
            ))}
          </div>
        </li>
      ))}
    </ul>
  );
}
