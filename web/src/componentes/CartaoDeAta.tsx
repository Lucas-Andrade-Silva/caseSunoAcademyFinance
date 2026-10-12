// Um cartão de Ata num trilho da guia Fontes: data, título, resumo de duas linhas, número de
// Âncoras e a bolinha de seleção (spec do front, seção 4.1).
import { Link } from "react-router-dom";
import type { ResumoDaAta } from "../dados/cliente";
import { dataDoDia, seloDaAta } from "../lib/fontes";
import Chip from "./Chip";

export default function CartaoDeAta({
  ata,
  selecionada,
  desligada,
  onAlternar,
}: {
  ata: ResumoDaAta;
  selecionada: boolean;
  /** A Origem está desligada: o cartão aparece, mas não entra na seleção. */
  desligada: boolean;
  onAlternar: () => void;
}) {
  const selo = seloDaAta(ata.categoria);
  return (
    <article
      className={`relative flex w-[215px] shrink-0 flex-col gap-1.5 rounded-[13px] bg-cartao p-3 transition ${
        desligada ? "opacity-55" : ""
      } ${selecionada ? "ring-1 ring-suno" : ""}`}
    >
      <span className="text-[10.5px] font-bold uppercase tracking-wide text-suno">
        {dataDoDia(ata.data_referencia)}
      </span>
      <strong className="pr-6 text-[12.5px] leading-snug">
        <Link
          to={`/fontes/${ata.identificador}`}
          title="Ler a Ata"
          className="after:absolute after:inset-0 hover:underline"
        >
          {ata.titulo}
        </Link>
      </strong>
      <p className="line-clamp-2 text-[11.5px] text-suave">{ata.resumo}</p>
      <div className="mt-0.5 flex flex-wrap items-center gap-1.5">
        <Chip>{ata.total_ancoras} Âncoras</Chip>
        {selo && <Chip tom="alerta">{selo}</Chip>}
        {!ata.extracao_completa && (
          <span title="Sem uma data e um número com unidade no texto, a geração reprovaria toda Célula por falha de extração.">
            <Chip tom="ruim">sem número</Chip>
          </span>
        )}
      </div>
      <button
        type="button"
        role="checkbox"
        aria-checked={selecionada}
        aria-label={`Selecionar ${ata.titulo}`}
        disabled={desligada}
        onClick={onAlternar}
        className={`absolute right-[11px] top-[11px] h-4 w-4 rounded-full border-[1.5px] disabled:cursor-not-allowed ${
          selecionada ? "border-suno bg-suno" : "border-[#4a4a50] hover:border-texto"
        }`}
      />
    </article>
  );
}
