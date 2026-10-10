// A Saída aberta ("/saidas/:id"): nome editável, exportar, o resumo de estados e a Matriz
// 3×3 (Audiências nas linhas, Formatos nas colunas). Células não pedidas ficam tracejadas
// (spec do front, seção 4.4, opção A).
import { Fragment, useState, type FormEvent } from "react";
import { Link, useParams } from "react-router-dom";
import { AUDIENCIAS, FORMATOS, obterResumo, renomearExecucao } from "../dados/cliente";
import { usarRequisicao } from "../ganchos/usarRequisicao";
import { Carregando, MensagemErro } from "../componentes/EstadoRequisicao";
import CelulaDaMatriz from "../componentes/CelulaDaMatriz";
import Chip from "../componentes/Chip";
import LinksDeExportacao from "../componentes/LinksDeExportacao";
import { chaveDaPosicao, contarPosicoes } from "../lib/matriz";
import {
  formatarDataCurta,
  pluralizar,
  rotuloAudiencia,
  rotuloFormato,
  rotuloModo,
  rotuloProvedor,
} from "../texto/rotulos";

export default function SaidaAberta() {
  const { id } = useParams<{ id: string }>();
  const identificador = id ?? "";
  const [recarga, recarregar] = useState(0);
  const estado = usarRequisicao(() => obterResumo(identificador), [identificador, recarga]);
  const [editando, definirEditando] = useState(false);
  const [novoNome, definirNovoNome] = useState("");
  const [enviando, definirEnviando] = useState(false);
  const [erroDoNome, definirErroDoNome] = useState<string | null>(null);

  if (estado.situacao === "carregando") return <Carregando rotulo="Carregando Saída…" />;
  if (estado.situacao === "erro") return <MensagemErro erro={estado.erro} />;

  const resumo = estado.dados;
  const contagem = contarPosicoes(resumo.posicoes);
  const porPosicao = new Map(
    resumo.posicoes.map((p) => [chaveDaPosicao(p.audiencia, p.formato), p]),
  );
  const modo = rotuloModo(resumo.modo);

  function comecarEdicao() {
    definirNovoNome(resumo.nome);
    definirErroDoNome(null);
    definirEditando(true);
  }

  function salvarNome(evento: FormEvent) {
    evento.preventDefault();
    definirEnviando(true);
    definirErroDoNome(null);
    renomearExecucao(identificador, novoNome)
      .then(() => {
        definirEditando(false);
        recarregar((atual) => atual + 1);
      })
      .catch((falha: unknown) => {
        definirErroDoNome(falha instanceof Error ? falha.message : String(falha));
      })
      .finally(() => definirEnviando(false));
  }

  return (
    <div className="px-5 py-4">
      <nav className="mb-1 text-[11.5px] text-suave">
        <Link to="/saidas" className="hover:text-texto">
          Saídas
        </Link>{" "}
        › {resumo.nome}
      </nav>

      <div className="flex flex-wrap items-center gap-2.5">
        {editando ? (
          <form onSubmit={salvarNome} className="flex flex-wrap items-center gap-2">
            <input
              value={novoNome}
              onChange={(evento) => definirNovoNome(evento.target.value)}
              aria-label="Novo nome da Saída"
              className="w-72 rounded-lg border border-linha bg-cartao px-2.5 py-1.5 text-sm"
            />
            <button
              type="submit"
              disabled={enviando}
              className="rounded-full bg-suno px-3.5 py-1.5 text-xs font-bold text-white disabled:opacity-50"
            >
              Salvar
            </button>
            <button
              type="button"
              onClick={() => definirEditando(false)}
              className="rounded-full border border-[#55555b] px-3.5 py-1.5 text-xs font-semibold"
            >
              Cancelar
            </button>
            {erroDoNome && <span className="text-xs text-[#ffb3ad]">{erroDoNome}</span>}
          </form>
        ) : (
          <>
            <h1 className="text-[17px] font-bold">{resumo.nome}</h1>
            <button
              type="button"
              onClick={comecarEdicao}
              className="rounded-lg border border-linha px-2 text-[11px] text-suave hover:text-texto"
            >
              renomear
            </button>
          </>
        )}
        <div className="flex-1" />
        <details className="relative">
          <summary className="cursor-pointer list-none rounded-full border border-[#55555b] px-4 py-1.5 text-xs font-semibold [&::-webkit-details-marker]:hidden">
            Exportar
          </summary>
          <div className="absolute right-0 z-20 mt-1 w-56 rounded-xl border border-linha bg-cartao-2 p-3 shadow-xl">
            <LinksDeExportacao identificador={identificador} />
          </div>
        </details>
      </div>

      <div className="mt-2 flex flex-wrap gap-1.5">
        <Chip tom="forte">{resumo.ata}</Chip>
        {modo && <Chip>{modo}</Chip>}
        <Chip>{rotuloProvedor(resumo.provedor)}</Chip>
        <Chip>{formatarDataCurta(resumo.iniciada_em)}</Chip>
      </div>

      <p className="my-3 flex flex-wrap gap-x-4 gap-y-1 text-sm text-suave">
        <span>
          <b className="text-texto">{contagem.total}</b>{" "}
          {contagem.total === 1 ? "Célula" : "Células"}
        </span>
        <span>
          <b className="text-texto">{contagem.laudoOk}</b>{" "}
          {contagem.laudoOk === 1 ? "aprovada" : "aprovadas"} pelo Laudo
        </span>
        <span>
          <b className="text-texto">{contagem.emRevisao}</b> em revisão
        </span>
        <span>
          <b className="text-texto">{contagem.bloqueadas}</b>{" "}
          {contagem.bloqueadas === 1 ? "bloqueada" : "bloqueadas"}
        </span>
        <span>
          você aprovou <b className="text-texto">{contagem.aprovadasPorVoce}</b> de{" "}
          {contagem.total}
        </span>
      </p>

      <div className="grid grid-cols-[84px_repeat(3,minmax(0,1fr))] gap-2.5">
        <div />
        {FORMATOS.map((formato) => (
          <div
            key={formato}
            className="px-0.5 text-[10.5px] font-bold uppercase tracking-wider text-suave"
          >
            {rotuloFormato(formato)}
          </div>
        ))}
        {AUDIENCIAS.map((audiencia) => (
          <Fragment key={audiencia}>
            <div className="flex items-center text-xs font-bold">{rotuloAudiencia(audiencia)}</div>
            {FORMATOS.map((formato) => {
              const posicao = porPosicao.get(chaveDaPosicao(audiencia, formato));
              return posicao ? (
                <CelulaDaMatriz
                  key={`${audiencia}:${formato}`}
                  identificador={identificador}
                  posicao={posicao}
                />
              ) : (
                <div
                  key={`${audiencia}:${formato}`}
                  className="flex min-h-[64px] items-center justify-center rounded-xl border border-dashed border-linha text-[11px] text-[#5d5d63]"
                >
                  não pedida
                </div>
              );
            })}
          </Fragment>
        ))}
      </div>

      <p className="mt-3 text-[11px] text-suave">
        {pluralizar(contagem.total, "Célula pedida", "Células pedidas")} de 9 possíveis. Clique
        numa Célula para ler o conteúdo, conferir o Laudo e decidir.
      </p>
    </div>
  );
}
