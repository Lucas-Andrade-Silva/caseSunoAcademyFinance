// A Célula aberta ("/saidas/:id/celulas/:audiencia/:formato"): conteúdo à esquerda; Laudo e
// Âncoras à direita, sempre visíveis; Pacote embaixo; barra Aprovar/Reprovar fixa no rodapé
// (spec do front, seção 4.5, opção B).
import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  listarPacotes,
  obterAncorasDaCelula,
  obterExecucao,
  registrarDecisao,
  type Audiencia,
  type DecisaoHumana,
  type Formato,
} from "../dados/cliente";
import { usarRequisicao } from "../ganchos/usarRequisicao";
import { Carregando, MensagemErro } from "../componentes/EstadoRequisicao";
import BarraDecisao from "../componentes/BarraDecisao";
import Chip from "../componentes/Chip";
import ConteudoCelula from "../componentes/ConteudoCelula";
import SecaoAncoras from "../componentes/SecaoAncoras";
import SecaoLaudo from "../componentes/SecaoLaudo";
import SecaoPacote from "../componentes/SecaoPacote";
import Reprovacao from "../componentes/Reprovacao";
import VereditoCartao from "../componentes/VereditoCartao";
import { celulaBloqueada, chaveDaPosicao, vizinhas } from "../lib/matriz";
import { guardarRevisor } from "../lib/revisor";
import { rotuloAudiencia, rotuloFormato } from "../texto/rotulos";

export default function CelulaAberta() {
  const parametros = useParams<{ id: string; audiencia: string; formato: string }>();
  const id = parametros.id ?? "";
  const audiencia = parametros.audiencia as Audiencia;
  const formato = parametros.formato as Formato;

  const [recarga, recarregar] = useState(0);
  const [enviando, definirEnviando] = useState(false);
  const [erroDaDecisao, definirErroDaDecisao] = useState<string | null>(null);
  const [registrada, definirRegistrada] = useState<{
    chave: string;
    decisao: DecisaoHumana;
  } | null>(null);

  const estadoExecucao = usarRequisicao(() => obterExecucao(id), [id]);
  const estadoAncoras = usarRequisicao(
    () => obterAncorasDaCelula(id, audiencia, formato),
    [id, audiencia, formato],
  );
  const estadoPacotes = usarRequisicao(() => listarPacotes(id), [id, recarga]);

  if (estadoExecucao.situacao === "carregando") return <Carregando rotulo="Carregando Célula…" />;
  if (estadoExecucao.situacao === "erro") return <MensagemErro erro={estadoExecucao.erro} />;

  const execucao = estadoExecucao.dados;
  const chave = `${id}:${chaveDaPosicao(audiencia, formato)}`;
  const historico = (execucao.celulas ?? []).find(
    (h) => h.audiencia === audiencia && h.formato === formato,
  );
  const tentativas = historico?.tentativas ?? [];
  const ultima = tentativas.at(-1);
  const bloqueada = celulaBloqueada(ultima?.laudo);
  const decisaoLocal = registrada?.chave === chave ? registrada.decisao : null;
  const decisao =
    decisaoLocal ??
    (execucao.decisoes ?? []).find((d) => d.audiencia === audiencia && d.formato === formato) ??
    null;
  const pedidas = (execucao.celulas ?? []).map((h) => ({
    audiencia: h.audiencia,
    formato: h.formato,
  }));
  const { anterior, proxima } = vizinhas(pedidas, audiencia, formato);
  const pacote =
    estadoPacotes.situacao === "pronto"
      ? (estadoPacotes.dados.find((p) => p.audiencia === audiencia && p.formato === formato) ??
        null)
      : null;

  function decidir(estado: "aprovada" | "reprovada", motivo: string | null, revisor: string) {
    definirEnviando(true);
    definirErroDaDecisao(null);
    guardarRevisor(revisor);
    registrarDecisao(id, audiencia, formato, {
      estado,
      motivo,
      revisor: revisor === "" ? null : revisor,
    })
      .then((nova) => definirRegistrada({ chave, decisao: nova }))
      .catch((falha: unknown) => {
        definirErroDaDecisao(falha instanceof Error ? falha.message : String(falha));
      })
      .finally(() => definirEnviando(false));
  }

  function linkDaVizinha(destino: { audiencia: string; formato: string } | null, rotulo: string) {
    if (destino === null) {
      return <span className="text-[#5d5d63]">{rotulo}</span>;
    }
    return (
      <Link
        to={`/saidas/${encodeURIComponent(id)}/celulas/${destino.audiencia}/${destino.formato}`}
        className="hover:text-texto"
      >
        {rotulo}
      </Link>
    );
  }

  return (
    <div className="flex min-h-screen flex-col">
      <header className="px-5 pb-2.5 pt-3">
        <nav className="mb-1 text-[11.5px] text-suave">
          <Link to="/saidas" className="hover:text-texto">
            Saídas
          </Link>{" "}
          ›{" "}
          <Link to={`/saidas/${encodeURIComponent(id)}`} className="hover:text-texto">
            {execucao.nome}
          </Link>{" "}
          › {rotuloAudiencia(audiencia)} · {rotuloFormato(formato)}
        </nav>
        <div className="flex flex-wrap items-center gap-2.5">
          <h1 className="text-[17px] font-bold">
            {rotuloAudiencia(audiencia)} · {rotuloFormato(formato)}
          </h1>
          {ultima && (
            <Chip tom={historico?.destino_final === "aprovado" ? "ok" : "alerta"}>
              {historico?.destino_final === "aprovado" ? "Laudo: aprovada" : "Laudo: não aprovada"}
            </Chip>
          )}
          {tentativas.length > 0 && (
            <Chip>
              {tentativas.length} {tentativas.length === 1 ? "rodada" : "rodadas"}
            </Chip>
          )}
          <div className="flex-1" />
          <span className="flex gap-3 text-xs text-suave">
            {linkDaVizinha(anterior, "‹ Célula anterior")}
            {linkDaVizinha(proxima, "próxima ›")}
          </span>
        </div>
      </header>

      {tentativas.length === 0 && (
        <p className="px-5 text-sm text-suave">
          Esta posição da Matriz não tem Célula gerada
          {historico?.falha ? `: ${historico.falha}` : "."}
        </p>
      )}

      {ultima && (
        <div className="grid flex-1 gap-4 px-5 pb-4 lg:grid-cols-[1.25fr_1fr]">
          <div className="min-w-0 space-y-3">
            <section className="rounded-2xl bg-cartao p-3.5">
              <h2 className="mb-2 text-[12.5px] font-bold">Conteúdo</h2>
              <ConteudoCelula conteudo={ultima.celula.conteudo} />
            </section>
            <Reprovacao laudo={ultima.laudo} destinoFinal={historico?.destino_final} />
            <SecaoPacote
              identificador={id}
              audiencia={audiencia}
              formato={formato}
              pacote={pacote}
              onAtualizado={() => recarregar((atual) => atual + 1)}
            />
            {tentativas.length > 1 && (
              <details className="rounded-2xl bg-cartao p-3.5">
                <summary className="cursor-pointer text-[12.5px] font-bold">
                  Histórico de tentativas ({tentativas.length})
                </summary>
                <ol className="mt-3 space-y-3">
                  {tentativas.map((tentativa) => (
                    <li key={tentativa.rodada} className="rounded-xl border border-linha p-3">
                      <p className="mb-2 text-xs font-bold uppercase tracking-wide text-suave">
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
              </details>
            )}
          </div>

          <div className="min-w-0 space-y-3">
            <SecaoLaudo
              laudo={ultima.laudo}
              destinoFinal={historico?.destino_final ?? ultima.laudo.destino}
            />
            {estadoAncoras.situacao === "carregando" && <Carregando />}
            {estadoAncoras.situacao === "erro" && <MensagemErro erro={estadoAncoras.erro} />}
            {estadoAncoras.situacao === "pronto" && <SecaoAncoras ancoras={estadoAncoras.dados} />}
          </div>
        </div>
      )}

      {ultima && (
        <BarraDecisao
          bloqueada={bloqueada}
          decisao={decisao}
          enviando={enviando}
          erro={erroDaDecisao}
          onDecidir={decidir}
        />
      )}
    </div>
  );
}
