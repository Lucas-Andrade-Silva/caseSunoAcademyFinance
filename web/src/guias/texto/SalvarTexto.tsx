// O popup de Salvar: pergunta se o texto vai para o Histórico no formato escolhido, com as quatro
// pílulas para trocar, e mostra à direita o texto como ele ficará salvo.
import { useState } from "react";
import Botao from "../../interface/Botao";
import Modal from "../../interface/Modal";
import { Pilulas } from "../../interface/Pilulas";
import { FORMATOS_DO_TEXTO, rotuloDoFormatoDoTexto, type FormatoDoTexto } from "./formatos";
import VistaDoTexto from "./VistaDoTexto";

export default function SalvarTexto({
  html,
  formatoInicial,
  onConfirmar,
  onFechar,
}: {
  html: string;
  formatoInicial: FormatoDoTexto;
  onConfirmar: (formato: FormatoDoTexto) => void;
  onFechar: () => void;
}) {
  const [formato, definirFormato] = useState(formatoInicial);

  const esquerda = (
    <>
      <h2 className="text-[30px] font-normal leading-[1.3]">
        Você deseja salvar este texto como {rotuloDoFormatoDoTexto(formato).toLowerCase()}?
      </h2>
      <Pilulas<FormatoDoTexto>
        className="mt-8"
        rotuloAcessivel="Formato do texto salvo"
        valor={formato}
        onMudar={definirFormato}
        opcoes={FORMATOS_DO_TEXTO}
      />
      <div className="mt-10 flex max-w-[489px] flex-col gap-2.5">
        <Botao variante="claro" tamanho="grande" onClick={() => onConfirmar(formato)}>
          Salvar
        </Botao>
        <Botao variante="escuro" tamanho="grande" onClick={onFechar}>
          Cancelar
        </Botao>
      </div>
    </>
  );

  const direita = (
    <div key={formato} className="surge p-6 lg:p-[50px]">
      <VistaDoTexto formato={formato} html={html} />
    </div>
  );

  return <Modal rotuloAcessivel="Salvar o texto" esquerda={esquerda} direita={direita} onFechar={onFechar} />;
}
