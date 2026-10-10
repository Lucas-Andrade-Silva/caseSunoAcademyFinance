// As Âncoras ao lado da Célula: chave, rótulo, valor citado e o trecho da Ata de origem.
import type { AncoraNumerica } from "../dados/cliente";

export default function Ancoras({ ancoras }: { ancoras: AncoraNumerica[] }) {
  if (ancoras.length === 0) {
    return <p className="text-sm text-suave">Nenhuma Âncora citada.</p>;
  }
  return (
    <ul>
      {ancoras.map((ancora) => (
        <li key={ancora.chave} className="border-t border-linha py-2 text-[12px] first:border-t-0">
          <div className="flex items-baseline justify-between gap-2">
            <span className="font-semibold">{ancora.rotulo}</span>
            <span className="whitespace-nowrap font-mono font-bold">
              {ancora.valor_literal} {ancora.unidade}
            </span>
          </div>
          <p className="mt-0.5 text-suave">&ldquo;{ancora.trecho}&rdquo;</p>
        </li>
      ))}
    </ul>
  );
}
