// Aplicar a aparência de um trecho. Com texto selecionado vale para a seleção; sem seleção vale
// para o texto todo (o que a pessoa quer ao escolher uma fonte sem marcar nada), e o tamanho
// poupa os títulos para eles não virarem corpo de texto.
import type { Editor } from "@tiptap/core";

type Atributos = Record<string, string | null>;

export function aplicarNoTexto(editor: Editor, atributos: Atributos, opcoes: { poupaTitulos?: boolean } = {}): void {
  editor
    .chain()
    .focus()
    .command(({ state, tr, dispatch }) => {
      if (!dispatch) return true;
      const marca = state.schema.marks.textStyle;
      if (!marca) return false;

      const faixas: [number, number][] = [];
      if (state.selection.empty) {
        state.doc.descendants((no, posicao) => {
          if (!no.isTextblock) return true;
          if (!(opcoes.poupaTitulos && no.type.name === "heading")) faixas.push([posicao + 1, posicao + no.nodeSize - 1]);
          return false;
        });
      } else {
        faixas.push([state.selection.from, state.selection.to]);
      }

      for (const [de, ate] of faixas) {
        state.doc.nodesBetween(de, ate, (no, posicao) => {
          if (!no.isText) return true;
          const inicio = Math.max(de, posicao);
          const fim = Math.min(ate, posicao + no.nodeSize);
          const atual = no.marks.find((m) => m.type === marca);
          const novos = { ...(atual?.attrs ?? {}), ...atributos };
          const vazio = Object.values(novos).every((valor) => valor === null || valor === undefined);
          if (vazio) tr.removeMark(inicio, fim, marca);
          else tr.addMark(inicio, fim, marca.create(novos));
          return false;
        });
      }
      return true;
    })
    .run();
}
