// Lista de execuções ("/"): Ata, provedor, data, aprovadas/9 e pendências de cada uma.
import { Link } from "react-router-dom";
import { listarExecucoes } from "../dados/cliente";
import { usarRequisicao } from "../ganchos/usarRequisicao";
import { Carregando, MensagemErro } from "../componentes/EstadoRequisicao";

export default function Execucoes() {
  const estado = usarRequisicao(listarExecucoes, []);

  if (estado.situacao === "carregando") return <Carregando rotulo="Carregando execuções…" />;
  if (estado.situacao === "erro") return <MensagemErro erro={estado.erro} />;

  if (estado.dados.length === 0) {
    return (
      <p className="text-sm text-slate-500 dark:text-slate-400">
        Nenhuma execução encontrada em <code>data/execucoes/</code>.
      </p>
    );
  }

  return (
    <div>
      <h1 className="mb-4 text-2xl font-semibold">Execuções</h1>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {estado.dados.map((execucao) => (
          <Link
            key={execucao.identificador}
            to={`/execucoes/${execucao.identificador}`}
            className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm transition hover:border-indigo-300 hover:shadow dark:border-slate-800 dark:bg-slate-900"
          >
            <p className="font-medium">{execucao.identificador}</p>
            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">Ata: {execucao.ata}</p>
            <p className="text-sm text-slate-500 dark:text-slate-400">
              Provedor: {execucao.provedor}
            </p>
            <p className="text-sm text-slate-500 dark:text-slate-400">
              {new Date(execucao.iniciada_em).toLocaleString("pt-BR")}
            </p>
            <div className="mt-3 flex flex-wrap items-center gap-2 text-sm">
              <span className="rounded-full bg-emerald-100 px-2.5 py-1 font-medium text-emerald-900 dark:bg-emerald-900 dark:text-emerald-100">
                {execucao.aprovadas}/{execucao.total_celulas} aprovadas
              </span>
              {execucao.pendencias > 0 && (
                <span className="rounded-full bg-amber-100 px-2.5 py-1 font-medium text-amber-900 dark:bg-amber-900 dark:text-amber-100">
                  {execucao.pendencias} pendência(s)
                </span>
              )}
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
