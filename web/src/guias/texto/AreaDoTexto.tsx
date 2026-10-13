// A tela do texto pronto. Sem editar, o texto no formato escolhido ocupa a área toda. Editar abre,
// à esquerda, o editor (a coluna desliza em 250 ms) e o texto final fica à direita; ele só muda
// quando a pessoa aperta "Salvar edição". A faixa do topo é uma só nos dois estados: Editar ou
// Fechar no canto esquerdo, as pílulas de formato e o Salvar no direito.
import { useEffect, useState } from "react";
import type { Audiencia } from "../../dados/cliente";
import Botao from "../../interface/Botao";
import { CorpoDaPrevia } from "../../interface/Divisao";
import { IconeFechar, IconeLapis, IconeMais, IconeMarca, IconeSalvar } from "../../interface/Icones";
import { Pilulas } from "../../interface/Pilulas";
import { rotuloAudiencia } from "../../texto/rotulos";
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
  audiencias: readonly Audiencia[];
  audiencia: Audiencia;
  onMudarAudiencia: (audiencia: Audiencia) => void;
  formato: FormatoDoTexto;
  onMudarFormato: (formato: FormatoDoTexto) => void;
  /** O texto que o formato mostra agora, da audiência escolhida. */
  html: string;
  onAplicar: (html: string) => void;
  onSalvar: (formato: FormatoDoTexto, html: string) => void;
  onGerarOutro: () => void;
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
  audiencias,
  audiencia,
  onMudarAudiencia,
  formato,
  onMudarFormato,
  html,
  onAplicar,
  onSalvar,
  onGerarOutro,
}: Propriedades) {
  const [editando, definirEditando] = useState(false);
  const [trabalhos, definirTrabalhos] = useState<Partial<Record<Audiencia, Trabalho>>>({});
  const [salvando, definirSalvando] = useState(false);
  const [salvo, avisarSalvo] = usarAviso(1800);
  const [editado, avisarEditado] = usarAviso(1800);
  const [confirmandoNovo, avisarConfirmandoNovo] = usarAviso(3000);

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

  return (
    <div className="texto-guia" data-editando={editando}>
      <div className="texto-fundo-do-editor" aria-hidden="true" />

      <header className="relative z-10 flex flex-wrap items-center gap-x-4 gap-y-3 px-5 pb-3 pt-10 lg:pl-[var(--area-da-rail)] lg:pr-[50px]">
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
          <button
            type="button"
            aria-label="Gerar outro texto"
            title="Gerar outro texto"
            onClick={() => (confirmandoNovo ? onGerarOutro() : avisarConfirmandoNovo())}
            className={`inline-flex h-[50px] shrink-0 items-center justify-center gap-2.5 rounded-lg bg-superficie text-[15px] font-semibold uppercase tracking-[0.01em] transition-colors duration-150 hover:bg-superficie-alta ${
              confirmandoNovo ? "px-6" : "w-[50px]"
            }`}
          >
            <IconeMais size={18} />
            {confirmandoNovo && "Confirmar"}
          </button>
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
            {salvo ? "Salvo" : "Salvar"}
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
              aoMudar={(escrito) =>
                definirTrabalhos((atuais) => {
                  const atual = atuais[audiencia];
                  return { ...atuais, [audiencia]: { base: atual?.base ?? escrito, rascunho: escrito } };
                })
              }
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
            onSalvar(escolhido, htmlParaSalvar);
            definirSalvando(false);
            avisarSalvo();
          }}
        />
      )}
    </div>
  );
}
