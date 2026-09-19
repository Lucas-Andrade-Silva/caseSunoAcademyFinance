// As três filas humanas ("/execucoes/:id/filas"): H3 desempate, H4 revisão (com decisão),
// H5 aprovação do Pacote (com a lista da conferência visual e a folha de contato).
import type { ReactNode } from "react";
import { useState } from "react";
import { useParams } from "react-router-dom";
import {
  aprovarPacote,
  listarPacotes,
  obterFilas,
  resolverH4,
  urlDoArquivo,
  type PacotePublicacao,
  type Pendencia,
} from "../dados/cliente";
import { usarRequisicao } from "../ganchos/usarRequisicao";
import { Carregando, MensagemErro } from "../componentes/EstadoRequisicao";
import { rotuloAudiencia, rotuloFormato } from "../texto/rotulos";

function ColunaFila({ titulo, children }: { titulo: string; children: ReactNode }) {
  return (
    <section className="rounded-xl border border-slate-200 p-4 dark:border-slate-800">
      <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
        {titulo}
      </h2>
      <div className="space-y-3">{children}</div>
    </section>
  );
}

function VazioFila() {
  return <p className="text-sm text-slate-500 dark:text-slate-400">Vazia.</p>;
}

function CartaoPendencia({ pendencia }: { pendencia: Pendencia }) {
  return (
    <div className="rounded-lg border border-slate-200 p-3 text-sm dark:border-slate-800">
      <p className="font-medium">
        {rotuloAudiencia(pendencia.audiencia)} · {rotuloFormato(pendencia.formato)}
      </p>
      <p className="mt-1 text-slate-600 dark:text-slate-300">{pendencia.motivo}</p>
      {pendencia.resolvida && (
        <p className="mt-1 text-emerald-700 dark:text-emerald-300">
          Resolvida: {pendencia.decisao ?? "—"}
        </p>
      )}
    </div>
  );
}

function CartaoH4({
  pendencia,
  onResolvida,
}: {
  pendencia: Pendencia;
  onResolvida: (decisao: string) => void;
}) {
  const [decisao, definirDecisao] = useState(pendencia.decisao ?? "");
  const [enviando, definirEnviando] = useState(false);

  if (pendencia.resolvida) {
    return (
      <div className="rounded-lg border border-slate-200 p-3 text-sm dark:border-slate-800">
        <p className="font-medium">
          {rotuloAudiencia(pendencia.audiencia)} · {rotuloFormato(pendencia.formato)}
        </p>
        <p className="mt-1 text-slate-600 dark:text-slate-300">{pendencia.motivo}</p>
        <p className="mt-1 text-emerald-700 dark:text-emerald-300">
          Resolvida: {pendencia.decisao ?? "—"}
        </p>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-slate-200 p-3 text-sm dark:border-slate-800">
      <p className="font-medium">
        {rotuloAudiencia(pendencia.audiencia)} · {rotuloFormato(pendencia.formato)}
      </p>
      <p className="mt-1 text-slate-600 dark:text-slate-300">{pendencia.motivo}</p>
      <form
        className="mt-2 flex gap-2"
        onSubmit={(evento) => {
          evento.preventDefault();
          if (!decisao.trim() || enviando) return;
          definirEnviando(true);
          onResolvida(decisao);
        }}
      >
        <input
          value={decisao}
          onChange={(evento) => definirDecisao(evento.target.value)}
          placeholder="reescrever à mão · ajustar Limiar · descartar"
          className="flex-1 rounded-md border border-slate-300 px-2 py-1 text-sm dark:border-slate-700 dark:bg-slate-900"
        />
        <button
          type="submit"
          disabled={enviando}
          className="rounded-md bg-indigo-600 px-3 py-1 text-sm font-medium text-white hover:bg-indigo-500 disabled:opacity-50"
        >
          Resolver
        </button>
      </form>
    </div>
  );
}

function CartaoH5({
  pacote,
  onAprovado,
}: {
  pacote: PacotePublicacao;
  onAprovado: () => void;
}) {
  const [enviando, definirEnviando] = useState(false);
  const defeitos = (pacote.conferencia?.medicoes ?? []).filter(
    (medicao) => medicao.defeito !== null && medicao.defeito !== undefined,
  );

  return (
    <div className="rounded-lg border border-slate-200 p-3 text-sm dark:border-slate-800">
      <p className="font-medium">
        {rotuloAudiencia(pacote.audiencia)} · {rotuloFormato(pacote.formato)}
      </p>
      {pacote.folha_de_contato && (
        <img
          src={urlDoArquivo(pacote.execucao, pacote.folha_de_contato)}
          alt="Folha de contato do Carrossel"
          className="mt-2 rounded-md border border-slate-200 dark:border-slate-800"
        />
      )}
      {defeitos.length > 0 ? (
        <ul className="mt-2 list-inside list-disc text-amber-700 dark:text-amber-300">
          {defeitos.map((medicao, indice) => (
            <li key={indice}>
              {medicao.artefato}: {medicao.defeito} {medicao.detalhe && `— ${medicao.detalhe}`}
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-2 text-slate-500 dark:text-slate-400">
          Nenhum defeito de render encontrado.
        </p>
      )}
      {pacote.conferencia?.juiz_visao && (
        <p className="mt-2 text-slate-600 dark:text-slate-300">
          Juiz de visão:{" "}
          {pacote.conferencia.juiz_visao.parece_quebrado ? "parece quebrado" : "sem suspeita"}
        </p>
      )}
      <button
        type="button"
        disabled={enviando}
        onClick={() => {
          definirEnviando(true);
          onAprovado();
        }}
        className="mt-3 rounded-md bg-emerald-600 px-3 py-1 text-sm font-medium text-white hover:bg-emerald-500 disabled:opacity-50"
      >
        Aprovar Pacote
      </button>
    </div>
  );
}

export default function Filas() {
  const { id } = useParams<{ id: string }>();
  const identificador = id ?? "";
  const [versao, forcarNovaLeitura] = useState(0);
  const estadoFilas = usarRequisicao(
    () => obterFilas(identificador),
    [identificador, versao],
  );
  const estadoPacotes = usarRequisicao(
    () => listarPacotes(identificador),
    [identificador, versao],
  );

  if (estadoFilas.situacao === "carregando" || estadoPacotes.situacao === "carregando") {
    return <Carregando rotulo="Carregando filas…" />;
  }
  if (estadoFilas.situacao === "erro") return <MensagemErro erro={estadoFilas.erro} />;
  if (estadoPacotes.situacao === "erro") return <MensagemErro erro={estadoPacotes.erro} />;

  const filas = estadoFilas.dados;
  const pacotesPendentes = estadoPacotes.dados.filter((pacote) => !pacote.aprovado_por_humano);

  return (
    <div>
      <h1 className="mb-4 text-2xl font-semibold">Filas humanas</h1>
      <div className="grid gap-4 lg:grid-cols-3">
        <ColunaFila titulo="H3 · Desempate">
          {filas.h3_desempate.length === 0 && <VazioFila />}
          {filas.h3_desempate.map((pendencia, indice) => (
            <CartaoPendencia key={indice} pendencia={pendencia} />
          ))}
        </ColunaFila>

        <ColunaFila titulo="H4 · Revisão">
          {filas.h4_revisao.length === 0 && <VazioFila />}
          {filas.h4_revisao.map((pendencia, indice) => (
            <CartaoH4
              key={indice}
              pendencia={pendencia}
              onResolvida={(decisao) => {
                resolverH4(identificador, indice, decisao).then(() => {
                  forcarNovaLeitura((atual) => atual + 1);
                });
              }}
            />
          ))}
        </ColunaFila>

        <ColunaFila titulo="H5 · Aprovação do Pacote">
          {pacotesPendentes.length === 0 && <VazioFila />}
          {pacotesPendentes.map((pacote) => (
            <CartaoH5
              key={`${pacote.audiencia}-${pacote.formato}`}
              pacote={pacote}
              onAprovado={() => {
                aprovarPacote(identificador, pacote.audiencia, pacote.formato).then(() => {
                  forcarNovaLeitura((atual) => atual + 1);
                });
              }}
            />
          ))}
        </ColunaFila>
      </div>
    </div>
  );
}
