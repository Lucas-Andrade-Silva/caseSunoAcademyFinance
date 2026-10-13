// A prévia de um carrossel salvo, para o Histórico: o carrossel dentro do celular de feed, com a paleta
// e a composição que a pessoa tinha escolhido. Tudo vem do próprio salvo, sem rede.
import { useMemo } from "react";
import Vazio from "../../interface/Vazio";
import type { Salvo } from "../../nucleo/historico";
import { rotuloAudiencia } from "../../texto/rotulos";
import Celular from "./Celular";
import { rotuloDaComposicao } from "./composicoes";
import { lerDadosSalvos, type DadosDoCarrossel } from "./dadosSalvos";
import { quadrosDaMontagem } from "./montagem";
import Quadro from "./Quadro";

function Carrossel({ salvo, dados }: { salvo: Salvo; dados: DadosDoCarrossel }) {
  const nos = useMemo(
    () =>
      quadrosDaMontagem(dados).map((quadro) => (
        <Quadro key={quadro.indice} quadro={quadro} paleta={dados.paleta} selo={rotuloAudiencia(salvo.audiencia)} />
      )),
    [dados, salvo.audiencia],
  );
  return (
    <div className="flex flex-col items-center gap-4 py-2">
      <Celular quadros={nos} legenda={dados.slides[0]?.titulo ?? salvo.titulo} rotuloAcessivel={salvo.titulo} />
      <p className="text-[12px] font-medium uppercase tracking-[0.02em] text-etiqueta">
        {rotuloDaComposicao(dados.composicao)} · {dados.paleta.nome}
      </p>
    </div>
  );
}

export default function PreviaSalva({ salvo }: { salvo: Salvo }) {
  const dados = useMemo(() => lerDadosSalvos(salvo.dados), [salvo.dados]);
  if (!dados) return <Vazio tom="coral" titulo="Este carrossel salvo está incompleto." />;
  return <Carrossel salvo={salvo} dados={dados} />;
}
