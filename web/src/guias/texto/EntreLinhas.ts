// A distância entre linhas por parágrafo. A extensão `LineHeight` do Tiptap grava o valor no
// trecho de texto (um `span`), e uma linha só ganha altura nova se o trecho dela for o maior;
// aqui o valor fica no parágrafo ou título, e vale a linha inteira.
import { Extension } from "@tiptap/core";

declare module "@tiptap/core" {
  interface Commands<ReturnType> {
    entreLinhas: {
      /** Vale para os parágrafos da seleção; sem seleção, para o texto todo. */
      definirEntreLinhas: (valor: number) => ReturnType;
    };
  }
}

const BLOCOS = ["paragraph", "heading"];

export const EntreLinhas = Extension.create({
  name: "entreLinhas",

  addGlobalAttributes() {
    return [
      {
        types: BLOCOS,
        attributes: {
          entreLinhas: {
            default: null,
            parseHTML: (elemento: HTMLElement) => elemento.style.lineHeight || null,
            renderHTML: (atributos: Record<string, unknown>) =>
              atributos.entreLinhas ? { style: `line-height: ${String(atributos.entreLinhas)}` } : {},
          },
        },
      },
    ];
  },

  addCommands() {
    return {
      definirEntreLinhas:
        (valor: number) =>
        ({ state, tr, dispatch }) => {
          if (!dispatch) return true;
          const { from, to, empty } = state.selection;
          const inicio = empty ? 0 : from;
          const fim = empty ? state.doc.content.size : to;
          state.doc.nodesBetween(inicio, fim, (no, posicao) => {
            if (BLOCOS.includes(no.type.name)) {
              tr.setNodeMarkup(posicao, undefined, { ...no.attrs, entreLinhas: String(valor) });
            }
          });
          return true;
        },
    };
  },
});
