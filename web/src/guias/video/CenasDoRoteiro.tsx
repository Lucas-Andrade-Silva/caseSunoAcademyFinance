// As cenas do roteiro, uma abaixo da outra: o intervalo, a fala, a rubrica da tela em cinza e, em
// letra pequena, o que a Direção de cena escolheu (cena e ícone). A edição fina (entrada, efeito)
// fica para o prompt, para a lista não poluir.
import type { BlocoFala } from "../../dados/cliente";
import { direcaoDaCena } from "./direcao";
import { formatarIntervalo } from "./tempo";

export default function CenasDoRoteiro({ blocos }: { blocos: readonly BlocoFala[] }) {
  return (
    <ol className="flex flex-col gap-2.5">
      {blocos.map((bloco, indice) => (
        <li
          key={indice}
          className="surge rounded-lg bg-superficie px-5 py-4"
          style={{ animationDelay: `${Math.min(indice, 8) * 40}ms` }}
        >
          <div className="flex items-baseline justify-between gap-4 text-[13px] text-etiqueta">
            <span className="shrink-0 tabular-nums">{formatarIntervalo(bloco.inicio_s, bloco.fim_s)}</span>
            <span className="min-w-0 truncate text-right">{direcaoDaCena(bloco)}</span>
          </div>
          <p className="mt-2.5 text-[16px] leading-snug">{bloco.fala}</p>
          {bloco.tela && <p className="mt-2 text-[14px] leading-snug text-etiqueta">{bloco.tela}</p>}
        </li>
      ))}
    </ol>
  );
}
