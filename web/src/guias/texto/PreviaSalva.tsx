// A prévia de um texto salvo no Histórico: o HTML guardado, no formato em que foi salvo.
import Vazio from "../../interface/Vazio";
import type { Salvo } from "../../nucleo/historico";
import { lerDados } from "./formatos";
import VistaDoTexto from "./VistaDoTexto";

export default function PreviaSalva({ salvo }: { salvo: Salvo }) {
  const dados = lerDados(salvo.dados);
  if (!dados) return <Vazio tom="coral" titulo="Este texto não abre mais." />;
  return <VistaDoTexto formato={dados.formato} html={dados.html} />;
}
