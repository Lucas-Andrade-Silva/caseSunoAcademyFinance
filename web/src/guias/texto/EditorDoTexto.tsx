// O editor: barra de ferramentas e a superfície de escrita. Escreve o HTML do texto e avisa a
// cada mudança; quem decide quando aquilo vira o texto final é o botão "Salvar edição" da guia.
import { EditorContent, useEditor } from "@tiptap/react";
import { useRef } from "react";
import BarraDoEditor from "./BarraDoEditor";
import { EXTENSOES } from "./extensoes";

interface Propriedades {
  /** O HTML com que o editor abre. Só vale na criação: para trocar o texto, troque a `key`. */
  inicial: string;
  /** O HTML como o editor o escreve, logo que ele abre: a base para saber se algo mudou. */
  aoCriar: (html: string) => void;
  aoMudar: (html: string) => void;
}

export default function EditorDoTexto({ inicial, aoCriar, aoMudar }: Propriedades) {
  const ouvintes = useRef({ aoCriar, aoMudar });
  ouvintes.current = { aoCriar, aoMudar };

  const editor = useEditor({
    extensions: EXTENSOES,
    content: inicial,
    editorProps: {
      attributes: { class: "texto-escrita", role: "textbox", "aria-multiline": "true", "aria-label": "Texto" },
    },
    onCreate: ({ editor: criado }) => ouvintes.current.aoCriar(criado.getHTML()),
    onUpdate: ({ editor: atual }) => ouvintes.current.aoMudar(atual.getHTML()),
  });

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-4">
      <BarraDoEditor editor={editor} />
      <div className="texto-superficie min-h-[320px] flex-1 overflow-y-auto rounded-xl bg-superficie">
        <EditorContent editor={editor} />
      </div>
    </div>
  );
}
