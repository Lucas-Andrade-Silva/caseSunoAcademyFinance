// O que o editor entende: texto corrido, títulos até o nível 3, listas, citação, negrito, itálico,
// sublinhado, e a aparência (família, tamanho, cor, alinhamento, distância entre linhas).
import { Extension } from "@tiptap/core";
import TextAlign from "@tiptap/extension-text-align";
import { TextStyleKit } from "@tiptap/extension-text-style";
import StarterKit from "@tiptap/starter-kit";
import { EntreLinhas } from "./EntreLinhas";

export const EXTENSOES: Extension[] = [
  StarterKit.configure({
    heading: { levels: [1, 2, 3] },
    link: false,
    // Sem isso o editor acrescenta um parágrafo vazio no fim, e o HTML salvo deixa de ser o texto.
    trailingNode: false,
  }),
  TextStyleKit.configure({ backgroundColor: false, lineHeight: false }),
  TextAlign.configure({ types: ["heading", "paragraph"] }),
  EntreLinhas,
];
