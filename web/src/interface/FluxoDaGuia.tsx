// O que as três guias de conteúdo têm em comum, na ordem em que a pessoa vive:
//   vazia     → o popup de confirmação (notícias + audiências);
//   enviando/gerando → o carregamento "Gerando…";
//   falhou    → a frase do problema e a saída;
//   pronta    → a guia mostra o conteúdo (`children`).
// Cada guia só escreve o que é dela, o conteúdo pronto.
import type { ReactNode } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import type { Audiencia, Formato } from "../dados/cliente";
import { guiaDoFormato } from "../nucleo/guias";
import type { ExtrasDaGeracao } from "../nucleo/pedido";
import { usarSessao, type Sessao } from "../nucleo/sessao";
import Botao from "./Botao";
import ConfirmarNoticias from "./ConfirmarNoticias";
import Gerando from "./Gerando";
import Vazio from "./Vazio";

interface Propriedades {
  formato: Formato;
  /** A frase do carregamento: "Gerando o texto…". */
  rotuloGerando: string;
  /** Extras que o pedido leva para o servidor (duração do vídeo, design do carrossel). */
  extras?: ExtrasDaGeracao;
  children: (sessao: Sessao) => ReactNode;
}

export default function FluxoDaGuia({ formato, rotuloGerando, extras, children }: Propriedades) {
  const sessao = usarSessao(formato);
  const navegar = useNavigate();
  const { pathname } = useLocation();
  // O popup sai por um portal e não é escondido com a vista: só abre na guia que está na tela.
  const naTela = pathname === guiaDoFormato(formato).caminho;

  if (sessao.fase === "pronta") return <>{children(sessao)}</>;

  // Retomando uma Saída depois de recarregar: não há o que mostrar até o servidor responder.
  if (sessao.fase === "enviando" && sessao.execucaoId) return null;

  if (sessao.fase === "enviando" || sessao.fase === "gerando") {
    return (
      <div className="flex min-h-full items-center justify-center px-5 lg:pl-[var(--area-da-rail)]">
        <Gerando rotulo={rotuloGerando} andamento={sessao.andamento} audiencias={sessao.audiencias} />
      </div>
    );
  }

  if (sessao.fase === "falhou") {
    return (
      <div className="flex min-h-full items-center justify-center lg:pl-[var(--area-da-rail)]">
        <Vazio
          tom="coral"
          titulo={sessao.erro ?? "A geração não terminou."}
          acao={
            <div className="flex gap-3">
              <Botao variante="escuro" tamanho="pequeno" onClick={() => navegar("/ingestao")}>
                Ingestão
              </Botao>
              <Botao variante="claro" tamanho="pequeno" onClick={sessao.limpar}>
                Tentar de novo
              </Botao>
            </div>
          }
        />
      </div>
    );
  }

  if (!naTela) return null;
  return (
    <ConfirmarNoticias
      onVoltar={() => navegar("/ingestao")}
      onConfirmar={(audiencias: Audiencia[]) => void sessao.iniciar(audiencias, extras)}
    />
  );
}
