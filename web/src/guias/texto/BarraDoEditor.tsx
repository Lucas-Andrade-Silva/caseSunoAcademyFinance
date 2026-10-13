// A barra de ferramentas do editor: desfazer e refazer, negrito, itálico, sublinhado, listas,
// alinhamento, tamanho, distância entre linhas, fonte (cartões "Aa") e cor (amostras redondas).
// Os botões não tiram o foco do texto (`mousedown` sem ação padrão), senão a seleção se perderia.
import type { Editor } from "@tiptap/core";
import { useEditorState } from "@tiptap/react";
import type { ReactNode } from "react";
import {
  IconeCentro,
  IconeDesfazer,
  IconeDireita,
  IconeEsquerda,
  IconeItalico,
  IconeJustificado,
  IconeLista,
  IconeListaNumerada,
  IconeMais,
  IconeNegrito,
  IconeRefazer,
  IconeSublinhado,
} from "../../interface/Icones";
import {
  CORES,
  ENTRELINHAS,
  FAMILIAS,
  FAMILIA_PADRAO,
  TAMANHO_PADRAO,
  entrelinhaDoCss,
  familiaDoCss,
  lerTamanho,
  mesmaCor,
  passoDeTamanho,
  rotuloDaEntrelinha,
  type IdDaFamilia,
} from "./ajustes";
import { aplicarNoTexto } from "./comandos";
import { IconeEntrelinha, IconeMenos } from "./icones";

type Alinhamento = "left" | "center" | "right" | "justify";

const ALINHAMENTOS: readonly { valor: Alinhamento; rotulo: string; icone: ReactNode }[] = [
  { valor: "left", rotulo: "Alinhar à esquerda", icone: <IconeEsquerda size={20} /> },
  { valor: "center", rotulo: "Centralizar", icone: <IconeCentro size={20} /> },
  { valor: "right", rotulo: "Alinhar à direita", icone: <IconeDireita size={20} /> },
  { valor: "justify", rotulo: "Justificar", icone: <IconeJustificado size={20} /> },
];

function Grupo({ rotulo, children }: { rotulo: string; children: ReactNode }) {
  return (
    <div role="group" aria-label={rotulo} className="inline-flex items-center gap-0.5 rounded-lg bg-superficie p-1">
      {children}
    </div>
  );
}

function Ferramenta({
  rotulo,
  ativa = false,
  desabilitada = false,
  onClick,
  children,
}: {
  rotulo: string;
  ativa?: boolean;
  desabilitada?: boolean;
  onClick: () => void;
  children: ReactNode;
}) {
  return (
    <button
      type="button"
      aria-label={rotulo}
      title={rotulo}
      aria-pressed={ativa}
      disabled={desabilitada}
      onMouseDown={(evento) => evento.preventDefault()}
      onClick={onClick}
      className={`grid h-9 min-w-9 place-items-center rounded-md px-1 text-[13px] font-semibold transition-colors duration-150 disabled:cursor-not-allowed disabled:opacity-40 ${
        ativa ? "bg-claro text-ilha" : "text-claro hover:bg-superficie-alta disabled:hover:bg-transparent"
      }`}
    >
      {children}
    </button>
  );
}

/** O tamanho que o passo do botão parte: o da seleção, ou o do corpo do texto quando nada está selecionado. */
function tamanhoAtual(editor: Editor, daSelecao: string | null | undefined): number {
  if (!editor.state.selection.empty) return lerTamanho(daSelecao) ?? TAMANHO_PADRAO;
  let tamanho: number | null = null;
  let achou = false;
  editor.state.doc.descendants((no) => {
    if (achou) return false;
    if (!no.isTextblock) return true;
    if (no.type.name !== "heading") {
      achou = true;
      tamanho = lerTamanho(no.firstChild?.marks.find((marca) => marca.type.name === 'textStyle')?.attrs.fontSize as string | undefined);
    }
    return false;
  });
  return tamanho ?? TAMANHO_PADRAO;
}

function RotuloDaSecao({ children }: { children: ReactNode }) {
  return <h3 className="mb-2.5 text-[12px] font-medium uppercase tracking-[0.02em] text-texto">{children}</h3>;
}

export default function BarraDoEditor({ editor }: { editor: Editor }) {
  const estado = useEditorState({
    editor,
    selector: ({ editor: atual }) => {
      const aparenciaDoTrecho = atual.getAttributes("textStyle") as Record<string, string | null | undefined>;
      const bloco = atual.isActive("heading") ? "heading" : "paragraph";
      return {
        negrito: atual.isActive("bold"),
        italico: atual.isActive("italic"),
        sublinhado: atual.isActive("underline"),
        lista: atual.isActive("bulletList"),
        numerada: atual.isActive("orderedList"),
        alinhamento: (ALINHAMENTOS.find((a) => atual.isActive({ textAlign: a.valor }))?.valor ?? "left") as Alinhamento,
        familia: familiaDoCss(aparenciaDoTrecho.fontFamily) ?? FAMILIA_PADRAO,
        tamanho: tamanhoAtual(atual, aparenciaDoTrecho.fontSize),
        cor: aparenciaDoTrecho.color ?? null,
        entrelinha: entrelinhaDoCss((atual.getAttributes(bloco) as { entreLinhas?: string | null }).entreLinhas),
        podeDesfazer: atual.can().undo(),
        podeRefazer: atual.can().redo(),
      };
    },
  });

  const mudarTamanho = (sentido: 1 | -1) =>
    aplicarNoTexto(editor, { fontSize: `${passoDeTamanho(estado.tamanho, sentido)}px` }, { poupaTitulos: true });
  const escolherFamilia = (id: IdDaFamilia) => {
    const familia = FAMILIAS.find((f) => f.id === id);
    if (familia) aplicarNoTexto(editor, { fontFamily: familia.css });
  };

  return (
    <div role="toolbar" aria-label="Formatação do texto" className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center gap-2">
        <Grupo rotulo="Histórico de edição">
          <Ferramenta rotulo="Desfazer" desabilitada={!estado.podeDesfazer} onClick={() => editor.chain().focus().undo().run()}>
            <IconeDesfazer size={20} />
          </Ferramenta>
          <Ferramenta rotulo="Refazer" desabilitada={!estado.podeRefazer} onClick={() => editor.chain().focus().redo().run()}>
            <IconeRefazer size={20} />
          </Ferramenta>
        </Grupo>
        <Grupo rotulo="Destaques">
          <Ferramenta rotulo="Negrito" ativa={estado.negrito} onClick={() => editor.chain().focus().toggleBold().run()}>
            <IconeNegrito size={20} />
          </Ferramenta>
          <Ferramenta rotulo="Itálico" ativa={estado.italico} onClick={() => editor.chain().focus().toggleItalic().run()}>
            <IconeItalico size={20} />
          </Ferramenta>
          <Ferramenta rotulo="Sublinhado" ativa={estado.sublinhado} onClick={() => editor.chain().focus().toggleUnderline().run()}>
            <IconeSublinhado size={20} />
          </Ferramenta>
        </Grupo>
        <Grupo rotulo="Listas">
          <Ferramenta rotulo="Lista com marcadores" ativa={estado.lista} onClick={() => editor.chain().focus().toggleBulletList().run()}>
            <IconeLista size={20} />
          </Ferramenta>
          <Ferramenta rotulo="Lista numerada" ativa={estado.numerada} onClick={() => editor.chain().focus().toggleOrderedList().run()}>
            <IconeListaNumerada size={20} />
          </Ferramenta>
        </Grupo>
        <Grupo rotulo="Alinhamento">
          {ALINHAMENTOS.map((alinhamento) => (
            <Ferramenta
              key={alinhamento.valor}
              rotulo={alinhamento.rotulo}
              ativa={estado.alinhamento === alinhamento.valor}
              onClick={() => editor.chain().focus().setTextAlign(alinhamento.valor).run()}
            >
              {alinhamento.icone}
            </Ferramenta>
          ))}
        </Grupo>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <Grupo rotulo="Tamanho da fonte">
          <Ferramenta rotulo="Diminuir a fonte" onClick={() => mudarTamanho(-1)}>
            <IconeMenos size={18} />
          </Ferramenta>
          <output aria-label="Tamanho atual" className="min-w-9 text-center text-[14px] font-semibold tabular-nums">
            {estado.tamanho}
          </output>
          <Ferramenta rotulo="Aumentar a fonte" onClick={() => mudarTamanho(1)}>
            <IconeMais size={18} />
          </Ferramenta>
        </Grupo>
        <Grupo rotulo="Distância entre as linhas">
          <span className="grid h-9 w-8 place-items-center text-etiqueta" aria-hidden="true">
            <IconeEntrelinha size={18} />
          </span>
          {ENTRELINHAS.map((valor) => (
            <Ferramenta
              key={valor}
              rotulo={`Distância ${rotuloDaEntrelinha(valor)}`}
              ativa={estado.entrelinha === valor}
              onClick={() => editor.chain().focus().definirEntreLinhas(valor).run()}
            >
              {rotuloDaEntrelinha(valor)}
            </Ferramenta>
          ))}
        </Grupo>
      </div>

      <section>
        <RotuloDaSecao>Fonte</RotuloDaSecao>
        <div role="group" aria-label="Fonte" className="grid grid-cols-2 gap-2.5 sm:grid-cols-4">
          {FAMILIAS.map((familia) => {
            const ativa = estado.familia === familia.id;
            return (
              <button
                key={familia.id}
                type="button"
                aria-pressed={ativa}
                onMouseDown={(evento) => evento.preventDefault()}
                onClick={() => escolherFamilia(familia.id)}
                className={`flex h-[76px] flex-col items-center justify-center gap-0.5 rounded-lg transition-colors duration-150 ${
                  ativa ? "bg-claro text-ilha" : "bg-superficie text-texto hover:bg-superficie-alta"
                }`}
              >
                <span className="text-[26px] leading-none" style={{ fontFamily: familia.css }}>
                  Aa
                </span>
                <span className={`text-[12px] ${ativa ? "text-[#4a4a4a]" : "text-etiqueta"}`}>{familia.nome}</span>
              </button>
            );
          })}
        </div>
      </section>

      <section>
        <RotuloDaSecao>Cor</RotuloDaSecao>
        <div role="group" aria-label="Cor do texto" className="flex flex-wrap items-center gap-3">
          <button
            type="button"
            aria-label="Cor padrão"
            title="Cor padrão"
            aria-pressed={estado.cor === null}
            onMouseDown={(evento) => evento.preventDefault()}
            onClick={() => aplicarNoTexto(editor, { color: null })}
            className={`h-8 w-8 rounded-full border border-[#555] transition-shadow duration-150 ${
              estado.cor === null ? "ring-2 ring-claro ring-offset-2 ring-offset-fundo" : "hover:ring-2 hover:ring-[#555] hover:ring-offset-2 hover:ring-offset-fundo"
            }`}
            style={{ background: "linear-gradient(135deg, #ffffff 50%, #1a1a1a 50%)" }}
          />
          {CORES.map((cor) => {
            const ativa = mesmaCor(estado.cor, cor.valor);
            return (
              <button
                key={cor.valor}
                type="button"
                aria-label={cor.nome}
                title={cor.nome}
                aria-pressed={ativa}
                onMouseDown={(evento) => evento.preventDefault()}
                onClick={() => aplicarNoTexto(editor, { color: cor.valor })}
                className={`h-8 w-8 rounded-full transition-shadow duration-150 ${
                  ativa ? "ring-2 ring-claro ring-offset-2 ring-offset-fundo" : "hover:ring-2 hover:ring-[#555] hover:ring-offset-2 hover:ring-offset-fundo"
                }`}
                style={{ backgroundColor: cor.valor }}
              />
            );
          })}
        </div>
      </section>
    </div>
  );
}
