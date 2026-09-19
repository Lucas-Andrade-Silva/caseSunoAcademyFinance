// O Pacote de publicação ("/execucoes/:id/pacotes"): imagens do Carrossel, legenda,
// hashtags, e o vídeo se existir.
import { useParams } from "react-router-dom";
import { listarPacotes, urlDoArquivo } from "../dados/cliente";
import { usarRequisicao } from "../ganchos/usarRequisicao";
import { Carregando, MensagemErro } from "../componentes/EstadoRequisicao";
import { rotuloAudiencia, rotuloFormato } from "../texto/rotulos";

export default function Pacotes() {
  const { id } = useParams<{ id: string }>();
  const identificador = id ?? "";
  const estado = usarRequisicao(() => listarPacotes(identificador), [identificador]);

  if (estado.situacao === "carregando") return <Carregando rotulo="Carregando Pacotes…" />;
  if (estado.situacao === "erro") return <MensagemErro erro={estado.erro} />;

  if (estado.dados.length === 0) {
    return (
      <p className="text-sm text-slate-500 dark:text-slate-400">
        Nenhum Pacote de publicação ainda: só Célula aprovada gera um.
      </p>
    );
  }

  return (
    <div>
      <h1 className="mb-4 text-2xl font-semibold">Pacotes de publicação</h1>
      <div className="space-y-6">
        {estado.dados.map((pacote) => (
          <section
            key={`${pacote.audiencia}-${pacote.formato}`}
            className="rounded-xl border border-slate-200 p-4 dark:border-slate-800"
          >
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h2 className="text-lg font-medium">
                {rotuloAudiencia(pacote.audiencia)} · {rotuloFormato(pacote.formato)}
              </h2>
              <span
                className={`rounded-full px-2.5 py-1 text-xs font-medium ${
                  pacote.aprovado_por_humano
                    ? "bg-emerald-100 text-emerald-900 dark:bg-emerald-900 dark:text-emerald-100"
                    : "bg-amber-100 text-amber-900 dark:bg-amber-900 dark:text-amber-100"
                }`}
              >
                {pacote.aprovado_por_humano ? "aprovado (H5)" : "aguardando H5"}
              </span>
            </div>

            {pacote.imagens && pacote.imagens.length > 0 && (
              <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-3 md:grid-cols-6">
                {pacote.imagens.map((imagem) => (
                  <img
                    key={imagem.indice}
                    src={urlDoArquivo(pacote.execucao, imagem.caminho)}
                    alt={`Slide ${imagem.indice + 1}`}
                    className="rounded-md border border-slate-200 dark:border-slate-800"
                  />
                ))}
              </div>
            )}

            {pacote.video && (
              <video
                controls
                className="mt-3 max-h-96 rounded-md border border-slate-200 dark:border-slate-800"
                src={urlDoArquivo(pacote.execucao, pacote.video)}
              />
            )}

            <p className="mt-3 whitespace-pre-wrap text-sm">{pacote.legenda}</p>
            <div className="mt-2 flex flex-wrap gap-1">
              {(pacote.hashtags ?? []).map((hashtag) => (
                <span
                  key={hashtag}
                  className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-600 dark:bg-slate-800 dark:text-slate-300"
                >
                  {hashtag}
                </span>
              ))}
            </div>
          </section>
        ))}
      </div>
    </div>
  );
}
