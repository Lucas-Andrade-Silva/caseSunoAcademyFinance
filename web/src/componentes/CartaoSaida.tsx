// Uma Saída na lista: nome, fonte, modo, provedor, mini-Matriz e estado. O cartão inteiro é
// clicável por um link esticado no título; o menu "···" fica acima dele.
import { Link } from "react-router-dom";
import type { ExecucaoResumo } from "../dados/cliente";
import { seloDaAta } from "../lib/fontes";
import { contarPosicoes, progressoDoAndamento } from "../lib/matriz";
import {
  formatarDataCurta,
  pluralizar,
  rotuloDasAtas,
  rotuloModo,
  rotuloProvedor,
  rotuloStatus,
} from "../texto/rotulos";
import Chip from "./Chip";
import MenuDoCartao from "./MenuDoCartao";
import MiniMatriz from "./MiniMatriz";

export default function CartaoSaida({
  saida,
  onAlterada,
}: {
  saida: ExecucaoResumo;
  onAlterada: () => void;
}) {
  const contagem = contarPosicoes(saida.posicoes);
  // Saída sem execucao.json: ainda gerando, na fila, interrompida ou que falhou. Não há o que
  // renomear nem exportar, e o cartão mostra o andamento no lugar das decisões.
  const semExecucao = ["na_fila", "gerando", "interrompida", "falhou"].includes(saida.status);
  const detalhes = semExecucao ? [] : [`você aprovou ${contagem.aprovadasPorVoce}`];
  if (semExecucao) {
    const progresso = progressoDoAndamento(
      saida.posicoes.map((p) => ({ etapa: p.etapa ?? "aguardando" })),
    );
    detalhes.push(`${progresso.terminadas} de ${progresso.total} prontas`);
  }
  if (contagem.aguardando > 0) {
    detalhes.push(`${contagem.aguardando} ${contagem.aguardando === 1 ? "espera" : "esperam"}`);
  }
  if (contagem.bloqueadas > 0) {
    detalhes.push(
      `${contagem.bloqueadas} ${contagem.bloqueadas === 1 ? "bloqueada" : "bloqueadas"}`,
    );
  }
  const modo = rotuloModo(saida.modo);
  const status = rotuloStatus(saida.status);
  const selo = seloDaAta(saida.categoria ?? "copom");

  return (
    <article className="relative flex min-w-0 flex-col gap-2 rounded-2xl border border-transparent bg-cartao p-3.5 transition hover:border-suno/45">
      <div className="flex items-start gap-2">
        <h2 className="text-[13.5px] font-bold leading-snug">
          <Link
            to={`/saidas/${encodeURIComponent(saida.identificador)}`}
            className="after:absolute after:inset-0 after:content-['']"
          >
            {saida.nome}
          </Link>
        </h2>
        <div className="ml-auto">
          <MenuDoCartao
            identificador={saida.identificador}
            nome={saida.nome}
            onRenomeada={onAlterada}
            onExcluida={onAlterada}
            completa={!semExecucao}
          />
        </div>
      </div>
      <div className="flex flex-wrap gap-1.5">
        <Chip tom="forte">{rotuloDasAtas(saida.modo, saida.ata, saida.atas)}</Chip>
        {modo && <Chip>{modo}</Chip>}
        <Chip>{rotuloProvedor(saida.provedor)}</Chip>
        {selo && <Chip tom="alerta">{selo}</Chip>}
      </div>
      <div className="my-0.5 flex items-center gap-3.5">
        <MiniMatriz posicoes={saida.posicoes} status={saida.status} />
        <p className="text-[11.5px] leading-relaxed text-suave">
          <b className="text-texto">{pluralizar(contagem.total, "Célula", "Células")}</b>
          <br />
          {detalhes.join(" · ")}
        </p>
      </div>
      <div className="mt-auto flex items-center gap-2 pt-1">
        <Chip tom={status.tom}>{status.texto}</Chip>
        {saida.erro && (
          <span className="truncate text-[11px] text-[#ffb3ad]" title={saida.erro}>
            {saida.erro}
          </span>
        )}
        <span className="ml-auto text-[11px] text-suave">
          {formatarDataCurta(saida.iniciada_em)}
        </span>
      </div>
    </article>
  );
}
