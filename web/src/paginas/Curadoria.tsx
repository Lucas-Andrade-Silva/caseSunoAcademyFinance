// A guia Curadoria ("/curadoria"): escolher o que entra, configurar e gerar, em três passos
// (spec do front, seção 4.2). O passo 3 vive na URL (`?saida=<id>`): dá para sair da tela e
// voltar, a geração continua no servidor.
import { useEffect, useState, type ReactNode } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import {
  criarSaida,
  listarReferenciasVisuais,
  listarOrigens,
  obterResumo,
  obterSaude,
  obterSugestoes,
  type Audiencia,
  type DuracaoDoVideo,
  type Formato,
  type ModoDeGeracao,
  type OrigemComAtas,
  type ReferenciaVisual,
  type ResumoDaAta,
  type Sugestao,
} from "../dados/cliente";
import { mensagemDeFalha } from "../dados/cliente";
import { usarRequisicao } from "../ganchos/usarRequisicao";
import { usarSelecaoDeAtas } from "../ganchos/SelecaoDeAtas";
import { Carregando, MensagemErro } from "../componentes/EstadoRequisicao";
import Chip from "../componentes/Chip";
import MatrizAoVivo from "../componentes/MatrizAoVivo";
import SeletorDeMatriz from "../componentes/SeletorDeMatriz";
import {
  dataDoDia,
  nomePadrao,
  podeUsarSelecao,
  seloDaAta,
  type ModoDaEscolha,
} from "../lib/fontes";
import { matrizInteira, resumirPedido, type Posicao } from "../lib/pedido";
import { rotuloDaComposicao } from "../lib/pacote";
import { DURACOES } from "../texto/rotulos";

const BOTAO_PRIMARIO =
  "rounded-full bg-suno px-5 py-2 text-xs font-bold uppercase tracking-wide text-white disabled:cursor-not-allowed disabled:opacity-40";
const BOTAO_SECUNDARIO =
  "rounded-full border border-[#55555b] px-4 py-2 text-xs font-semibold hover:border-texto";

type Passo = 1 | 2 | 3;

const COMPOSICOES_VISUAIS: ReferenciaVisual["composicao"][] = [
  "editorial",
  "minimalista",
  "infografico",
  "comparativo",
  "estatistico",
  "narrativo",
];

/** O que o passo 1 entrega ao passo 2: um Destaque único (uma Ata) ou uma Visão unida (2 a 5). */
interface Escolha {
  modo: ModoDaEscolha;
  atas: ResumoDaAta[];
}

function Passos({ atual }: { atual: Passo }) {
  const nomes = ["Escolher", "Configurar", "Gerando"] as const;
  return (
    <ol className="flex gap-6">
      {nomes.map((nome, indice) => {
        const numero = (indice + 1) as Passo;
        const feito = numero < atual;
        const ativo = numero === atual;
        return (
          <li
            key={nome}
            aria-current={ativo ? "step" : undefined}
            className={`flex items-center gap-2 border-b-[3px] pb-2 pt-1.5 text-[13px] font-semibold ${
              ativo ? "border-suno text-texto" : "border-transparent text-suave"
            }`}
          >
            <span
              className={`flex h-[19px] w-[19px] items-center justify-center rounded-full border-[1.5px] text-[10.5px] ${
                ativo
                  ? "border-suno bg-suno text-white"
                  : feito
                    ? "border-ok bg-ok text-fundo"
                    : "border-[#4a4a50]"
              }`}
            >
              {feito ? "✓" : numero}
            </span>
            {nome}
          </li>
        );
      })}
    </ol>
  );
}

function Moldura({
  titulo,
  passo,
  rodape,
  children,
}: {
  titulo: string;
  passo: Passo;
  rodape: ReactNode;
  children: ReactNode;
}) {
  return (
    <div className="flex min-h-screen flex-col">
      <header className="border-b border-linha px-5 pt-3">
        <h1 className="mb-2 text-[17px] font-bold">{titulo}</h1>
        <Passos atual={passo} />
      </header>
      <div className="flex-1 px-5 py-4">{children}</div>
      <footer className="sticky bottom-0 flex flex-wrap items-center gap-2.5 border-t border-linha bg-lateral px-5 py-2.5">
        {rodape}
      </footer>
    </div>
  );
}

const NOTA_DA_CURADORIA =
  "A curadoria sugere pauta de conteúdo. Nunca sugere ativo para comprar ou vender.";

// ---------------------------------------------------------------- passo 1

function LinhaDeAta({ ata, origem }: { ata: ResumoDaAta; origem: string }) {
  const selo = seloDaAta(ata.categoria);
  return (
    <div className="flex flex-wrap items-center gap-2 rounded-[10px] bg-cartao-2 px-2.5 py-2">
      <Chip tom="forte">{origem}</Chip>
      <strong className="min-w-0 flex-1 text-xs">{ata.titulo}</strong>
      {selo && <Chip tom="alerta">{selo}</Chip>}
      <span className="text-[10.5px] text-suave">{dataDoDia(ata.data_referencia)}</span>
    </div>
  );
}

function CartaoDeSugestao({
  titulo,
  chip,
  sugestao,
  nomeDaOrigem,
  vazio,
  explicacao,
  destaque,
  acao,
  onUsar,
}: {
  titulo: string;
  chip: string;
  sugestao: Sugestao | null;
  nomeDaOrigem: (origem: string) => string;
  vazio: ReactNode;
  explicacao: string;
  destaque: boolean;
  acao: string;
  onUsar: (atas: ResumoDaAta[]) => void;
}) {
  return (
    <section
      aria-label={titulo}
      className={`flex flex-col gap-2 rounded-[14px] bg-cartao p-3.5 ${
        destaque ? "border border-suno/50" : "border border-transparent"
      }`}
    >
      <h2 className="flex items-center gap-2 text-sm font-bold">
        {titulo}
        {sugestao && <Chip tom={destaque ? "ok" : "neutro"}>{chip}</Chip>}
      </h2>
      {sugestao ? (
        <>
          {sugestao.itens.map((ata) => (
            <LinhaDeAta key={ata.identificador} ata={ata} origem={nomeDaOrigem(ata.origem)} />
          ))}
          <p className="text-[11.5px] text-suave">{sugestao.motivo}</p>
          <p className="text-[11.5px] text-suave">{explicacao}</p>
          <div className="flex-1" />
          <button
            type="button"
            onClick={() => onUsar(sugestao.itens)}
            className={destaque ? BOTAO_PRIMARIO : BOTAO_SECUNDARIO}
          >
            {acao}
          </button>
        </>
      ) : (
        <p className="text-[12.5px] text-suave">{vazio}</p>
      )}
    </section>
  );
}

function PassoEscolher({
  destaque,
  unida,
  origens,
  onUsar,
}: {
  destaque: Sugestao | null;
  unida: Sugestao | null;
  origens: OrigemComAtas[];
  onUsar: (escolha: Escolha) => void;
}) {
  const { selecao } = usarSelecaoDeAtas();
  const todas = origens.flatMap((origem) => origem.atas);
  const marcadas = todas.filter((ata) => selecao.includes(ata.identificador));
  const nomeDaOrigem = (id: string) => origens.find((o) => o.id === id)?.nome ?? id;
  const pode = podeUsarSelecao(marcadas.map((ata) => ata.identificador));
  const aviso = (
    <>
      Ligue uma fonte ou importe um documento na guia{" "}
      <Link to="/fontes" className="font-semibold text-suno hover:underline">
        Fontes
      </Link>
      .
    </>
  );

  return (
    <Moldura
      titulo="Sugestão da curadoria"
      passo={1}
      rodape={<span className="text-xs text-suave">{NOTA_DA_CURADORIA}</span>}
    >
      <div className="grid max-w-4xl gap-3.5 lg:grid-cols-2">
        <CartaoDeSugestao
          titulo="Destaque único"
          chip="mais recente"
          sugestao={destaque}
          nomeDaOrigem={nomeDaOrigem}
          vazio={<>Nenhum item nas fontes ligadas. {aviso}</>}
          explicacao="Uma única fonte: todas as Células citam os mesmos fatos."
          destaque
          acao="Usar este destaque"
          onUsar={(atas) => onUsar({ modo: "destaque", atas })}
        />
        <CartaoDeSugestao
          titulo="Visão unida"
          chip={`${unida?.itens.length ?? 0} itens`}
          sugestao={unida}
          nomeDaOrigem={nomeDaOrigem}
          vazio={<>A Visão unida precisa de ao menos dois itens que consigam gerar. {aviso}</>}
          explicacao="Só no modo Real: a Demo não tem respostas prontas para uma combinação de Atas."
          destaque={false}
          acao="Usar esta visão"
          onUsar={(atas) => onUsar({ modo: "unida", atas })}
        />
      </div>

      <section className="mt-3.5 flex max-w-4xl flex-wrap items-center gap-3 rounded-[13px] border border-dashed border-[#44444a] px-3.5 py-3 text-sm text-suave">
        <b className="text-texto">Montar a minha</b>
        <span className="min-w-0 flex-1 text-[12.5px]">
          {marcadas.length === 0
            ? "Escolha os itens nas Fontes (bolinhas dos cartões) e volte aqui."
            : (pode.motivo ?? marcadas.map((ata) => ata.titulo).join(" · "))}
        </span>
        <Chip>
          {marcadas.length} {marcadas.length === 1 ? "selecionado" : "selecionados"}
        </Chip>
        <Link to="/fontes" className={BOTAO_SECUNDARIO}>
          Ir às Fontes
        </Link>
        <button
          type="button"
          disabled={!pode.ok}
          onClick={() => pode.modo && onUsar({ modo: pode.modo, atas: marcadas })}
          className={BOTAO_SECUNDARIO + " disabled:cursor-not-allowed disabled:opacity-40"}
        >
          {marcadas.length > 1 ? "Usar selecionados" : "Usar selecionado"}
        </button>
      </section>
    </Moldura>
  );
}

// ---------------------------------------------------------------- passo 2

/** A duração do Roteiro, e portanto do vídeo: as cinco opções, em segundos de fala. */
function SeletorDeDuracao({
  valor,
  onMudar,
  desabilitado,
}: {
  valor: DuracaoDoVideo;
  onMudar: (duracao: DuracaoDoVideo) => void;
  desabilitado: boolean;
}) {
  return (
    <div className="mt-4">
      <p className="mb-1.5 text-[10.5px] font-bold uppercase tracking-wider text-suave">
        Duração do vídeo
      </p>
      <div role="radiogroup" aria-label="Duração do vídeo" className="flex flex-wrap gap-2">
        {DURACOES.map((opcao) => (
          <button
            key={opcao.valor}
            type="button"
            role="radio"
            aria-checked={valor === opcao.valor}
            disabled={desabilitado}
            onClick={() => onMudar(opcao.valor)}
            className={`rounded-full border px-4 py-1.5 text-xs font-semibold disabled:opacity-40 ${
              valor === opcao.valor
                ? "border-suno bg-suno/15 text-texto"
                : "border-[#55555b] text-suave hover:border-texto"
            }`}
          >
            {opcao.rotulo}
          </button>
        ))}
      </div>
      <p className="mt-1.5 text-[11px] text-suave">
        O Roteiro é escrito para caber nesse tempo: cerca de 150 palavras por minuto de fala.
      </p>
    </div>
  );
}

function OpcaoDeModo({
  titulo,
  descricao,
  marcada,
  desabilitada,
  onEscolher,
}: {
  titulo: string;
  descricao: string;
  marcada: boolean;
  desabilitada: boolean;
  onEscolher: () => void;
}) {
  return (
    <button
      type="button"
      role="radio"
      aria-checked={marcada}
      disabled={desabilitada}
      onClick={onEscolher}
      className={`rounded-xl border-[1.5px] bg-cartao p-3 text-left disabled:cursor-not-allowed disabled:opacity-50 ${
        marcada && !desabilitada ? "border-suno bg-suno/10" : "border-linha"
      }`}
    >
      <b className="block text-[12.5px]">{titulo}</b>
      <small className="text-[11px] text-suave">{descricao}</small>
    </button>
  );
}

function ConfiguracaoVisual({
  referencias,
  composicao,
  referencia,
  desabilitada,
  onComposicao,
  onReferencia,
}: {
  referencias: ReferenciaVisual[];
  composicao: ReferenciaVisual["composicao"];
  referencia: string;
  desabilitada: boolean;
  onComposicao: (valor: ReferenciaVisual["composicao"]) => void;
  onReferencia: (valor: string) => void;
}) {
  const estilos = referencias.filter(
    (item) => item.aprovada && item.composicao === composicao,
  );
  const escolhido = estilos.find((item) => item.identificador === referencia);
  return (
    <section className="mt-6 rounded-xl border border-linha bg-cartao p-4">
      <div className="flex flex-wrap items-start gap-3">
        <div className="min-w-[240px] flex-1">
          <h2 className="text-sm font-bold">Direção visual do Carrossel</h2>
          <p className="mt-1 text-[11px] leading-relaxed text-suave">
            Escolha a família de composição e um exemplo aprovado da sua biblioteca. O
            conteúdo continua vindo da fonte selecionada; a referência orienta somente o design.
          </p>
        </div>
        <Link to="/referencias" className={BOTAO_SECUNDARIO}>
          Configurar exemplos
        </Link>
      </div>
      <p className="mb-1.5 mt-4 text-[10.5px] font-bold uppercase tracking-wider text-suave">
        Tipo de referência visual
      </p>
      <div role="radiogroup" aria-label="Tipo de referência visual" className="flex flex-wrap gap-2">
        {COMPOSICOES_VISUAIS.map((item) => (
          <button
            key={item}
            type="button"
            role="radio"
            aria-checked={composicao === item}
            disabled={desabilitada}
            onClick={() => onComposicao(item)}
            className={`rounded-full border px-3 py-1.5 text-xs font-semibold disabled:opacity-40 ${
              composicao === item
                ? "border-suno bg-suno/15 text-texto"
                : "border-[#55555b] text-suave hover:border-texto"
            }`}
          >
            {rotuloDaComposicao(item)}
          </button>
        ))}
      </div>
      <label className="mt-4 grid gap-1 text-xs md:max-w-xl">
        Estilo de design
        <select
          value={referencia}
          disabled={desabilitada || estilos.length === 0}
          onChange={(evento) => onReferencia(evento.target.value)}
          className="rounded-lg border border-linha bg-fundo px-3 py-2"
        >
          {estilos.length === 0 && <option value="">Nenhum exemplo aprovado</option>}
          {estilos.map((item) => (
            <option key={item.identificador} value={item.identificador}>
              {item.titulo}
            </option>
          ))}
        </select>
      </label>
      {escolhido && (
        <p className="mt-2 max-w-3xl text-[11px] leading-relaxed text-suave">
          <b className="text-texto">{escolhido.titulo}:</b> {escolhido.descricao}
        </p>
      )}
      {estilos.length === 0 && (
        <p role="alert" className="mt-2 text-[11px] text-[#ffb3ad]">
          Aprove um exemplo desta composição na Configuração visual para continuar.
        </p>
      )}
    </section>
  );
}

function PassoConfigurar({
  escolha,
  realDisponivel,
  onVoltar,
  onGerada,
}: {
  escolha: Escolha;
  realDisponivel: boolean;
  onVoltar: () => void;
  onGerada: (identificador: string) => void;
}) {
  const unida = escolha.modo === "unida";
  const demoDisponivel = !unida && escolha.atas[0].demo_disponivel;
  const extracaoCompleta = escolha.atas.every((ata) => ata.extracao_completa);
  const semCalibrar = escolha.atas.some((ata) => seloDaAta(ata.categoria) !== null);

  const [nome, definirNome] = useState(nomePadrao(escolha.atas.map((ata) => ata.titulo)));
  const [modo, definirModo] = useState<ModoDeGeracao>(
    demoDisponivel || !realDisponivel ? "demo" : "real",
  );
  const [selecao, definirSelecao] = useState<Posicao[]>(matrizInteira());
  const [duracao, definirDuracao] = useState<DuracaoDoVideo>("60");
  const referencias = usarRequisicao(listarReferenciasVisuais, []);
  const [composicaoVisual, definirComposicaoVisual] =
    useState<ReferenciaVisual["composicao"]>("editorial");
  const [referenciaVisual, definirReferenciaVisual] = useState("");
  const [enviando, definirEnviando] = useState(false);
  const [erro, definirErro] = useState<string | null>(null);

  const incluiCarrossel = selecao.some((posicao) => posicao.formato === "carrossel");
  const referenciasAprovadas =
    referencias.situacao === "pronto"
      ? referencias.dados.filter((item) => item.aprovada)
      : [];
  const estilosDaComposicao = referenciasAprovadas.filter(
    (item) => item.composicao === composicaoVisual,
  );

  useEffect(() => {
    if (!estilosDaComposicao.some((item) => item.identificador === referenciaVisual)) {
      definirReferenciaVisual(estilosDaComposicao[0]?.identificador ?? "");
    }
  }, [composicaoVisual, referenciaVisual, referencias.situacao]);

  const modoDisponivel = modo === "demo" ? demoDisponivel : realDisponivel;
  const podeGerar =
    selecao.length > 0 &&
    nome.trim() !== "" &&
    modoDisponivel &&
    extracaoCompleta &&
    (!incluiCarrossel || referenciaVisual !== "") &&
    !enviando;

  function gerar() {
    definirEnviando(true);
    definirErro(null);
    const pedido = selecao.map((p) => ({
      audiencia: p.audiencia as Audiencia,
      formato: p.formato as Formato,
    }));
    criarSaida({
      nome: nome.trim(),
      ...(unida
        ? { itens: escolha.atas.map((ata) => ata.identificador) }
        : { ata: escolha.atas[0].identificador }),
      modo,
      pedido,
      comite: false,
      duracao,
      ...(incluiCarrossel
        ? {
            composicao_visual: composicaoVisual,
            referencia_visual: referenciaVisual,
          }
        : {}),
    })
      .then((andamento) => onGerada(andamento.identificador))
      .catch((falha: unknown) => {
        definirErro(mensagemDeFalha(falha));
        definirEnviando(false);
      });
  }

  return (
    <Moldura
      titulo="Configurar a Saída"
      passo={2}
      rodape={
        <>
          <span className="text-xs text-suave">
            <b className="text-texto">{resumirPedido(selecao)}</b> serão geradas ·{" "}
            {modo === "demo" ? "sem custo, sem rede" : "usa a cota gratuita dos provedores"}
          </span>
          <div className="flex-1" />
          <button type="button" onClick={onVoltar} className={BOTAO_SECUNDARIO}>
            Voltar
          </button>
          <button type="button" disabled={!podeGerar} onClick={gerar} className={BOTAO_PRIMARIO}>
            {enviando ? "Enviando…" : "Gerar"}
          </button>
        </>
      }
    >
      <div className="grid gap-6 lg:grid-cols-[1fr_1.15fr]">
        <div>
          <label
            htmlFor="nome-da-saida"
            className="mb-1.5 block text-[10.5px] font-bold uppercase tracking-wider text-suave"
          >
            Nome da Saída
          </label>
          <input
            id="nome-da-saida"
            value={nome}
            maxLength={120}
            onChange={(evento) => definirNome(evento.target.value)}
            className="w-full rounded-[10px] border border-linha bg-cartao px-3 py-2 text-[13px]"
          />
          <div className="mb-4 mt-1.5 text-[11px] text-suave">
            <p className="flex flex-wrap items-center gap-1.5">
              {unida
                ? `Visão unida de ${escolha.atas.length} itens`
                : `Fonte: ${escolha.atas[0].titulo} · Destaque único`}
              {semCalibrar && <Chip tom="alerta">não calibrado</Chip>}
            </p>
            {unida && (
              <ol className="mt-1 list-inside list-decimal space-y-0.5">
                {escolha.atas.map((ata) => (
                  <li key={ata.identificador}>{ata.titulo}</li>
                ))}
              </ol>
            )}
          </div>
          {!extracaoCompleta && (
            <p
              role="alert"
              className="mb-4 rounded-xl border border-suno/45 bg-suno/10 px-3 py-2 text-[11.5px] text-[#ffb3ad]"
            >
              <b>Geração bloqueada.</b>{" "}
              {unida
                ? "Um dos itens não tem uma data e um número com unidade no texto: a Visão unida inteira reprovaria por falha de extração."
                : "Esta Ata não tem uma data e um número com unidade no texto: toda Célula reprovaria por falha de extração e a geração só gastaria cota."}{" "}
              Importe o documento completo, com valores.
            </p>
          )}
          {semCalibrar && (
            <p className="mb-4 rounded-xl border border-alerta/40 bg-alerta/10 px-3 py-2 text-[11.5px] text-suave">
              <b className="text-texto">Não calibrado.</b> Os Limiares e o Léxico foram medidos só
              com Atas do Copom: o Laudo desta Saída vale como triagem, não como a mesma régua.
            </p>
          )}

          <p className="mb-1.5 text-[10.5px] font-bold uppercase tracking-wider text-suave">
            Como gerar
          </p>
          <div role="radiogroup" aria-label="Como gerar" className="grid grid-cols-2 gap-2">
            <OpcaoDeModo
              titulo="Demo"
              descricao={
                unida
                  ? "Indisponível: a Visão unida não tem respostas prontas."
                  : demoDisponivel
                    ? "Sem rede, respostas prontas. Disponível para esta Ata."
                    : "Indisponível: esta Ata não tem respostas prontas."
              }
              marcada={modo === "demo"}
              desabilitada={!demoDisponivel}
              onEscolher={() => definirModo("demo")}
            />
            <OpcaoDeModo
              titulo="Real"
              descricao={
                realDisponivel
                  ? "Gemini e Groq. Usa a cota gratuita."
                  : "Indisponível: falta chave e modelo de provedor no .env."
              }
              marcada={modo === "real"}
              desabilitada={!realDisponivel}
              onEscolher={() => definirModo("real")}
            />
          </div>
          {!demoDisponivel && !realDisponivel && (
            <p role="alert" className="mt-2 text-[11.5px] text-[#ffb3ad]">
              Nenhum modo disponível para esta escolha. A Demo só existe para uma Ata com respostas
              prontas; o modo Real precisa de chave e modelo de um provedor no .env.
            </p>
          )}
          {modo === "real" && (
            <p className="mt-2 text-[11px] text-suave">
              Cada Célula pode gastar até 3 chamadas ao modelo (a original e duas correções),
              além da extração das Âncoras
              {unida ? ` (uma por item, ${escolha.atas.length} no total)` : ""} e do Judge da
              Matriz.
            </p>
          )}
        </div>

        <div>
          <p className="mb-1.5 text-[10.5px] font-bold uppercase tracking-wider text-suave">
            Quais Células? Clique nas Células, nas linhas ou nas colunas
          </p>
          <SeletorDeMatriz selecao={selecao} onMudar={definirSelecao} desabilitado={enviando} />
          {selecao.some((p) => p.formato === "roteiro") && (
            <SeletorDeDuracao valor={duracao} onMudar={definirDuracao} desabilitado={enviando} />
          )}
          {selecao.length === 1 && (
            <p className="mt-2 text-[11px] text-suave">
              Com uma Célula só, a avaliação da Matriz inteira não roda: coerência entre Células
              pede ao menos duas.
            </p>
          )}
        </div>
      </div>
      {incluiCarrossel && referencias.situacao === "carregando" && (
        <Carregando rotulo="Carregando configuração visual…" />
      )}
      {incluiCarrossel && referencias.situacao === "erro" && (
        <MensagemErro erro={referencias.erro} />
      )}
      {incluiCarrossel && referencias.situacao === "pronto" && (
        <ConfiguracaoVisual
          referencias={referencias.dados}
          composicao={composicaoVisual}
          referencia={referenciaVisual}
          desabilitada={enviando}
          onComposicao={definirComposicaoVisual}
          onReferencia={definirReferenciaVisual}
        />
      )}
      {erro && (
        <p
          role="alert"
          className="mt-4 rounded-xl border border-suno/45 bg-suno/10 px-3 py-2 text-sm text-[#ffb3ad]"
        >
          {erro}
        </p>
      )}
    </Moldura>
  );
}

// ---------------------------------------------------------------- passo 3

function PassoGerando({ identificador }: { identificador: string }) {
  const resumo = usarRequisicao(() => obterResumo(identificador), [identificador]);
  const nome = resumo.situacao === "pronto" ? resumo.dados.nome : identificador;
  return (
    <Moldura
      titulo={`Gerando · ${nome}`}
      passo={3}
      rodape={
        <>
          <span className="text-xs text-suave">Ao terminar, a Saída aparece na guia Saídas.</span>
          <div className="flex-1" />
          <Link to="/curadoria" className={BOTAO_SECUNDARIO}>
            Nova geração
          </Link>
          <Link
            to={`/saidas/${encodeURIComponent(identificador)}`}
            className={`${BOTAO_PRIMARIO} inline-block`}
          >
            Ver em Saídas
          </Link>
        </>
      }
    >
      <MatrizAoVivo identificador={identificador} />
    </Moldura>
  );
}

// ---------------------------------------------------------------- a página

export default function Curadoria() {
  const [parametros, definirParametros] = useSearchParams();
  const saida = parametros.get("saida");
  const [passo, definirPasso] = useState<1 | 2>(1);
  const [escolha, definirEscolha] = useState<Escolha | null>(null);
  const { selecao } = usarSelecaoDeAtas();
  const navegar = useNavigate();

  const origens = usarRequisicao(listarOrigens, []);
  const sugestoes = usarRequisicao(obterSugestoes, []);
  const saude = usarRequisicao(obterSaude, []);

  if (saida !== null) return <PassoGerando identificador={saida} />;

  if (
    origens.situacao === "carregando" ||
    sugestoes.situacao === "carregando" ||
    saude.situacao === "carregando"
  ) {
    return <Carregando rotulo="Carregando a Curadoria…" />;
  }
  if (origens.situacao === "erro") return <MensagemErro erro={origens.erro} />;
  if (sugestoes.situacao === "erro") return <MensagemErro erro={sugestoes.erro} />;
  if (saude.situacao === "erro") return <MensagemErro erro={saude.erro} />;

  // Quem marcou itens nas Fontes e apertou "Prosseguir" cai direto em Configurar, só com eles.
  const marcadas = origens.dados.origens
    .flatMap((origem) => origem.atas)
    .filter((ata) => selecao.includes(ata.identificador));
  const daSelecao = podeUsarSelecao(marcadas.map((ata) => ata.identificador));
  if (passo === 1 && daSelecao.ok && daSelecao.modo !== null) {
    return (
      <PassoConfigurar
        key={marcadas.map((ata) => ata.identificador).join("+")}
        escolha={{ modo: daSelecao.modo, atas: marcadas }}
        realDisponivel={saude.dados.real_disponivel}
        onVoltar={() => navegar("/fontes")}
        onGerada={(identificador) => definirParametros({ saida: identificador })}
      />
    );
  }

  if (passo === 2 && escolha !== null) {
    return (
      <PassoConfigurar
        key={escolha.atas.map((ata) => ata.identificador).join("+")}
        escolha={escolha}
        realDisponivel={saude.dados.real_disponivel}
        onVoltar={() => definirPasso(1)}
        onGerada={(identificador) => definirParametros({ saida: identificador })}
      />
    );
  }

  return (
    <PassoEscolher
      destaque={sugestoes.dados.destaque_unico}
      unida={sugestoes.dados.visao_unida}
      origens={origens.dados.origens}
      onUsar={(nova) => {
        definirEscolha(nova);
        definirPasso(2);
      }}
    />
  );
}
