// A guia Ingestão. À esquerda, uma linha por origem de notícias e o botão branco de importar
// documento. À direita, as notícias da origem escolhida (30 dias no Real, acervo no Demo); abrir uma
// mostra o texto já estruturado. A pessoa marca até 3 e o botão ATUALIZAR as guarda para gerar
// conteúdo. A seleção guardada some quando a aba fecha.
import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import {
  alterarOrigem,
  atualizarFontes,
  baixarPeriodo,
  cancelarAtualizacao,
  listarOrigens,
  mensagemDeFalha,
  obterAtualizacao,
  obterAta,
  type OrigemComAtas,
  type ResumoDaAta,
} from "../../dados/cliente";
import Botao from "../../interface/Botao";
import CartaoDeNoticia, { Bolinha } from "../../interface/CartaoDeNoticia";
import { CorpoDaPrevia, Divisao, Ilha, Titulo, TopoDaPrevia } from "../../interface/Divisao";
import { IconeAtualizar, IconeMarca, IconeVoltarSeta } from "../../interface/Icones";
import Linha from "../../interface/Linha";
import TextoDaAta from "../../interface/TextoDaAta";
import Vazio from "../../interface/Vazio";
import { seloDaAta } from "../../lib/fontes";
import { usarConfiguracoes } from "../../nucleo/configuracoes";
import { usarDados } from "../../nucleo/dados";
import { JANELA_EM_DIAS, noticiasDoModo } from "../../nucleo/janela";
import { CHAVES } from "../../nucleo/precarga";
import { MAXIMO_DE_NOTICIAS, usarSelecao } from "../../nucleo/selecao";
import { formatarDataCurta, formatarDataDoDia } from "../../texto/rotulos";
import FiltrarPeriodo from "./FiltrarPeriodo";
import ImportarComunicado from "./ImportarComunicado";
import { caraDaOrigem, frequenciaDaOrigem } from "./origens";

const INTERVALO_DA_ATUALIZACAO_MS = 1500;

function DetalheDaNoticia({
  ata,
  marcada,
  cheia,
  onMarcar,
  onVoltar,
}: {
  ata: ResumoDaAta;
  marcada: boolean;
  cheia: boolean;
  onMarcar: () => void;
  onVoltar: () => void;
}) {
  const { dados, erro } = usarDados(CHAVES.ata(ata.identificador), () => obterAta(ata.identificador));
  const selo = seloDaAta(ata.categoria);
  return (
    <div className="surge mx-auto max-w-[760px]">
      <div className="mb-6 flex items-start gap-4">
        <button
          type="button"
          onClick={onVoltar}
          aria-label="Voltar para as notícias"
          className="grid h-10 w-10 shrink-0 place-items-center rounded-full bg-superficie text-claro transition-colors duration-150 hover:bg-superficie-alta"
        >
          <IconeVoltarSeta size={22} />
        </button>
        <div className="min-w-0 flex-1">
          <h2 className="text-[24px] font-normal leading-tight">{ata.titulo}</h2>
          <p className="mt-1.5 text-[14px] text-etiqueta">
            {formatarDataDoDia(ata.data_referencia)}
            {selo && <span className="ml-2 text-coral-claro">{selo}</span>}
          </p>
        </div>
        <Bolinha
          marcada={marcada}
          desabilitada={cheia && !marcada}
          onClick={onMarcar}
          rotulo={`Selecionar ${ata.titulo}`}
        />
      </div>
      {ata.resumo && <p className="mb-6 text-[17px] leading-relaxed text-claro">{ata.resumo}</p>}
      {dados ? (
        <TextoDaAta texto={dados.texto} />
      ) : erro ? (
        <Vazio tom="coral" titulo="Não consegui abrir o texto." detalhe={erro.message} />
      ) : (
        <div className="flex flex-col gap-3" aria-hidden="true">
          {[100, 94, 98, 70].map((largura, indice) => (
            <span key={indice} className="pulsa h-3 rounded-full bg-superficie" style={{ width: `${largura}%` }} />
          ))}
        </div>
      )}
    </div>
  );
}

export default function GuiaIngestao() {
  const { modo } = usarConfiguracoes();
  const { dados, erro, recarregar } = usarDados(CHAVES.origens, listarOrigens);
  // O andamento da busca vem de uma rota leve: `/api/fontes` é lenta enquanto o servidor lê PDFs
  // grandes, e a tela ficaria parada em "Baixando 0 de N" esperando por ela.
  const { dados: andamento, recarregar: recarregarAndamento } = usarDados("atualizacao", obterAtualizacao, {
    atualizarACada: (estado) =>
      ["consultando", "baixando"].includes(estado.estado) ? INTERVALO_DA_ATUALIZACAO_MS : null,
  });
  const { rascunho, alternar, atualizar, pendente } = usarSelecao();
  const [origemAberta, definirOrigemAberta] = useState<string | null>(null);
  const [ataAberta, definirAtaAberta] = useState<string | null>(null);
  const [importando, definirImportando] = useState(false);
  const [ocupado, definirOcupado] = useState(false);
  const [aviso, definirAviso] = useState<string | null>(null);
  const [confirmado, definirConfirmado] = useState(false);
  const [baixando, definirBaixando] = useState(false);
  const [resultadoVisivel, definirResultadoVisivel] = useState(false);

  const origens = dados?.origens ?? [];
  const atualizacao = andamento ?? dados?.atualizacao;
  const estadoDaBusca = atualizacao?.estado;
  const buscando = estadoDaBusca === "consultando" || estadoDaBusca === "baixando";
  const aguardandoPeriodo = estadoDaBusca === "aguardando_filtro" && atualizacao !== undefined;
  const origem = origens.find((o) => o.id === origemAberta) ?? null;
  const cheia = rascunho.length >= MAXIMO_DE_NOTICIAS;

  const atasDaOrigem = useMemo(() => (origem ? noticiasDoModo(origem.atas, modo) : []), [origem, modo]);
  const todasAsAtas = useMemo(() => noticiasDoModo(origens.flatMap((o) => o.atas), modo), [origens, modo]);
  const ataEscolhida = todasAsAtas.find((a) => a.identificador === ataAberta) ?? null;
  const marcadas = rascunho
    .map((id) => todasAsAtas.find((a) => a.identificador === id))
    .filter((a): a is ResumoDaAta => a !== undefined);
  const noticiasSemOrigem = modo === "demo" ? todasAsAtas : marcadas;

  useEffect(() => {
    definirAtaAberta(null);
    definirConfirmado(false);
  }, [modo]);

  useEffect(() => {
    if (!confirmado) return;
    const temporizador = window.setTimeout(() => definirConfirmado(false), 1800);
    return () => window.clearTimeout(temporizador);
  }, [confirmado]);

  // Quando a busca termina (ou para esperando o período), a lista de notícias é lida de novo.
  const estadoAnterior = useRef(atualizacao?.estado);
  useEffect(() => {
    const antes = estadoAnterior.current;
    estadoAnterior.current = estadoDaBusca;
    if (antes && ["consultando", "baixando"].includes(antes) && estadoDaBusca !== antes) void recarregar();
  }, [estadoDaBusca, recarregar]);

  // O resultado de uma busca (quantos vieram) fica à vista por alguns segundos; a falha, até a próxima.
  useEffect(() => {
    if (estadoDaBusca !== "ok") return;
    definirResultadoVisivel(true);
    const temporizador = window.setTimeout(() => definirResultadoVisivel(false), 8000);
    return () => window.clearTimeout(temporizador);
  }, [estadoDaBusca, atualizacao?.concluida_em]);

  async function baixarOPeriodo(de: string, ate: string) {
    definirBaixando(true);
    definirAviso(null);
    try {
      await baixarPeriodo(de, ate);
      await recarregarAndamento();
    } catch (falha: unknown) {
      definirAviso(mensagemDeFalha(falha));
    } finally {
      definirBaixando(false);
    }
  }

  async function descartarConsulta() {
    try {
      await cancelarAtualizacao();
    } finally {
      await recarregarAndamento();
    }
  }

  function abrirOrigem(identificador: string) {
    definirOrigemAberta(identificador);
    definirAtaAberta(null);
  }

  async function buscarNovas() {
    definirOcupado(true);
    definirAviso(null);
    try {
      await atualizarFontes();
      await recarregarAndamento();
    } catch (falha: unknown) {
      definirAviso(mensagemDeFalha(falha));
    } finally {
      definirOcupado(false);
    }
  }

  async function ligar(origemAlvo: OrigemComAtas) {
    definirOcupado(true);
    definirAviso(null);
    try {
      await alterarOrigem(origemAlvo.id, true);
      await atualizarFontes();
      await recarregarAndamento();
    } catch (falha: unknown) {
      definirAviso(mensagemDeFalha(falha));
    } finally {
      definirOcupado(false);
    }
  }

  async function confirmar() {
    atualizar();
    definirConfirmado(true);
    await recarregar();
  }

  const esquerda = (
    <>
      <div className="flex items-center justify-between gap-4">
        <Titulo>Ingestão</Titulo>
        <button
          type="button"
          onClick={() => void buscarNovas()}
          disabled={ocupado || buscando}
          aria-label="Buscar notícias novas"
          title="Buscar notícias novas"
          className="grid h-10 w-10 place-items-center rounded-full text-claro transition-colors duration-150 hover:bg-superficie disabled:cursor-not-allowed disabled:opacity-50"
        >
          <IconeAtualizar size={22} className={ocupado || buscando ? "animate-spin" : ""} />
        </button>
      </div>

      <p className="mt-3 text-[14px] leading-snug text-etiqueta">
        {modo === "demo" ? "Acervo de demonstração · datas originais" : `Notícias dos últimos ${JANELA_EM_DIAS} dias`}
      </p>

      {atualizacao?.estado === "erro" && (
        <p role="alert" className="mt-3 text-[14px] leading-snug text-coral-claro">
          {atualizacao.mensagem}
        </p>
      )}
      {estadoDaBusca === "consultando" && (
        <p role="status" className="mt-3 text-[14px] leading-snug text-etiqueta">
          Procurando notícias dos últimos {atualizacao?.janela_dias} dias…
        </p>
      )}
      {estadoDaBusca === "baixando" && (
        <p role="status" className="mt-3 text-[14px] leading-snug text-etiqueta">
          Baixando {atualizacao?.baixados} de {atualizacao?.a_baixar}…
        </p>
      )}
      {estadoDaBusca === "ok" && resultadoVisivel && atualizacao?.mensagem && (
        <p role="status" className="mt-3 text-[14px] leading-snug text-claro">
          {atualizacao.mensagem}
        </p>
      )}
      {(aviso ?? (dados === undefined ? erro?.message : null)) && (
        <p role="alert" className="mt-3 text-[14px] leading-snug text-coral-claro">
          {aviso ?? erro?.message}
        </p>
      )}

      <div className="mt-8 flex flex-col gap-2.5">
        {dados === undefined &&
          !erro &&
          [0, 1, 2, 3].map((indice) => (
            <span
              key={indice}
              aria-hidden="true"
              className="pulsa h-[70px] rounded-lg bg-superficie"
              style={{ animationDelay: `${indice * 120}ms` }}
            />
          ))}
        {origens.map((o) => {
          const aparencia = caraDaOrigem(o.id);
          return (
            <Linha
              key={o.id}
              cor={aparencia.cor}
              icone={aparencia.icone(22)}
              titulo={o.nome}
              subtitulo={!o.disponivel ? (o.aviso ?? "em breve") : undefined}
              tomDoSubtitulo="coral"
              selecionada={o.id === origemAberta}
              desabilitada={!o.disponivel}
              onClick={() => abrirOrigem(o.id)}
            />
          );
        })}
      </div>

      <div className="mt-8">
        <Botao variante="claro" tamanho="grande" onClick={() => definirImportando(true)}>
          Importar documento
        </Botao>
      </div>
    </>
  );

  let corpo: ReactNode;
  if (ataEscolhida) {
    corpo = (
      <DetalheDaNoticia
        key={ataEscolhida.identificador}
        ata={ataEscolhida}
        marcada={rascunho.includes(ataEscolhida.identificador)}
        cheia={cheia}
        onMarcar={() => alternar(ataEscolhida.identificador)}
        onVoltar={() => definirAtaAberta(null)}
      />
    );
  } else if (origem) {
    corpo =
      atasDaOrigem.length > 0 ? (
        <ul key={origem.id} className="grid gap-3 xl:grid-cols-2">
          {atasDaOrigem.map((ata, indice) => (
            <li key={ata.identificador} className="surge" style={{ animationDelay: `${Math.min(indice, 8) * 40}ms` }}>
              <CartaoDeNoticia
                ata={ata}
                marcada={rascunho.includes(ata.identificador)}
                bolinhaDesabilitada={cheia && !rascunho.includes(ata.identificador)}
                onMarcar={() => alternar(ata.identificador)}
                onAbrir={() => definirAtaAberta(ata.identificador)}
              />
            </li>
          ))}
        </ul>
      ) : modo === "demo" ? (
        <Vazio
          titulo="Esta origem não tem Atas de demonstração."
          detalhe="Escolha uma origem com respostas prontas no acervo. As datas originais são preservadas."
        />
      ) : !origem.ativa && origem.disponivel ? (
        <Vazio
          titulo="Esta origem está desligada."
          acao={
            <Botao variante="claro" tamanho="pequeno" disabled={ocupado} onClick={() => void ligar(origem)}>
              Ligar e buscar
            </Botao>
          }
        />
      ) : (
        <Vazio
          titulo={`Nada nos últimos ${JANELA_EM_DIAS} dias.`}
          acao={
            <Botao variante="escuro" tamanho="pequeno" disabled={ocupado || buscando} onClick={() => void buscarNovas()}>
              Buscar novas
            </Botao>
          }
        />
      );
  } else if (noticiasSemOrigem.length > 0) {
    corpo = (
      <ul className="surge grid gap-3 xl:grid-cols-2">
        {noticiasSemOrigem.map((ata) => (
          <li key={ata.identificador}>
            <CartaoDeNoticia
              ata={ata}
              marcada={rascunho.includes(ata.identificador)}
              bolinhaDesabilitada={cheia && !rascunho.includes(ata.identificador)}
              onMarcar={() => alternar(ata.identificador)}
              onAbrir={() => {
                const dona = origens.find((o) => o.atas.some((a) => a.identificador === ata.identificador));
                if (dona) definirOrigemAberta(dona.id);
                definirAtaAberta(ata.identificador);
              }}
            />
          </li>
        ))}
      </ul>
    );
  } else {
    corpo = <Vazio titulo={modo === "demo"
      ? dados === undefined && !erro ? "Carregando o acervo de demonstração…" : "O acervo de demonstração está vazio."
      : "Escolha uma origem."} />;
  }

  const direita = (
    <>
      <TopoDaPrevia
        esquerda={
          <Ilha>
            {rascunho.length} de {MAXIMO_DE_NOTICIAS} selecionadas
          </Ilha>
        }
        direita={
          <Botao
            variante={pendente ? "claro" : "escuro"}
            onClick={() => void confirmar()}
            disabled={!pendente && !confirmado}
            icone={confirmado ? <IconeMarca size={18} strokeWidth={2.5} /> : undefined}
          >
            {confirmado ? "Atualizado" : "Atualizar"}
          </Botao>
        }
      />
      <CorpoDaPrevia>{corpo}</CorpoDaPrevia>
      {modo === "real" && origem && frequenciaDaOrigem(origem.id) && (
        <p className="shrink-0 px-5 pb-5 text-right text-[13px] leading-snug text-etiqueta lg:px-[50px]">
          {frequenciaDaOrigem(origem.id)}
        </p>
      )}
    </>
  );

  return (
    <>
      <Divisao esquerda={esquerda} direita={direita} />
      {importando && (
        <ImportarComunicado
          onFechar={() => definirImportando(false)}
          onImportada={(ata) => {
            definirImportando(false);
            void recarregar().then(() => {
              abrirOrigem("importados");
              definirAtaAberta(ata.identificador);
            });
          }}
        />
      )}
      {aguardandoPeriodo && (
        <FiltrarPeriodo
          estado={atualizacao}
          origens={origens}
          enviando={baixando}
          erro={aviso}
          onBaixar={(de, ate) => void baixarOPeriodo(de, ate)}
          onCancelar={() => void descartarConsulta()}
        />
      )}
      {atualizacao?.concluida_em && (
        <span className="sr-only">Atualizado em {formatarDataCurta(atualizacao.concluida_em)}</span>
      )}
    </>
  );
}
