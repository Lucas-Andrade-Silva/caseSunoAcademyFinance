// O plano de edição de um Roteiro aprovado, para quem vai produzir o vídeo: o JSON para colar num
// gerador de avatar sintético e a tabela legível da edição. O plano é montado no servidor a
// partir do Roteiro (nenhuma informação nova nasce aqui) e só existe para Roteiro aprovado.
import { useState } from "react";
import {
  mensagemDeFalha,
  obterPlanoDeEdicao,
  type Audiencia,
  type PlanoDeEdicao,
} from "../dados/cliente";

type Estado = "parado" | "carregando" | "copiado" | "erro";

export default function PainelDoPlano({
  identificador,
  audiencia,
}: {
  identificador: string;
  audiencia: Audiencia;
}) {
  const [estado, definirEstado] = useState<Estado>("parado");
  const [detalhe, definirDetalhe] = useState<string>("");

  async function copiar(extrair: (plano: PlanoDeEdicao) => string, rotulo: string) {
    definirEstado("carregando");
    try {
      const plano = await obterPlanoDeEdicao(identificador, audiencia);
      await navigator.clipboard.writeText(extrair(plano));
      definirDetalhe(rotulo);
      definirEstado("copiado");
    } catch (falha) {
      definirDetalhe(mensagemDeFalha(falha));
      definirEstado("erro");
    }
  }

  const ocupado = estado === "carregando";
  const botao =
    "rounded-full border border-[#55555b] px-4 py-1.5 text-xs font-semibold hover:border-texto disabled:cursor-not-allowed disabled:opacity-40";

  return (
    <div className="mt-3 rounded-xl border border-linha p-3">
      <p className="text-[12.5px] font-bold">Plano de edição</p>
      <p className="mt-0.5 text-[11px] text-suave">
        Cena a cena: o que o avatar fala, o que aparece escrito, ícone, transição, efeito e sons,
        com os tempos e o design system. Cole o JSON no gerador de vídeo com avatar.
      </p>
      <div className="mt-2 flex flex-wrap items-center gap-2">
        <button
          type="button"
          disabled={ocupado}
          className={botao}
          onClick={() =>
            copiar((p) => JSON.stringify(p.plano, null, 2), "JSON copiado para a área de transferência.")
          }
        >
          Copiar JSON para avatar
        </button>
        <button
          type="button"
          disabled={ocupado}
          className={botao}
          onClick={() => copiar((p) => p.markdown, "Tabela copiada para a área de transferência.")}
        >
          Copiar tabela
        </button>
        <span role="status" className="text-[11px] text-suave">
          {estado === "carregando" && "Montando o plano…"}
          {estado === "copiado" && detalhe}
        </span>
      </div>
      {estado === "erro" && (
        <p role="alert" className="mt-2 text-[11.5px] text-[#ffb3ad]">
          Não foi possível copiar o plano: {detalhe}
        </p>
      )}
    </div>
  );
}
