import { useState, type FormEvent } from "react";
import { Carregando, MensagemErro } from "../componentes/EstadoRequisicao";
import {
  alterarAprovacaoDaReferencia,
  analisarImagemDaReferencia,
  importarReferenciaVisual,
  listarReferenciasVisuais,
  mensagemDeFalha,
  urlDaImagemDaReferencia,
  type ReferenciaVisual,
} from "../dados/cliente";
import { usarRequisicao } from "../ganchos/usarRequisicao";
import { rotuloDaComposicao } from "../lib/pacote";
import ColetaReferencias from "../componentes/ColetaReferencias";

function Previa({ composicao }: { composicao: ReferenciaVisual["composicao"] }) {
  const base =
    "relative aspect-[4/5] overflow-hidden rounded-xl border border-[#39393f] bg-[#202023] p-4 text-white";
  if (composicao === "minimalista") {
    return (
      <div className={base} aria-label="Prévia minimalista">
        <span className="absolute right-4 top-4 h-3 w-3 rounded-full bg-suno" />
        <div className="absolute inset-x-4 top-[38%]">
          <div className="h-3 w-4/5 rounded bg-white" />
          <div className="mt-3 h-1.5 w-2/5 rounded bg-[#77777f]" />
        </div>
      </div>
    );
  }
  if (composicao === "infografico") {
    return (
      <div className={base} aria-label="Prévia de infográfico">
        <div className="h-2.5 w-3/4 rounded bg-white" />
        <div className="mt-8 grid gap-3">
          {["Juros", "Crédito", "Investimentos"].map((item, indice) => (
            <div key={item} className="flex items-center gap-2">
              <b className="grid h-7 w-7 place-items-center rounded-full bg-suno text-[10px]">
                {indice + 1}
              </b>
              <span className="flex-1 rounded-md border border-[#4a4a50] px-2 py-1 text-[9px]">
                {item}
              </span>
            </div>
          ))}
        </div>
      </div>
    );
  }
  if (composicao === "comparativo") {
    return (
      <div className={base} aria-label="Prévia comparativa">
        <div className="h-2.5 w-2/3 rounded bg-white" />
        <div className="mt-6 grid h-3/5 grid-cols-2 gap-2">
          <div className="rounded-lg border border-suno/70 bg-suno/10 p-2">
            <b className="text-[9px]">Tesouro</b>
            <div className="mt-4 space-y-2">
              <div className="h-1 rounded bg-[#a4a4aa]" />
              <div className="h-1 w-4/5 rounded bg-[#a4a4aa]" />
            </div>
          </div>
          <div className="rounded-lg border border-[#4a4a50] p-2">
            <b className="text-[9px]">CDB</b>
            <div className="mt-4 space-y-2">
              <div className="h-1 rounded bg-[#a4a4aa]" />
              <div className="h-1 w-4/5 rounded bg-[#a4a4aa]" />
            </div>
          </div>
        </div>
      </div>
    );
  }
  if (composicao === "estatistico") {
    return (
      <div className={base} aria-label="Prévia estatística">
        <div className="h-2.5 w-3/5 rounded bg-white" />
        <div className="absolute inset-x-4 top-[38%] text-center">
          <b className="text-4xl leading-none text-suno">XX,X%</b>
          <div className="mx-auto mt-3 h-1.5 w-2/5 rounded bg-[#77777f]" />
        </div>
      </div>
    );
  }
  if (composicao === "narrativo") {
    return (
      <div className={base} aria-label="Prévia narrativa">
        <div className="h-2.5 w-3/4 rounded bg-white" />
        <div className="mt-7 flex items-center gap-1">
          {[1, 2, 3].map((item) => (
            <div key={item} className="flex flex-1 items-center gap-1">
              <b className="grid h-7 w-7 place-items-center rounded-full border border-suno text-[9px]">
                0{item}
              </b>
              {item < 3 && <span className="h-px flex-1 bg-[#55555b]" />}
            </div>
          ))}
        </div>
        <div className="mt-5 h-1.5 w-4/5 rounded bg-[#8a8a92]" />
        <div className="mt-2 h-1.5 w-3/5 rounded bg-[#55555b]" />
      </div>
    );
  }
  return (
    <div className={base} aria-label="Prévia editorial">
      <span className="absolute left-0 top-0 h-1.5 w-full bg-suno" />
      <div className="mt-5 h-4 w-4/5 rounded bg-white" />
      <div className="mt-2 h-4 w-3/5 rounded bg-white" />
      <div className="mt-5 h-1.5 w-2/3 rounded bg-[#77777f]" />
      <svg className="absolute bottom-5 right-4 h-2/5 w-4/5" viewBox="0 0 100 60" aria-hidden="true">
        <path d="M2 52 L24 36 L40 43 L62 18 L78 28 L98 5" fill="none" stroke="#ff1f1f" strokeWidth="4" />
        <path d="M2 58 H98" stroke="#55555b" />
      </svg>
    </div>
  );
}

function normalizar(valor: string) {
  return valor.replaceAll("_", " ");
}

export default function ReferenciasVisuais() {
  const [recarga, definirRecarga] = useState(0);
  const [formularioAberto, definirFormularioAberto] = useState(false);
  const [ocupado, definirOcupado] = useState<string | null>(null);
  const [aviso, definirAviso] = useState<string | null>(null);
  const estado = usarRequisicao(listarReferenciasVisuais, [recarga]);

  function importar(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault();
    const formulario = evento.currentTarget;
    const dados = new FormData(formulario);
    definirOcupado("importar");
    definirAviso(null);
    importarReferenciaVisual({
      titulo: String(dados.get("titulo") ?? ""),
      tema: String(dados.get("tema") ?? ""),
      composicao: String(dados.get("composicao") ?? "editorial") as ReferenciaVisual["composicao"],
      descricao: String(dados.get("descricao") ?? ""),
      instrucao_de_design: String(dados.get("instrucao_de_design") ?? ""),
      origem: String(dados.get("origem") ?? "Importação manual"),
    })
      .then(() => {
        formulario.reset();
        definirFormularioAberto(false);
        definirRecarga((atual) => atual + 1);
      })
      .catch((erro: unknown) => definirAviso(mensagemDeFalha(erro)))
      .finally(() => definirOcupado(null));
  }

  function mudarAprovacao(referencia: ReferenciaVisual) {
    definirOcupado(referencia.identificador);
    definirAviso(null);
    alterarAprovacaoDaReferencia(referencia.identificador, !referencia.aprovada)
      .then(() => definirRecarga((atual) => atual + 1))
      .catch((erro: unknown) => definirAviso(mensagemDeFalha(erro)))
      .finally(() => definirOcupado(null));
  }

  function analisarImagem(referencia: ReferenciaVisual, arquivo: File | undefined) {
    if (!arquivo) return;
    definirOcupado(`imagem:${referencia.identificador}`);
    definirAviso(null);
    analisarImagemDaReferencia(referencia.identificador, arquivo)
      .then((atualizada) => {
        definirRecarga((atual) => atual + 1);
        if (atualizada.estado_analise === "erro") {
          definirAviso(
            atualizada.mensagem_analise ??
              "A imagem foi salva, mas a análise automática não terminou.",
          );
        }
      })
      .catch((erro: unknown) => definirAviso(mensagemDeFalha(erro)))
      .finally(() => definirOcupado(null));
  }

  if (estado.situacao === "carregando") {
    return <Carregando rotulo="Carregando referências visuais…" />;
  }
  if (estado.situacao === "erro") return <MensagemErro erro={estado.erro} />;

  const aprovadas = estado.dados.filter((item) => item.aprovada);
  return (
    <div className="px-5 py-4">
      <div className="mb-5 flex flex-wrap items-end gap-3">
        <div>
          <h1 className="text-[17px] font-bold">Configuração visual</h1>
          <p className="mt-1 max-w-2xl text-xs text-suave">
            Cadastre e aprove exemplos de Carrossel para escolher depois, junto da fonte, na
            Curadoria. Os exemplos orientam o design; textos e números continuam vindo da fonte.
          </p>
        </div>
        <span className="rounded-full border border-suno/50 bg-suno/10 px-3 py-1 text-xs font-semibold text-[#ffb3ad]">
          {aprovadas.length} aprovadas
        </span>
        <div className="flex-1" />
        <button
          type="button"
          onClick={() => definirFormularioAberto((atual) => !atual)}
          className="rounded-full bg-suno px-4 py-1.5 text-xs font-bold uppercase tracking-wide text-white"
        >
          {formularioAberto ? "Fechar" : "Adicionar exemplo"}
        </button>
      </div>

      {formularioAberto && (
        <form onSubmit={importar} className="mb-5 grid gap-3 rounded-xl border border-linha bg-cartao p-4 md:grid-cols-2">
          <label className="grid gap-1 text-xs">
            Título
            <input name="titulo" required minLength={3} maxLength={120} className="rounded-lg border border-linha bg-fundo px-3 py-2" />
          </label>
          <label className="grid gap-1 text-xs">
            Tema financeiro
            <input name="tema" required minLength={3} maxLength={100} className="rounded-lg border border-linha bg-fundo px-3 py-2" />
          </label>
          <label className="grid gap-1 text-xs">
            Composição
            <select name="composicao" className="rounded-lg border border-linha bg-fundo px-3 py-2">
              {["editorial", "minimalista", "infografico", "comparativo", "estatistico", "narrativo"].map((item) => (
                <option key={item} value={item}>{rotuloDaComposicao(item)}</option>
              ))}
            </select>
          </label>
          <label className="grid gap-1 text-xs">
            URL ou origem autorizada
            <input name="origem" placeholder="Opcional" maxLength={500} className="rounded-lg border border-linha bg-fundo px-3 py-2" />
          </label>
          <label className="grid gap-1 text-xs md:col-span-2">
            O que aproveitar da referência
            <textarea name="descricao" required minLength={10} maxLength={400} rows={2} className="rounded-lg border border-linha bg-fundo px-3 py-2" />
          </label>
          <label className="grid gap-1 text-xs md:col-span-2">
            Instrução de design
            <textarea name="instrucao_de_design" required minLength={10} maxLength={500} rows={2} className="rounded-lg border border-linha bg-fundo px-3 py-2" />
          </label>
          <div className="flex items-center gap-3 md:col-span-2">
            <button disabled={ocupado === "importar"} className="rounded-full bg-suno px-4 py-1.5 text-xs font-bold text-white disabled:opacity-50">
              {ocupado === "importar" ? "Importando…" : "Salvar para curadoria"}
            </button>
            <span className="text-[11px] text-suave">A nova referência entra não aprovada.</span>
          </div>
        </form>
      )}

      {aviso && <p role="alert" className="mb-4 rounded-xl border border-suno/45 bg-suno/10 px-3 py-2 text-sm text-[#ffb3ad]">{aviso}</p>}

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {estado.dados.map((referencia) => (
          <article key={referencia.identificador} className="grid grid-cols-[112px_1fr] gap-3 rounded-xl border border-linha bg-cartao p-3">
            {referencia.imagem_disponivel ? (
              <img
                src={urlDaImagemDaReferencia(referencia.identificador, recarga)}
                alt={`Referência ${referencia.titulo}`}
                className="aspect-[4/5] w-full rounded-xl border border-[#39393f] object-cover"
              />
            ) : (
              <Previa composicao={referencia.composicao} />
            )}
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-1.5">
                <b className="text-sm">{rotuloDaComposicao(referencia.composicao)}</b>
                <span className="rounded-full bg-[#2f2f34] px-2 py-0.5 text-[9px] uppercase tracking-wide text-suave">
                  {referencia.aprovada ? "aprovada" : "em revisão"}
                </span>
              </div>
              <h2 className="mt-1 text-xs font-semibold">{referencia.titulo}</h2>
              <p className="mt-1 text-[10.5px] text-suave">{referencia.tema}</p>
              <p className="mt-2 text-[11px] leading-relaxed">{referencia.descricao}</p>
              <div className="mt-2 flex flex-wrap gap-1">
                <span className="rounded bg-[#2f2f34] px-1.5 py-0.5 text-[9px] text-suave">
                  título {normalizar(referencia.analise.posicao_do_titulo)}
                </span>
                <span className="rounded bg-[#2f2f34] px-1.5 py-0.5 text-[9px] text-suave">
                  densidade {normalizar(referencia.analise.densidade_textual)}
                </span>
                {referencia.estado_analise !== "nao_solicitada" && (
                  <span className="rounded bg-[#2f2f34] px-1.5 py-0.5 text-[9px] text-suave">
                    análise {normalizar(referencia.estado_analise)}
                  </span>
                )}
              </div>
              <div className="mt-3 flex flex-wrap gap-1.5">
                <label className="cursor-pointer rounded-full border border-[#55555b] px-2.5 py-1 text-[10px] font-semibold hover:border-texto">
                  {ocupado === `imagem:${referencia.identificador}`
                    ? "Analisando…"
                    : referencia.imagem_disponivel
                      ? "Trocar imagem"
                      : "Enviar imagem"}
                  <input
                    type="file"
                    accept="image/png,image/jpeg,image/webp"
                    disabled={ocupado !== null}
                    className="sr-only"
                    onChange={(evento) => {
                      analisarImagem(referencia, evento.target.files?.[0]);
                      evento.target.value = "";
                    }}
                  />
                </label>
                <button
                  type="button"
                  disabled={ocupado !== null}
                  onClick={() => mudarAprovacao(referencia)}
                  className="rounded-full border border-[#55555b] px-2.5 py-1 text-[10px] font-semibold hover:border-texto disabled:opacity-50"
                >
                  {referencia.aprovada ? "Rejeitar" : "Aprovar"}
                </button>
              </div>
              {referencia.provedor_analise && (
                <p className="mt-1.5 text-[9.5px] text-suave">
                  análise automática: {referencia.provedor_analise}
                </p>
              )}
            </div>
          </article>
        ))}
      </div>
      <div className="mt-6 border-t border-linha pt-6">
        <ColetaReferencias />
      </div>
    </div>
  );
}
