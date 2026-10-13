// O texto no formato escolhido. É a parte da tela que nunca muda de natureza: a guia, o popup de
// salvar e o Histórico mostram o mesmo componente.
import { useMemo } from "react";
import { dataDeHoje, derivarEstrutura } from "./estrutura";
import type { FormatoDoTexto } from "./formatos";
import VistaArtigo from "./VistaArtigo";
import VistaEmail from "./VistaEmail";
import VistaNewsletter from "./VistaNewsletter";
import VistaSite from "./VistaSite";

const VISTAS = {
  email: VistaEmail,
  newsletter: VistaNewsletter,
  site: VistaSite,
  artigo: VistaArtigo,
} as const;

export default function VistaDoTexto({ formato, html }: { formato: FormatoDoTexto; html: string }) {
  const estrutura = useMemo(() => derivarEstrutura(html), [html]);
  const hoje = useMemo(() => dataDeHoje(), []);
  const Vista = VISTAS[formato];
  return <Vista estrutura={estrutura} hoje={hoje} />;
}
