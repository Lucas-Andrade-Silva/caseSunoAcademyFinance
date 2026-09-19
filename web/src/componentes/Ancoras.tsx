// As Âncoras ao lado da Célula: chave, rótulo, valor citado e o trecho da Ata de origem.
import type { AncoraNumerica } from "../dados/cliente";

export default function Ancoras({ ancoras }: { ancoras: AncoraNumerica[] }) {
  if (ancoras.length === 0) {
    return <p className="text-sm text-slate-500 dark:text-slate-400">Nenhuma Âncora citada.</p>;
  }
  return (
    <ul className="space-y-3">
      {ancoras.map((ancora) => (
        <li
          key={ancora.chave}
          className="rounded-lg border border-slate-200 p-3 text-sm dark:border-slate-800"
        >
          <div className="flex items-baseline justify-between gap-2">
            <span className="font-medium">{ancora.rotulo}</span>
            <span className="font-mono text-slate-600 dark:text-slate-300">
              {ancora.valor_literal} {ancora.unidade}
            </span>
          </div>
          <p className="mt-1 text-slate-500 dark:text-slate-400">&ldquo;{ancora.trecho}&rdquo;</p>
        </li>
      ))}
    </ul>
  );
}
