// O texto dentro dos formatos. O HTML vem do `marked` (que aqui não deixa passar HTML cru nem
// link) ou do Tiptap (que só escreve o que o esquema dele conhece), então entra como está.
// A aparência que a pessoa deu a um título (alinhamento, fonte) acompanha o título.
import type { ElementType } from "react";
import { aparenciaDosAtributos, type Bloco } from "./estrutura";
import "./texto.css";

export default function TrechoHtml({ blocos, className = "" }: { blocos: readonly Bloco[]; className?: string }) {
  if (blocos.length === 0) return null;
  return (
    <div
      className={`corpo-do-texto ${className}`}
      dangerouslySetInnerHTML={{ __html: blocos.map((bloco) => bloco.html).join("") }}
    />
  );
}

export function TituloHtml({
  como: Etiqueta,
  html,
  atributos,
  className = "",
}: {
  como: ElementType;
  html: string;
  atributos: string;
  className?: string;
}) {
  return (
    <Etiqueta
      className={className}
      style={aparenciaDosAtributos(atributos)}
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}
