// A tela do texto pronto. Sem editar, o texto no formato escolhido ocupa a área toda. Editar abre,
// à esquerda, o editor (a coluna desliza em 250 ms) e o texto final fica à direita; ele só muda
// quando a pessoa aperta "Salvar edição". A faixa do topo é uma só nos dois estados: Editar ou
// Fechar no canto esquerdo, as pílulas de formato e o Salvar no direito.
import { useEffect, useMemo, useRef, useState } from "react";
import { editarTextoDaCelula, type Audiencia, type Laudo } from "../../dados/cliente";
import Barras from "../../interface/Barras";
import Botao from "../../interface/Botao";
import PainelDeCorrecoes from "../../interface/PainelDeCorrecoes";
import { CorpoDaPrevia, TituloDaGuia } from "../../interface/Divisao";
import { IconeFechar, IconeLapis, IconeMarca, IconeSalvar } from "../../interface/Icones";
import { Pilulas } from "../../interface/Pilulas";
import { barrasDoLaudo } from "../../nucleo/laudo";
import { localizarCorrecoes, type CampoCorrigivel } from "../../nucleo/correcoes";
import { rotuloAudiencia, rotuloMotivo } from "../../texto/rotulos";
import EditorDoTexto from "./EditorDoTexto";
import { FORMATOS_DO_TEXTO, type FormatoDoTexto } from "./formatos";
import SalvarTexto from "./SalvarTexto";
import VistaDoTexto from "./VistaDoTexto";
import "./texto.css";

interface Trabalho {
  /** O que o editor escreveu ao abrir, ou a última edição aplicada. */
  base: string;
  /** O que está no editor agora. */
  rascunho: string;
}

interface Propriedades {
  execucaoId: string | null;
  laudo: Laudo | null;
  onFecharSalvo?: () => void;
  audiencias: readonly Audiencia[];
  audiencia: Audiencia;
  onMudarAudiencia: (audiencia: Audiencia) => void;
  formato: FormatoDoTexto;
  onMudarFormato: (formato: FormatoDoTexto) => void;
  /** O texto que o formato mostra agora, da audiência escolhida. */
  html: string;
  onAplicar: (html: string) => void;
  onSalvar: (formato: FormatoDoTexto, html: string, laudo: Laudo | null) => void;
}

/** Conserva a separação entre parágrafos e itens ao enviar o conteúdo ao Avaliador. */
function textoDoHtml(html: string): string {
  const corpo = new DOMParser().parseFromString(html, "text/html").body;
  corpo.querySelectorAll("script, style").forEach((no) => no.remove());
  corpo.querySelectorAll("br").forEach((no) => no.replaceWith("\n"));
  corpo.querySelectorAll("p, h1, h2, h3, h4, h5, h6, li, blockquote, div").forEach((no) => no.append("\n\n"));
  return (corpo.textContent ?? "").replace(/\n[ \t]*\n(?:[ \t]*\n)+/g, "\n\n").trim();
}

/** Um aviso que acende e apaga sozinho: "Salvo", "Edição salva". */
function usarAviso(duracaoMs: number): [boolean, () => void] {
  const [aceso, definirAceso] = useState(false);
  useEffect(() => {
    if (!aceso) return;
    const temporizador = window.setTimeout(() => definirAceso(false), duracaoMs);
    return () => window.clearTimeout(temporizador);
  }, [aceso, duracaoMs]);
  return [aceso, () => definirAceso(true)];
}

export default function AreaDoTexto({
  execucaoId,
  laudo,
  onFecharSalvo,
  audiencias,
  audiencia,
  onMudarAudiencia,
  formato,
  onMudarFormato,
  html,
  onAplicar,
  onSalvar,
}: Propriedades) {
  const [editando, definirEditando] = useState(false);
  const [trabalhos, definirTrabalhos] = useState<Partial<Record<Audiencia, Trabalho>>>({});
  const [salvando, definirSalvando] = useState(false);
  const [salvo, avisarSalvo] = usarAviso(1800);
  const [editado, avisarEditado] = usarAviso(1800);
  const [avaliacoes, definirAvaliacoes] = useState<Partial<Record<Audiencia, { html: string; laudo: Laudo }>>>({});
  const [reavaliando, definirReavaliando] = useState(false);
  const [erro, definirErro] = useState<string | null>(null);
  const revisoes = useRef<Partial<Record<Audiencia, number>>>({});
  const revisaoEmCurso = useRef(false);

  const trabalho = trabalhos[audiencia];
  const pendente = trabalho !== undefined && trabalho.rascunho !== trabalho.base;

  function aplicar(): string | null {
    if (!trabalho || !pendente) return null;
    onAplicar(trabalho.rascunho);
    definirTrabalhos((atuais) => ({ ...atuais, [audiencia]: { base: trabalho.rascunho, rascunho: trabalho.rascunho } }));
    return trabalho.rascunho;
  }

  function pedirSalvar() {
    // Quem edita e aperta Salvar quer guardar o que escreveu: a edição pendente entra antes.
    if (editando) aplicar();
    definirSalvando(true);
  }

  const htmlParaSalvar = editando && pendente && trabalho ? trabalho.rascunho : html;
  const avaliado = avaliacoes[audiencia];
  const laudoAtual = avaliado?.html === htmlParaSalvar ? avaliado.laudo : pendente ? null : laudo;
  const aprovado = laudoAtual?.destino === "aprovado";
  // Enquanto a pessoa digita, o novo texto ainda não tem Laudo; as indicações da versão anterior
  // continuam visíveis para ela não perder a referência no primeiro caractere alterado.
  const laudoParaCorrecao = laudoAtual ?? avaliado?.laudo ?? laudo;
  const motivosAntesDoJev = (laudoParaCorrecao?.motivos ?? []).filter(
    (motivo) => motivo !== "qualidade" && motivo !== "fidelidade",
  );
  const qualidadeMedida = laudoParaCorrecao?.medidas.some((medida) => medida.metrica === "qualidade") ?? false;
  const camposCorrigiveis = useMemo<CampoCorrigivel[]>(
    () => [{ indice: 0, local: "Texto analítico", texto: textoDoHtml(htmlParaSalvar) }],
    [htmlParaSalvar],
  );
  const correcoes = useMemo(
    () => localizarCorrecoes(laudoParaCorrecao, camposCorrigiveis),
    [laudoParaCorrecao, camposCorrigiveis],
  );

  async function reavaliar() {
    if (execucaoId === null || revisaoEmCurso.current) return;
    const revisao = revisoes.current[audiencia] ?? 0;
    const htmlAvaliado = htmlParaSalvar;
    if (editando) aplicar();
    revisaoEmCurso.current = true;
    definirReavaliando(true);
    definirErro(null);
    try {
      const novo = await editarTextoDaCelula(execucaoId, audiencia, "texto_analitico", { texto: textoDoHtml(htmlAvaliado) });
      if ((revisoes.current[audiencia] ?? 0) !== revisao) return;
      definirAvaliacoes((atuais) => ({ ...atuais, [audiencia]: { html: htmlAvaliado, laudo: novo } }));
    } catch (falha) {
      definirErro(falha instanceof Error ? falha.message : "Não consegui reavaliar o texto.");
    } finally {
      revisaoEmCurso.current = false;
      definirReavaliando(false);
    }
  }

  return (
    <div className="texto-guia" data-editando={editando}>
      <div className="texto-fundo-do-editor" aria-hidden="true" />

      <header className="relative z-10 flex flex-wrap items-center gap-x-4 gap-y-3 px-5 pb-3 pt-10 lg:pl-[var(--area-da-rail)] lg:pr-[50px]">
        <div className="basis-full">
          <TituloDaGuia>Texto analítico</TituloDaGuia>
        </div>
        <div className="flex basis-full flex-wrap items-center gap-3">
          <p role="status" className="text-[14px] text-etiqueta">
            {aprovado ? "Laudo aprovado para esta versão." : laudoAtual ? "Rascunho · Laudo reprovado." : "Rascunho · esta versão ainda não foi avaliada."}
          </p>
          {execucaoId !== null && !aprovado && (
            <Botao tamanho="pequeno" disabled={reavaliando} onClick={() => void reavaliar()}>
              {reavaliando ? "Reavaliando…" : "Salvar texto e reavaliar"}
            </Botao>
          )}
          {onFecharSalvo && <Botao tamanho="pequeno" onClick={onFecharSalvo}>Sair do salvo</Botao>}
          {erro && <p role="alert" className="text-[14px] text-coral-claro">{erro}</p>}
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <Botao
            variante="escuro"
            aria-expanded={editando}
            icone={editando ? <IconeFechar size={18} /> : <IconeLapis size={18} />}
            onClick={() => definirEditando((atual) => !atual)}
          >
            {editando ? "Fechar" : "Editar"}
          </Botao>
          {audiencias.length > 1 && (
            <Pilulas<Audiencia>
              rotuloAcessivel="Audiência"
              valor={audiencia}
              onMudar={onMudarAudiencia}
              opcoes={audiencias.map((a) => ({ valor: a, rotulo: rotuloAudiencia(a) }))}
            />
          )}
        </div>
        <div className="ml-auto flex flex-wrap items-center gap-3">
          <Pilulas<FormatoDoTexto>
            rotuloAcessivel="Formato do texto"
            valor={formato}
            onMudar={onMudarFormato}
            opcoes={FORMATOS_DO_TEXTO}
          />
          <Botao
            variante="claro"
            icone={salvo ? <IconeMarca size={18} strokeWidth={2.5} /> : <IconeSalvar size={18} />}
            onClick={pedirSalvar}
          >
            {salvo ? "Salvo" : aprovado ? "Salvar" : "Salvar rascunho"}
          </Botao>
        </div>
      </header>

      <div className="texto-corpo">
        <aside className="texto-editor" aria-label="Editor do texto" inert={!editando}>
          <div className="texto-editor-miolo flex flex-col overflow-y-auto px-5 pb-6 pt-4 lg:pl-[var(--area-da-rail)] lg:pr-6 lg:pt-1">
            <EditorDoTexto
              key={audiencia}
              inicial={trabalho?.rascunho ?? html}
              aoCriar={(criado) =>
                definirTrabalhos((atuais) =>
                  atuais[audiencia] ? atuais : { ...atuais, [audiencia]: { base: criado, rascunho: criado } },
                )
              }
              aoMudar={(escrito) => {
                revisoes.current[audiencia] = (revisoes.current[audiencia] ?? 0) + 1;
                definirTrabalhos((atuais) => {
                  const atual = atuais[audiencia];
                  return { ...atuais, [audiencia]: { base: atual?.base ?? escrito, rascunho: escrito } };
                });
              }}
            />
            <div className="mt-4 shrink-0">
              <Botao
                variante={pendente ? "claro" : "escuro"}
                tamanho="grande"
                disabled={!pendente && !editado}
                icone={editado ? <IconeMarca size={18} strokeWidth={2.5} /> : undefined}
                onClick={() => {
                  if (aplicar()) avisarEditado();
                }}
              >
                {editado ? "Edição salva" : "Salvar edição"}
              </Botao>
            </div>
          </div>
        </aside>

        <section className="texto-previa" aria-label="Texto no formato final">
          <CorpoDaPrevia className="pt-2">
            {laudoParaCorrecao && (
              <details
                open={laudoParaCorrecao.destino !== "aprovado"}
                className="mb-4 rounded-lg bg-superficie p-4 lg:ml-[calc(var(--area-da-rail)-50px)]"
              >
                <summary className="cursor-pointer text-[15px]">Ver Laudo desta versão</summary>
                <div className="mt-4">
                  {motivosAntesDoJev.length > 0 && !qualidadeMedida && (
                    <p className="mb-4 rounded-lg bg-fundo px-4 py-3 text-[14px] leading-relaxed text-claro">
                      O Jev não foi executado nesta última versão porque a avaliação anterior reprovou em {motivosAntesDoJev.map(rotuloMotivo).join(", ")}. Primeiro essa etapa precisa passar; depois o Jev e a Fidelidade são executados.
                    </p>
                  )}
                  <div className="mb-4">
                    <PainelDeCorrecoes
                      pontos={correcoes}
                      aoEditar={() => definirEditando(true)}
                      aoSelecionar={() => definirEditando(true)}
                    />
                  </div>
                  <Barras barras={barrasDoLaudo(laudoParaCorrecao)} />
                </div>
              </details>
            )}
            <div key={`${formato}-${audiencia}`} className="surge">
              <VistaDoTexto formato={formato} html={html} />
            </div>
          </CorpoDaPrevia>
        </section>
      </div>

      {salvando && (
        <SalvarTexto
          html={htmlParaSalvar}
          formatoInicial={formato}
          onFechar={() => definirSalvando(false)}
          onConfirmar={(escolhido) => {
            onSalvar(escolhido, htmlParaSalvar, laudoAtual);
            definirSalvando(false);
            avisarSalvo();
          }}
        />
      )}
    </div>
  );
}
