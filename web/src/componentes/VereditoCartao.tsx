// O veredito em palavras, com o número ao lado — a marca da tela (ver ARQUITETURA.md,
// seção "A interface"). Destaque visual reservado à dimensão de Recomendação: é a linha
// que não se cruza (CLAUDE.md).
import type { Medida } from "../dados/cliente";
import { descreverMedida, formatarNumero, rotuloMetrica } from "../texto/rotulos";

export default function VereditoCartao({ medida }: { medida: Medida }) {
  const destaque = medida.metrica === "recomendacao";
  return (
    <div
      className={`flex items-center justify-between gap-3 rounded-lg border px-3 py-2 text-sm ${
        destaque
          ? "border-2 border-indigo-400 bg-indigo-50 font-medium dark:border-indigo-500 dark:bg-indigo-950"
          : "border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900"
      }`}
    >
      <span>
        <span className="text-slate-500 dark:text-slate-400">{rotuloMetrica(medida.metrica)}: </span>
        {descreverMedida(medida)}
      </span>
      <span className="shrink-0 font-mono tabular-nums text-slate-600 dark:text-slate-300">
        {formatarNumero(medida.valor)}
      </span>
    </div>
  );
}
