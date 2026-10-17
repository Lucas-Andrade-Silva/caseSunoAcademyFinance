// A prévia de um vídeo salvo, na área escura do Histórico: o prompt (com o botão de copiar), o
// Laudo de quando foi salvo e as cenas do roteiro.
import { TituloDeSecao } from "../../interface/Divisao";
import Barras from "../../interface/Barras";
import Vazio from "../../interface/Vazio";
import type { Salvo } from "../../nucleo/historico";
import { rotuloAudiencia } from "../../texto/rotulos";
import CartaoDoPrompt from "./CartaoDoPrompt";
import CenasDoRoteiro from "./CenasDoRoteiro";
import { rotuloDosJeitos } from "./jeitos";
import { lerDadosDoVideo } from "./salvo";

export default function PreviaSalva({ salvo }: { salvo: Salvo }) {
  const dados = lerDadosDoVideo(salvo.dados, salvo.audiencia);
  if (!dados) return <Vazio tom="coral" titulo="Não consegui ler este salvo." />;

  const detalhes = [rotuloAudiencia(salvo.audiencia), salvo.resumo, rotuloDosJeitos(dados.clima, dados.ritmo)];
  return (
    <div className="mx-auto max-w-[620px]">
      <h2 className="text-[24px] font-normal leading-tight">{salvo.titulo}</h2>
      <p className="mt-2 text-[14px] text-etiqueta">{detalhes.filter(Boolean).join(" · ")}</p>

      <div className="mt-8 flex flex-col gap-6">
        {dados.laudo?.destino === "aprovado"
          ? <CartaoDoPrompt texto={dados.instrucao} />
          : <Vazio titulo="Rascunho: reabra e reavalie antes de copiar o prompt." />}
        <Barras barras={dados.barras} />
      </div>

      <div className="mt-12">
        <TituloDeSecao>Roteiro</TituloDeSecao>
        <div className="mt-6">
          <CenasDoRoteiro blocos={dados.blocos} />
        </div>
      </div>
    </div>
  );
}
