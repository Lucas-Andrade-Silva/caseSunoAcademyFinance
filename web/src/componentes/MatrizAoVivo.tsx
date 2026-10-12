// A Matriz ao vivo: barra de progresso e uma Célula por posição pedida, atualizada por polling
// enquanto a Saída é gerada em segundo plano (spec do front, seção 4.2, passo 3). Dá para sair da
// tela: a geração continua no servidor.
import { Fragment } from "react";
import { Link } from "react-router-dom";
import { AUDIENCIAS, FORMATOS, type Andamento, type AndamentoDaCelula } from "../dados/cliente";
import { geracaoTerminou, usarAndamento } from "../ganchos/usarAndamento";
import { chaveDaPosicao, progressoDoAndamento } from "../lib/matriz";
import {
  rotuloAudiencia,
  rotuloEtapa,
  rotuloFase,
  rotuloFormato,
  pluralizar,
} from "../texto/rotulos";
import { Carregando, MensagemErro } from "./EstadoRequisicao";

const CLASSE_DA_ETAPA: Record<string, string> = {
  aguardando: "border-dashed border-[#3b3b40] text-suave",
  gerando: "border-suno bg-suno/15 text-texto",
  corrigindo: "border-suno bg-suno/15 text-texto",
  aprovada: "border-ok/50 bg-ok/10 text-texto",
  revisao_humana: "border-alerta/55 bg-alerta/10 text-texto",
};
const CLASSE_DE_QUEM_PAROU = "border-suno/45 bg-suno/5 text-suave";
const ETAPAS_EM_CURSO = ["aguardando", "gerando", "corrigindo"];

function CelulaAoVivo({ celula, parou }: { celula: AndamentoDaCelula; parou: boolean }) {
  const naoTerminou = ETAPAS_EM_CURSO.includes(celula.etapa);
  const { titulo, detalhe } = rotuloEtapa(celula.etapa, celula.rodada, parou && naoTerminou);
  const classe =
    parou && naoTerminou ? CLASSE_DE_QUEM_PAROU : (CLASSE_DA_ETAPA[celula.etapa] ?? "");
  const pulsando = !parou && (celula.etapa === "gerando" || celula.etapa === "corrigindo");
  return (
    <div
      className={`flex min-h-[58px] flex-col items-center justify-center gap-0.5 rounded-xl border-[1.5px] px-2 text-center text-[11px] font-semibold ${classe} ${
        pulsando ? "animate-pulse" : ""
      }`}
    >
      {titulo}
      {detalhe && <small className="text-[10.5px] font-normal text-suave">{detalhe}</small>}
    </div>
  );
}

function resumoDoAndamento(celulas: AndamentoDaCelula[]): string {
  const progresso = progressoDoAndamento(celulas);
  const aprovadas = celulas.filter((c) => c.etapa === "aprovada").length;
  const emRevisao = celulas.filter((c) => c.etapa === "revisao_humana").length;
  const corrigindo = celulas.filter((c) => c.etapa === "corrigindo").length;
  const partes = [`${progresso.terminadas} de ${progresso.total} concluídas`];
  const detalhes: string[] = [];
  if (aprovadas > 0) detalhes.push(pluralizar(aprovadas, "aprovada", "aprovadas"));
  if (emRevisao > 0) detalhes.push(`${emRevisao} foi para a revisão humana`);
  if (detalhes.length > 0) partes[0] += ` (${detalhes.join(", ")})`;
  if (corrigindo > 0) partes.push(`${corrigindo} em correção`);
  return partes.join(" · ");
}

export default function MatrizAoVivo({
  identificador,
  aoConcluir,
  linkDaSaida = true,
}: {
  identificador: string;
  aoConcluir?: (andamento: Andamento) => void;
  /** Mostra "Abrir Saída" quando termina. Desligado na própria página da Saída. */
  linkDaSaida?: boolean;
}) {
  const { andamento, erro } = usarAndamento(identificador, aoConcluir);

  if (andamento === null) {
    return erro ? <MensagemErro erro={erro} /> : <Carregando rotulo="Consultando o andamento…" />;
  }

  const celulas = andamento.celulas ?? [];
  const progresso = progressoDoAndamento(celulas);
  const parou = andamento.estado === "interrompida" || andamento.estado === "falhou";
  const terminou = geracaoTerminou(andamento);
  const porPosicao = new Map(
    celulas.map((celula) => [chaveDaPosicao(celula.audiencia, celula.formato), celula]),
  );

  return (
    <div>
      <div
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={progresso.percentual}
        className="relative my-1.5 h-2 overflow-hidden rounded bg-cartao-2"
      >
        <div
          className={`absolute inset-y-0 left-0 rounded transition-all duration-500 ${
            parou ? "bg-[#5a5a60]" : "bg-suno"
          }`}
          style={{ width: `${progresso.percentual}%` }}
        />
      </div>
      <p className="mb-3 text-sm text-suave">
        <b className="text-texto">{resumoDoAndamento(celulas)}</b>
        {!terminou && <> · {rotuloFase(andamento.fase)} Pode sair da tela, a geração continua.</>}
      </p>

      {andamento.estado === "concluida" && (
        <p className="mb-3 rounded-xl border border-ok/40 bg-ok/10 px-3 py-2 text-sm">
          Geração concluída.{" "}
          {linkDaSaida && (
            <Link
              to={`/saidas/${encodeURIComponent(andamento.identificador)}`}
              className="font-semibold text-suno hover:underline"
            >
              Abrir a Saída
            </Link>
          )}
        </p>
      )}
      {parou && (
        <p className="mb-3 rounded-xl border border-suno/45 bg-suno/10 px-3 py-2 text-sm text-[#ffb3ad]">
          {andamento.estado === "interrompida" ? "Geração interrompida" : "A geração falhou"}
          {andamento.erro ? `: ${andamento.erro}` : "."}
        </p>
      )}

      <div className="grid grid-cols-[78px_repeat(3,minmax(0,1fr))] sm:grid-cols-[84px_repeat(3,minmax(0,1fr))] gap-2">
        <div />
        {FORMATOS.map((formato) => (
          <div
            key={formato}
            className="rounded-lg bg-cartao px-1 py-1 text-center text-[10.5px] font-bold uppercase tracking-wider"
          >
            {rotuloFormato(formato)}
          </div>
        ))}
        {AUDIENCIAS.map((audiencia) => (
          <Fragment key={audiencia}>
            <div className="flex items-center rounded-lg bg-cartao px-2 text-xs font-bold">
              {rotuloAudiencia(audiencia)}
            </div>
            {FORMATOS.map((formato) => {
              const celula = porPosicao.get(chaveDaPosicao(audiencia, formato));
              return celula ? (
                <CelulaAoVivo key={formato} celula={celula} parou={parou} />
              ) : (
                <div
                  key={formato}
                  className="flex min-h-[58px] items-center justify-center rounded-xl border-[1.5px] border-dashed border-[#3b3b40] text-[11px] text-[#5d5d63]"
                >
                  não pedida
                </div>
              );
            })}
          </Fragment>
        ))}
      </div>
    </div>
  );
}
