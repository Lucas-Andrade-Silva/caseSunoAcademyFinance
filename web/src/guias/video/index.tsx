// A guia Vídeo. O fluxo comum cuida do popup, do "Gerando o roteiro…" e da falha; a tela com o
// roteiro pronto vive em `TelaDoVideo`. Um salvo do Histórico entra por aqui direto, sem popup e
// sem precisar de sessão: os blocos vêm no próprio salvo.
import { useEffect, useState } from "react";
import type { Audiencia } from "../../dados/cliente";
import Botao from "../../interface/Botao";
import FluxoDaGuia from "../../interface/FluxoDaGuia";
import Vazio from "../../interface/Vazio";
import { usarHistorico, type Salvo } from "../../nucleo/historico";
import { barrasDoLaudo, celulaBloqueada } from "../../nucleo/laudo";
import type { Sessao } from "../../nucleo/sessao";
import { lerDadosDoVideo, type DadosDoVideo } from "./salvo";
import TelaDoVideo, { type RoteiroDaAudiencia } from "./TelaDoVideo";

interface SalvoAberto {
  salvo: Salvo;
  dados: DadosDoVideo;
}

function roteirosDaSessao(sessao: Sessao): Partial<Record<Audiencia, RoteiroDaAudiencia>> {
  const roteiros: Partial<Record<Audiencia, RoteiroDaAudiencia>> = {};
  for (const audiencia of sessao.audiencias) {
    const celula = sessao.celulas[audiencia];
    if (!celula) continue;
    roteiros[audiencia] = {
      blocos: celula.conteudo.blocos ?? [],
      barras: barrasDoLaudo(celula.laudo),
      bloqueado: celulaBloqueada(celula.laudo),
    };
  }
  return roteiros;
}

export default function GuiaVideo() {
  const { paraAbrir, consumirAbertura } = usarHistorico();
  const [aberto, definirAberto] = useState<SalvoAberto | null>(null);
  const [ilegivel, definirIlegivel] = useState(false);

  useEffect(() => {
    if (paraAbrir?.especie !== "video") return;
    const dados = lerDadosDoVideo(paraAbrir.dados);
    definirAberto(dados ? { salvo: paraAbrir, dados } : null);
    definirIlegivel(dados === null);
    consumirAbertura();
  }, [paraAbrir, consumirAbertura]);

  if (aberto) {
    const { salvo, dados } = aberto;
    return (
      <TelaDoVideo
        key={salvo.id}
        nome={salvo.titulo}
        execucaoId={salvo.execucaoId}
        audiencias={[salvo.audiencia]}
        roteiros={{ [salvo.audiencia]: { blocos: dados.blocos, barras: dados.barras, bloqueado: false } }}
        reaberto={{ clima: dados.clima, ritmo: dados.ritmo, onFechar: () => definirAberto(null) }}
      />
    );
  }

  if (ilegivel) {
    return (
      <div className="flex min-h-full items-center justify-center lg:pl-[var(--area-da-rail)]">
        <Vazio
          tom="coral"
          titulo="Não consegui abrir este salvo."
          acao={
            <Botao variante="claro" tamanho="pequeno" onClick={() => definirIlegivel(false)}>
              Fechar
            </Botao>
          }
        />
      </div>
    );
  }

  return (
    <FluxoDaGuia formato="roteiro" rotuloGerando="Gerando o roteiro…">
      {(sessao) => (
        <TelaDoVideo
          key={sessao.execucaoId ?? "sessao"}
          nome={sessao.nome}
          execucaoId={sessao.execucaoId}
          audiencias={sessao.audiencias}
          roteiros={roteirosDaSessao(sessao)}
        />
      )}
    </FluxoDaGuia>
  );
}
