// A Matriz ("/execucoes/:id"): grade 3 Audiências × 3 Formatos, cada cartão com o
// veredito em palavras e o número ao lado, cor por destino, e um botão para ver as
// Âncoras da execução inteira.
import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { AUDIENCIAS, FORMATOS, obterAncoras, obterExecucao } from "../dados/cliente";
import { usarRequisicao } from "../ganchos/usarRequisicao";
import { Carregando, MensagemErro } from "../componentes/EstadoRequisicao";
import Ancoras from "../componentes/Ancoras";
import VereditoCartao from "../componentes/VereditoCartao";
import { corDestino, rotuloAudiencia, rotuloDestino, rotuloFormato } from "../texto/rotulos";

export default function Matriz() {
  const { id } = useParams<{ id: string }>();
  const identificador = id ?? "";
  const estadoExecucao = usarRequisicao(() => obterExecucao(identificador), [identificador]);
  const [mostrarAncoras, definirMostrarAncoras] = useState(false);
  const estadoAncoras = usarRequisicao(() => obterAncoras(identificador), [identificador]);

  if (estadoExecucao.situacao === "carregando") return <Carregando rotulo="Carregando execução…" />;
  if (estadoExecucao.situacao === "erro") return <MensagemErro erro={estadoExecucao.erro} />;

  const execucao = estadoExecucao.dados;
  const celulas = execucao.celulas ?? [];
  const porPosicao = new Map<string, (typeof celulas)[number]>();
  for (const historico of celulas) {
    porPosicao.set(`${historico.audiencia}:${historico.formato}`, historico);
  }

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold">{execucao.identificador}</h1>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            Ata {execucao.ata} · provedor {execucao.provedor_gerador}
          </p>
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => definirMostrarAncoras((atual) => !atual)}
            className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm font-medium hover:bg-slate-100 dark:border-slate-700 dark:hover:bg-slate-800"
          >
            {mostrarAncoras ? "Esconder Âncoras" : "Ver Âncoras da execução"}
          </button>
          <Link
            to={`/execucoes/${execucao.identificador}/filas`}
            className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm font-medium hover:bg-slate-100 dark:border-slate-700 dark:hover:bg-slate-800"
          >
            Filas
          </Link>
          <Link
            to={`/execucoes/${execucao.identificador}/pacotes`}
            className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm font-medium hover:bg-slate-100 dark:border-slate-700 dark:hover:bg-slate-800"
          >
            Pacotes
          </Link>
        </div>
      </div>

      {mostrarAncoras && (
        <section className="mb-6 rounded-xl border border-slate-200 p-4 dark:border-slate-800">
          <h2 className="mb-2 text-lg font-medium">Âncoras da execução</h2>
          {estadoAncoras.situacao === "carregando" && <Carregando />}
          {estadoAncoras.situacao === "erro" && <MensagemErro erro={estadoAncoras.erro} />}
          {estadoAncoras.situacao === "pronto" && (
            <div className="grid gap-4 md:grid-cols-2">
              <Ancoras ancoras={estadoAncoras.dados.numericas ?? []} />
              <ul className="space-y-3">
                {(estadoAncoras.dados.textuais ?? []).map((textual) => (
                  <li
                    key={textual.identificador}
                    className="rounded-lg border border-slate-200 p-3 text-sm dark:border-slate-800"
                  >
                    <p className="font-medium">{textual.afirmacao}</p>
                    <p className="mt-1 text-slate-500 dark:text-slate-400">
                      &ldquo;{textual.trecho}&rdquo;
                    </p>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </section>
      )}

      <div className="grid gap-4 md:grid-cols-3">
        {AUDIENCIAS.map((audiencia) => (
          <div key={audiencia} className="space-y-4">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
              {rotuloAudiencia(audiencia)}
            </h2>
            {FORMATOS.map((formato) => {
              const historico = porPosicao.get(`${audiencia}:${formato}`);
              const tentativas = historico?.tentativas ?? [];
              const ultimaTentativa = tentativas.at(-1);
              const laudo = ultimaTentativa?.laudo;
              return (
                <Link
                  key={formato}
                  to={`/execucoes/${execucao.identificador}/celulas/${audiencia}/${formato}`}
                  className={`block rounded-xl border p-3 shadow-sm transition hover:shadow ${
                    laudo
                      ? corDestino(laudo.destino)
                      : "border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900"
                  }`}
                >
                  <p className="font-medium">{rotuloFormato(formato)}</p>
                  {!historico && (
                    <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
                      sem Célula gerada
                    </p>
                  )}
                  {laudo && (
                    <>
                      <p className="mt-1 text-sm font-medium">{rotuloDestino(laudo.destino)}</p>
                      <div className="mt-2 space-y-1">
                        {laudo.medidas.map((medida) => (
                          <VereditoCartao key={medida.metrica} medida={medida} />
                        ))}
                      </div>
                    </>
                  )}
                </Link>
              );
            })}
          </div>
        ))}
      </div>
    </div>
  );
}
