// A barra fixa no rodapé da Célula aberta: Compliance, a decisão registrada, o nome do
// revisor e os botões Reprovar… (pede motivo) e Aprovar. Aprovar fica desabilitado, com o
// motivo à vista, quando o Laudo detectou Recomendação; o servidor também recusa (409).
import { useState, type FormEvent } from "react";
import type { DecisaoHumana } from "../dados/cliente";
import { lerRevisor } from "../lib/revisor";
import { formatarDataCurta } from "../texto/rotulos";
import Chip from "./Chip";

export interface PropriedadesDaBarra {
  bloqueada: boolean;
  decisao: DecisaoHumana | null;
  enviando: boolean;
  erro: string | null;
  onDecidir: (estado: "aprovada" | "reprovada", motivo: string | null, revisor: string) => void;
}

function resumoDaDecisao(decisao: DecisaoHumana): string {
  const quem = decisao.revisor ? ` · ${decisao.revisor}` : "";
  const motivo = decisao.motivo ? ` — ${decisao.motivo}` : "";
  const quando = decisao.em ? ` · ${formatarDataCurta(decisao.em)}` : "";
  const acao = decisao.estado === "aprovada" ? "Você aprovou" : "Você reprovou";
  return `${acao}${quem}${quando}${motivo}`;
}

export default function BarraDecisao({
  bloqueada,
  decisao,
  enviando,
  erro,
  onDecidir,
}: PropriedadesDaBarra) {
  const [reprovando, definirReprovando] = useState(false);
  const [motivo, definirMotivo] = useState("");
  const [revisor, definirRevisor] = useState(lerRevisor);

  function confirmarReprovacao(evento: FormEvent) {
    evento.preventDefault();
    if (motivo.trim() === "") return;
    onDecidir("reprovada", motivo.trim(), revisor.trim());
    definirReprovando(false);
    definirMotivo("");
  }

  return (
    <div className="sticky bottom-0 z-20 border-t border-linha bg-lateral px-5 py-2.5">
      {reprovando && (
        <form onSubmit={confirmarReprovacao} className="mb-2.5 flex flex-wrap items-start gap-2">
          <label htmlFor="motivo-da-reprovacao" className="sr-only">
            Motivo da reprovação
          </label>
          <textarea
            id="motivo-da-reprovacao"
            value={motivo}
            onChange={(evento) => definirMotivo(evento.target.value)}
            placeholder="Por que esta Célula não serve? O motivo fica registrado."
            rows={2}
            className="min-w-[280px] flex-1 rounded-lg border border-linha bg-cartao px-3 py-2 text-sm"
          />
          <button
            type="submit"
            disabled={enviando || motivo.trim() === ""}
            className="rounded-full bg-suno px-4 py-2 text-xs font-bold tracking-wide text-white disabled:cursor-not-allowed disabled:opacity-40"
          >
            CONFIRMAR REPROVAÇÃO
          </button>
          <button
            type="button"
            onClick={() => definirReprovando(false)}
            className="rounded-full border border-[#55555b] px-4 py-2 text-xs font-semibold"
          >
            Cancelar
          </button>
        </form>
      )}

      <div className="flex flex-wrap items-center gap-3">
        {bloqueada ? (
          <Chip tom="ruim">Bloqueada: o Laudo detectou Recomendação</Chip>
        ) : (
          <Chip tom="ok">Compliance ok · sem Recomendação</Chip>
        )}
        {decisao && <span className="text-xs text-suave">{resumoDaDecisao(decisao)}</span>}
        {erro && <span className="text-xs text-[#ffb3ad]">{erro}</span>}
        <div className="flex-1" />
        <label className="flex items-center gap-2 text-xs text-suave">
          Revisor
          <input
            value={revisor}
            onChange={(evento) => definirRevisor(evento.target.value)}
            placeholder="seu nome"
            className="w-36 rounded-lg border border-linha bg-cartao px-2.5 py-1 text-sm text-texto"
          />
        </label>
        <button
          type="button"
          disabled={enviando}
          onClick={() => definirReprovando(true)}
          className="rounded-full border border-[#55555b] px-[18px] py-2 text-xs font-semibold disabled:opacity-40"
        >
          Reprovar…
        </button>
        <button
          type="button"
          disabled={enviando || bloqueada}
          title={
            bloqueada
              ? "O Laudo detectou Recomendação: esta Célula não pode ser aprovada."
              : undefined
          }
          onClick={() => onDecidir("aprovada", null, revisor.trim())}
          className="rounded-full bg-suno px-[18px] py-2 text-xs font-bold tracking-wide text-white disabled:cursor-not-allowed disabled:opacity-40"
        >
          APROVAR
        </button>
      </div>
    </div>
  );
}
