// A Célula ("/execucoes/:id/celulas/:audiencia/:formato"): o texto final por Formato, com
// as Âncoras ao lado, a Reprovação (se houver) e o histórico de tentativas (rodada 0, 1, 2).
import ReactMarkdown from "react-markdown";
import { useParams } from "react-router-dom";
import {
  obterAncorasDaCelula,
  obterCelula,
  type Audiencia,
  type Conteudo,
  type Formato,
} from "../dados/cliente";
import { usarRequisicao } from "../ganchos/usarRequisicao";
import { Carregando, MensagemErro } from "../componentes/EstadoRequisicao";
import Ancoras from "../componentes/Ancoras";
import Reprovacao from "../componentes/Reprovacao";
import VereditoCartao from "../componentes/VereditoCartao";
import { rotuloAudiencia, rotuloFormato } from "../texto/rotulos";

function ConteudoCelula({ conteudo }: { conteudo: Conteudo }) {
  if (conteudo.formato === "texto_analitico") {
    return (
      <article className="markdown rounded-xl border border-slate-200 p-4 dark:border-slate-800">
        <ReactMarkdown>{conteudo.texto ?? ""}</ReactMarkdown>
      </article>
    );
  }
  if (conteudo.formato === "carrossel") {
    return (
      <div className="grid gap-3 sm:grid-cols-2">
        {(conteudo.slides ?? []).map((slide, indice) => (
          <div
            key={indice}
            className="rounded-xl border border-slate-200 p-4 dark:border-slate-800"
          >
            <p className="text-xs font-semibold text-slate-500 dark:text-slate-400">
              Slide {indice + 1}
            </p>
            <p className="mt-1 font-medium">{slide.titulo}</p>
            <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">{slide.corpo}</p>
          </div>
        ))}
      </div>
    );
  }
  return (
    <ol className="space-y-3">
      {(conteudo.blocos ?? []).map((bloco, indice) => (
        <li key={indice} className="rounded-xl border border-slate-200 p-4 dark:border-slate-800">
          <p className="text-xs font-semibold text-slate-500 dark:text-slate-400">
            {bloco.inicio_s.toFixed(1)}s – {bloco.fim_s.toFixed(1)}s
          </p>
          <p className="mt-1">{bloco.fala}</p>
          {bloco.tela && (
            <p className="mt-1 text-sm italic text-slate-500 dark:text-slate-400">{bloco.tela}</p>
          )}
        </li>
      ))}
    </ol>
  );
}

export default function CelulaVista() {
  const parametros = useParams<{ id: string; audiencia: string; formato: string }>();
  const id = parametros.id ?? "";
  const audiencia = parametros.audiencia as Audiencia;
  const formato = parametros.formato as Formato;

  const estadoCelula = usarRequisicao(
    () => obterCelula(id, audiencia, formato),
    [id, audiencia, formato],
  );
  const estadoAncoras = usarRequisicao(
    () => obterAncorasDaCelula(id, audiencia, formato),
    [id, audiencia, formato],
  );

  if (estadoCelula.situacao === "carregando") return <Carregando rotulo="Carregando Célula…" />;
  if (estadoCelula.situacao === "erro") return <MensagemErro erro={estadoCelula.erro} />;

  const historico = estadoCelula.dados;
  const tentativas = historico.tentativas ?? [];
  const ultimaTentativa = tentativas.at(-1);

  return (
    <div>
      <h1 className="text-2xl font-semibold">
        {rotuloAudiencia(audiencia)} · {rotuloFormato(formato)}
      </h1>

      {tentativas.length === 0 && (
        <p className="mt-4 text-sm text-slate-500 dark:text-slate-400">
          Esta posição da Matriz não tem tentativa gravada.
        </p>
      )}

      <div className="mt-6 grid gap-6 lg:grid-cols-[2fr_1fr]">
        <div className="space-y-6">
          {ultimaTentativa && <ConteudoCelula conteudo={ultimaTentativa.celula.conteudo} />}
          {ultimaTentativa && <Reprovacao laudo={ultimaTentativa.laudo} />}
        </div>

        <aside className="space-y-3">
          <h2 className="text-lg font-medium">Âncoras ao lado</h2>
          {estadoAncoras.situacao === "carregando" && <Carregando />}
          {estadoAncoras.situacao === "erro" && <MensagemErro erro={estadoAncoras.erro} />}
          {estadoAncoras.situacao === "pronto" && <Ancoras ancoras={estadoAncoras.dados} />}
        </aside>
      </div>

      {tentativas.length > 0 && (
        <section className="mt-8">
          <h2 className="mb-3 text-lg font-medium">Histórico de tentativas</h2>
          <ol className="space-y-4">
            {tentativas.map((tentativa) => (
              <li
                key={tentativa.rodada}
                className="rounded-xl border border-slate-200 p-4 dark:border-slate-800"
              >
                <p className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
                  Rodada {tentativa.rodada}
                </p>
                <div className="space-y-1">
                  {tentativa.laudo.medidas.map((medida) => (
                    <VereditoCartao key={medida.metrica} medida={medida} />
                  ))}
                </div>
              </li>
            ))}
          </ol>
        </section>
      )}
    </div>
  );
}
