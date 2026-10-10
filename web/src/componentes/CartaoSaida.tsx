// Uma Saída na lista: nome, fonte, modo, provedor, mini-Matriz e estado. O cartão inteiro é
// clicável por um link esticado no título; o menu "···" fica acima dele.
import { Link } from "react-router-dom";
import type { ExecucaoResumo } from "../dados/cliente";
import { contarPosicoes } from "../lib/matriz";
import { formatarDataCurta, pluralizar, rotuloModo, rotuloProvedor } from "../texto/rotulos";
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
  const detalhes = [`você aprovou ${contagem.aprovadasPorVoce}`];
  if (contagem.aguardando > 0) {
    detalhes.push(`${contagem.aguardando} ${contagem.aguardando === 1 ? "espera" : "esperam"}`);
  }
  if (contagem.bloqueadas > 0) {
    detalhes.push(
      `${contagem.bloqueadas} ${contagem.bloqueadas === 1 ? "bloqueada" : "bloqueadas"}`,
    );
  }
  const modo = rotuloModo(saida.modo);

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
          />
        </div>
      </div>
      <div className="flex flex-wrap gap-1.5">
        <Chip tom="forte">{saida.ata}</Chip>
        {modo && <Chip>{modo}</Chip>}
        <Chip>{rotuloProvedor(saida.provedor)}</Chip>
      </div>
      <div className="my-0.5 flex items-center gap-3.5">
        <MiniMatriz posicoes={saida.posicoes} />
        <p className="text-[11.5px] leading-relaxed text-suave">
          <b className="text-texto">{pluralizar(contagem.total, "Célula", "Células")}</b>
          <br />
          {detalhes.join(" · ")}
        </p>
      </div>
      <div className="mt-auto flex items-center gap-2 pt-1">
        {saida.status === "aguardando_revisao" ? (
          <Chip tom="alerta">Aguardando revisão</Chip>
        ) : (
          <Chip tom="ok">Concluída</Chip>
        )}
        <span className="ml-auto text-[11px] text-suave">
          {formatarDataCurta(saida.iniciada_em)}
        </span>
      </div>
    </article>
  );
}
