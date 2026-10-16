// A tela da guia Vídeo com o roteiro pronto. À esquerda: as cenas, o estilo (tom e ritmo) e o botão
// Quero o prompt. À direita: o Laudo em barras, o prompt (depois de pedido) e, embaixo, Salvar no
// histórico. Serve tanto à geração desta sessão quanto a um salvo reaberto do Histórico: quem
// chama entrega os roteiros já prontos, e o salvo reaberto vem sem popup nem sessão.
import { useEffect, useMemo, useRef, useState } from "react";
import { editarTextoDaCelula, obterPlanoDeEdicao, type Audiencia, type BlocoFala, type Laudo } from "../../dados/cliente";
import Barras from "../../interface/Barras";
import Botao from "../../interface/Botao";
import { CorpoDaPrevia, Divisao, Ilha, TituloDaGuia, TopoDaPrevia } from "../../interface/Divisao";
import { IconeFechar, IconeMarca, IconeSalvar } from "../../interface/Icones";
import { Pilulas } from "../../interface/Pilulas";
import Vazio from "../../interface/Vazio";
import { usarHistorico } from "../../nucleo/historico";
import { barrasDoLaudo, celulaBloqueada, type BarraDoLaudo } from "../../nucleo/laudo";
import { rotuloAudiencia } from "../../texto/rotulos";
import CartaoDoPrompt from "./CartaoDoPrompt";
import CenasDoRoteiro, { type CamposDaCena } from "./CenasDoRoteiro";
import EscolhaDeJeitos from "./EscolhaDeJeitos";
import { lerAtuacao, type AtuacaoDoPlano } from "./atuacao";
import { montarPrompt } from "./instrucao";
import type { ClimaDoNarrador, RitmoDoNarrador } from "./jeitos";
import { mostrarNaRolagem } from "./rolagem";
import type { DadosDoVideo } from "./salvo";
import { resumoDoRoteiro } from "./tempo";

export interface RoteiroDaAudiencia {
  blocos: readonly BlocoFala[];
  barras: readonly BarraDoLaudo[];
  /** Laudo com Recomendação: o prompt e o salvo ficam bloqueados, como o Pacote no servidor. */
  bloqueado: boolean;
}

interface Propriedades {
  nome: string;
  execucaoId: string | null;
  audiencias: readonly Audiencia[];
  roteiros: Partial<Record<Audiencia, RoteiroDaAudiencia>>;
  /** Presente só quando a tela abre um salvo do Histórico. */
  reaberto?: {
    clima: ClimaDoNarrador | null;
    ritmo: RitmoDoNarrador | null;
    onFechar: () => void;
  };
}

/** O que identifica o que está na tela, para saber se o que a pessoa vê já está salvo. */
function assinatura(
  audiencia: Audiencia,
  clima: ClimaDoNarrador | null,
  ritmo: RitmoDoNarrador | null,
  edicoes = 0,
): string {
  return [audiencia, clima ?? "", ritmo ?? "", edicoes].join("|");
}

export default function TelaDoVideo({ nome, execucaoId, audiencias, roteiros, reaberto }: Propriedades) {
  const { salvar } = usarHistorico();
  const [escolhida, definirEscolhida] = useState<Audiencia>(audiencias[0]);
  const [clima, definirClima] = useState<ClimaDoNarrador | null>(reaberto?.clima ?? null);
  const [ritmo, definirRitmo] = useState<RitmoDoNarrador | null>(reaberto?.ritmo ?? null);
  const [mostrando, definirMostrando] = useState(reaberto !== undefined);
  const [pedidos, definirPedidos] = useState(0);
  const [salvoComo, definirSalvoComo] = useState<string | null>(
    reaberto ? assinatura(audiencias[0], reaberto.clima, reaberto.ritmo) : null,
  );
  // O texto corrigido nas cenas vale no lugar do gerado: o prompt e o salvo saem dele.
  const [editados, definirEditados] = useState<Partial<Record<Audiencia, BlocoFala[]>>>({});
  const [edicoes, definirEdicoes] = useState(0);
  const cartao = useRef<HTMLDivElement>(null);

  const audiencia = audiencias.includes(escolhida) ? escolhida : audiencias[0];
  const roteiro = roteiros[audiencia];
  const blocos = useMemo(() => editados[audiencia] ?? roteiro?.blocos ?? [], [editados, audiencia, roteiro]);
  const textoEditado = editados[audiencia] !== undefined;
  const [laudosNovos, definirLaudosNovos] = useState<Partial<Record<Audiencia, Laudo>>>({});
  const [textoSalvo, definirTextoSalvo] = useState<Partial<Record<Audiencia, boolean>>>({});
  const [salvandoTexto, definirSalvandoTexto] = useState(false);
  const [erroDoTexto, definirErroDoTexto] = useState<string | null>(null);

  async function salvarTexto() {
    if (execucaoId === null) return;
    definirSalvandoTexto(true);
    definirErroDoTexto(null);
    try {
      const novo = await editarTextoDaCelula(execucaoId, audiencia, "roteiro", {
        blocos: blocos.map(({ fala, tela }) => ({ fala, tela })),
      });
      definirLaudosNovos((atuais) => ({ ...atuais, [audiencia]: novo }));
      definirTextoSalvo((atuais) => ({ ...atuais, [audiencia]: true }));
    } catch (erro) {
      definirErroDoTexto(erro instanceof Error ? erro.message : "Não consegui salvar o texto.");
    } finally {
      definirSalvandoTexto(false);
    }
  }

  function editarCena(indice: number, campos: Partial<CamposDaCena>) {
    definirEditados((atuais) => {
      const base = atuais[audiencia] ?? roteiro?.blocos ?? [];
      return { ...atuais, [audiencia]: base.map((bloco, i) => (i === indice ? { ...bloco, ...campos } : bloco)) };
    });
    definirEdicoes((n) => n + 1);
    definirTextoSalvo((atuais) => ({ ...atuais, [audiencia]: false }));
  }
  // Derivado a cada escolha: o prompt na tela nunca fica velho em relação ao estilo marcado.
  // A atuação do avatar vem do plano do servidor (a LLM preenche uma vez por Roteiro e o servidor
  // guarda): olhar, expressão, gesto, entonação, pausas, pronúncia e legendas.
  const [atuacoes, definirAtuacoes] = useState<Partial<Record<Audiencia, AtuacaoDoPlano | null>>>({});
  const [buscandoAtuacao, definirBuscandoAtuacao] = useState(false);
  const atuacao = atuacoes[audiencia] ?? null;
  const instrucao = useMemo(
    () => montarPrompt({ blocos, clima, ritmo, atuacao }),
    [blocos, clima, ritmo, atuacao],
  );

  useEffect(() => {
    if (pedidos === 0) return;
    const reduzido = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (cartao.current) mostrarNaRolagem(cartao.current, !reduzido);
  }, [pedidos]);

  if (!roteiro || blocos.length === 0) {
    return (
      <div className="flex min-h-full items-center justify-center lg:pl-[var(--area-da-rail)]">
        <Vazio titulo="Este roteiro não tem cenas." />
      </div>
    );
  }

  const novoLaudo = laudosNovos[audiencia];
  const barras = novoLaudo ? barrasDoLaudo(novoLaudo) : roteiro.barras;
  const bloqueado = novoLaudo ? celulaBloqueada(novoLaudo) : roteiro.bloqueado;
  const jaSalvo = salvoComo === assinatura(audiencia, clima, ritmo, edicoes);

  async function pedirPrompt() {
    if (execucaoId !== null && !(audiencia in atuacoes)) {
      definirBuscandoAtuacao(true);
      let lida: AtuacaoDoPlano | null = null;
      try {
        lida = lerAtuacao((await obterPlanoDeEdicao(execucaoId, audiencia)).plano);
      } catch {
        lida = null; // sem plano (servidor fora ou Roteiro não aprovado): o prompt sai sem atuação
      } finally {
        definirBuscandoAtuacao(false);
      }
      definirAtuacoes((atuais) => ({ ...atuais, [audiencia]: lida }));
    }
    definirMostrando(true);
    definirPedidos((n) => n + 1);
  }

  function aoSalvar() {
    const dados: DadosDoVideo = { blocos: [...blocos], clima, ritmo, instrucao, barras: [...barras] };
    salvar({
      especie: "video",
      titulo: nome || "Roteiro de vídeo",
      resumo: resumoDoRoteiro(blocos),
      audiencia,
      execucaoId,
      dados,
    });
    definirSalvoComo(assinatura(audiencia, clima, ritmo, edicoes));
  }

  const esquerda = (
    <>
      <TituloDaGuia>Vídeo</TituloDaGuia>
      {audiencias.length > 1 && (
        <div className="mt-6">
          <Pilulas<Audiencia>
            rotuloAcessivel="Audiência"
            valor={audiencia}
            onMudar={definirEscolhida}
            opcoes={audiencias.map((a) => ({ valor: a, rotulo: rotuloAudiencia(a) }))}
          />
        </div>
      )}

      <div className="mt-8">
        <CenasDoRoteiro key={audiencia} blocos={blocos} aoEditar={editarCena} />
        {textoEditado && (
          <div className="mt-4">
            <p className="text-[13px] text-etiqueta">
              {textoSalvo[audiencia]
                ? "Texto salvo e reavaliado: o Laudo ao lado já é o da sua versão."
                : "Texto editado: o prompt já usa a sua versão. Salve para reavaliar o Laudo."}
            </p>
            {execucaoId !== null && !textoSalvo[audiencia] && (
              <div className="mt-3">
                <Botao variante="claro" tamanho="pequeno" disabled={salvandoTexto} onClick={() => void salvarTexto()}>
                  {salvandoTexto ? "Reavaliando…" : "Salvar texto e reavaliar"}
                </Botao>
              </div>
            )}
            {erroDoTexto && (
              <p role="alert" className="mt-3 text-[14px] text-coral-claro">
                {erroDoTexto}
              </p>
            )}
          </div>
        )}
      </div>

      <div className="mt-14">
        <EscolhaDeJeitos clima={clima} ritmo={ritmo} onClima={definirClima} onRitmo={definirRitmo} />
      </div>

      {/* O -bottom-16 desconta o pb-16 da coluna (Divisao): o botão gruda rente à borda da tela. */}
      <div className="sticky bottom-0 mt-10 bg-fundo pb-6 pt-4 before:pointer-events-none before:absolute before:inset-x-0 before:-top-8 before:h-8 before:bg-linear-to-t before:from-fundo before:to-transparent lg:-bottom-16">
        <Botao variante="claro" tamanho="grande" disabled={bloqueado || buscandoAtuacao}
          onClick={() => void pedirPrompt()}
        >
          {buscandoAtuacao ? "Dirigindo o avatar…" : "Quero o prompt"}
        </Botao>
        {bloqueado && (
          <p role="status" className="mt-3 text-[14px] leading-snug text-coral-claro">
            Laudo com Recomendação: sem prompt.
          </p>
        )}
      </div>
    </>
  );

  const direita = (
    <>
      <TopoDaPrevia
        esquerda={
          <Ilha>
            {reaberto ? "Salvo · " : ""}9:16 · {resumoDoRoteiro(blocos)}
          </Ilha>
        }
        direita={
          reaberto && (
            <Botao variante="escuro" tamanho="pequeno" icone={<IconeFechar size={16} />} onClick={reaberto.onFechar}>
              Fechar
            </Botao>
          )
        }
      />
      <CorpoDaPrevia>
        <div className="flex flex-col gap-6">
          {barras.length > 0 ? (
            <Barras barras={barras} />
          ) : (
            !mostrando && <Vazio titulo="Sem laudo." />
          )}
          {mostrando && (
            <div ref={cartao} className="surge">
              <CartaoDoPrompt texto={instrucao} />
            </div>
          )}
        </div>
      </CorpoDaPrevia>
      <div className="flex shrink-0 justify-end px-5 pb-8 pt-3 lg:px-[50px]">
        <Botao
          variante="escuro"
          icone={
            jaSalvo ? <IconeMarca size={18} strokeWidth={2.5} className="text-ok" /> : <IconeSalvar size={18} />
          }
          disabled={bloqueado}
          aria-disabled={jaSalvo || undefined}
          onClick={jaSalvo ? undefined : aoSalvar}
          className={jaSalvo ? "cursor-default hover:bg-superficie!" : ""}
        >
          {jaSalvo ? "Salvo" : "Salvar no histórico"}
        </Botao>
        <span role="status" className="sr-only">
          {jaSalvo ? "Salvo no histórico" : ""}
        </span>
      </div>
    </>
  );

  return <Divisao esquerda={esquerda} direita={direita} />;
}
