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
        destaque ? "border-suno/60 bg-suno/10 font-medium" : "border-linha bg-cartao"
      }`}
    >
      <span>
        <span className="text-suave">{rotuloMetrica(medida.metrica)}: </span>
        {descreverMedida(medida)}
      </span>
      <span className="shrink-0 font-mono tabular-nums text-suave">
        {formatarNumero(medida.valor)}
      </span>
    </div>
  );
}
