// O popup que abre as guias Texto, Carrossel e Vídeo: confirma as notícias guardadas na Ingestão
// (à direita) e pergunta para quais audiências gerar (à esquerda). Voltar leva de volta à
// Ingestão. A geração só começa quando a pessoa confirma.
import { useState } from "react";
import { AUDIENCIAS, type Audiencia } from "../dados/cliente";
import { usarConfiguracoes } from "../nucleo/configuracoes";
import { motivoDeRecusa } from "../nucleo/pedido";
import { usarSelecao } from "../nucleo/selecao";
import { rotuloAudiencia } from "../texto/rotulos";
import Botao from "./Botao";
import CartaoDeNoticia from "./CartaoDeNoticia";
import { IconeMarca, IconeNivel1, IconeNivel2, IconeNivel3 } from "./Icones";
import { Quadrado, type CorDoQuadrado } from "./Linha";
import Modal from "./Modal";

const DA_AUDIENCIA: Record<Audiencia, { cor: CorDoQuadrado; icone: React.ReactNode }> = {
  iniciante: { cor: "verde", icone: <IconeNivel1 size={20} /> },
  intermediario: { cor: "amarelo", icone: <IconeNivel2 size={20} /> },
  avancado: { cor: "coral", icone: <IconeNivel3 size={20} /> },
};

export default function ConfirmarNoticias({
  onConfirmar,
  onVoltar,
}: {
  onConfirmar: (audiencias: Audiencia[]) => void;
  onVoltar: () => void;
}) {
  const { atasGuardadas, guardada } = usarSelecao();
  const { modo } = usarConfiguracoes();
  const [marcadas, definirMarcadas] = useState<Audiencia[]>([]);

  // As notícias guardadas ainda não chegaram do servidor (abertura direta desta guia): sem pergunta
  // errada na tela até lá.
  if (guardada.length > 0 && atasGuardadas.length === 0) return null;

  const semNoticias = atasGuardadas.length === 0;
  const audiencias = AUDIENCIAS.filter((a) => marcadas.includes(a));
  const motivo = motivoDeRecusa({ atas: atasGuardadas, modo, audiencias });

  function alternar(audiencia: Audiencia) {
    definirMarcadas((atuais) =>
      atuais.includes(audiencia) ? atuais.filter((a) => a !== audiencia) : [...atuais, audiencia],
    );
  }

  const esquerda = semNoticias ? (
    <>
      <h2 className="text-[30px] font-normal leading-[1.3]">Nenhuma notícia selecionada.</h2>
      <div className="mt-10 max-w-[489px]">
        <Botao variante="claro" tamanho="grande" onClick={onVoltar}>
          Ir para a Ingestão
        </Botao>
      </div>
    </>
  ) : (
    <>
      <h2 className="text-[30px] font-normal leading-[1.3]">
        Você deseja utilizar essas notícias para gerar o seu conteúdo?
      </h2>
      <ul className="mt-10 flex max-w-[489px] flex-col gap-2.5">
        {AUDIENCIAS.map((audiencia) => {
          const marcada = marcadas.includes(audiencia);
          const { cor, icone } = DA_AUDIENCIA[audiencia];
          return (
            <li key={audiencia}>
              <button
                type="button"
                role="checkbox"
                aria-checked={marcada}
                onClick={() => alternar(audiencia)}
                className={`flex h-[70px] w-full items-center gap-4 rounded-lg px-[21px] text-left transition-colors duration-150 ${
                  marcada ? "bg-superficie-alta" : "bg-superficie hover:bg-superficie-alta"
                }`}
              >
                <Quadrado cor={cor}>{icone}</Quadrado>
                <span className="flex-1 text-[17px]">{rotuloAudiencia(audiencia)}</span>
                <span
                  className={`grid h-6 w-6 place-items-center rounded-full border transition-colors duration-150 ${
                    marcada ? "border-white bg-white text-ilha" : "border-[#555] text-transparent"
                  }`}
                >
                  <IconeMarca size={15} strokeWidth={2.5} />
                </span>
              </button>
            </li>
          );
        })}
      </ul>
      <div className="mt-6 flex max-w-[489px] flex-col gap-2.5">
        <Botao
          variante="claro"
          tamanho="grande"
          disabled={motivo !== null}
          onClick={() => onConfirmar(audiencias)}
        >
          Gerar
        </Botao>
        {audiencias.length > 0 && motivo && (
          <p role="alert" className="text-[14px] leading-snug text-coral-claro">
            {motivo}
          </p>
        )}
        <Botao variante="escuro" tamanho="grande" onClick={onVoltar}>
          Voltar
        </Botao>
      </div>
    </>
  );

  const direita = semNoticias ? null : (
    <div className="flex flex-col gap-3 p-6 lg:p-[50px]">
      {atasGuardadas.map((ata) => (
        <CartaoDeNoticia key={ata.identificador} ata={ata} />
      ))}
    </div>
  );

  return <Modal rotuloAcessivel="Confirmar as notícias" esquerda={esquerda} direita={direita} />;
}
