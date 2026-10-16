// Configurações: o modo de geração, o nome do avatar, o que o sistema liga e desliga (Jev, checador,
// limite de requisições, provedor e modelo de cada papel) e a limpeza do que fica no navegador.
// À direita, o estado do servidor.
import { useState } from "react";
import { obterSaude } from "../../dados/cliente";
import Botao from "../../interface/Botao";
import { CorpoDaPrevia, Divisao, Rotulo, Titulo, TituloDeSecao, TopoDaPrevia } from "../../interface/Divisao";
import { Pilulas } from "../../interface/Pilulas";
import { usarConfiguracoes } from "../../nucleo/configuracoes";
import { usarDados } from "../../nucleo/dados";
import { usarHistorico } from "../../nucleo/historico";
import { JANELA_EM_DIAS } from "../../nucleo/janela";
import { CHAVES } from "../../nucleo/precarga";
import Sistema from "./Sistema";
import { usarSelecao } from "../../nucleo/selecao";

function Cartao({ children }: { children: React.ReactNode }) {
  return <div className="rounded-lg bg-superficie p-5">{children}</div>;
}

function LinhaDeEstado({ rotulo, valor, tom = "claro" }: { rotulo: string; valor: string; tom?: "claro" | "coral" }) {
  return (
    <div className="flex items-baseline justify-between gap-4 border-b border-[#333] py-4 last:border-b-0">
      <dt className="text-[17px]">{rotulo}</dt>
      <dd className={`text-[17px] tabular-nums ${tom === "coral" ? "text-coral-claro" : "text-claro"}`}>{valor}</dd>
    </div>
  );
}

export default function GuiaConfiguracoes() {
  const { modo, realDisponivel, nome, definirModo, definirNome } = usarConfiguracoes();
  const { salvos, limpar: limparHistorico } = usarHistorico();
  const { guardada, limpar: limparSelecao } = usarSelecao();
  const { dados: saude, erro } = usarDados(CHAVES.saude, obterSaude);
  const [confirmando, definirConfirmando] = useState(false);

  return (
    <Divisao
      esquerda={
        <>
          <Titulo>Configurações</Titulo>

          <div className="mt-8 flex flex-col gap-2.5">
            <Cartao>
              <div className="flex items-center justify-between gap-3">
                <span className="text-[17px]">Modo de geração</span>
                <Pilulas
                  rotuloAcessivel="Modo de geração"
                  valor={modo}
                  onMudar={definirModo}
                  opcoes={[
                    { valor: "demo", rotulo: "Demo" },
                    { valor: "real", rotulo: "Real" },
                  ]}
                />
              </div>
              {modo === "real" && !realDisponivel && (
                <p className="mt-3 text-[13px] text-coral-claro">O servidor não tem provedor configurado.</p>
              )}
            </Cartao>

            <Cartao>
              <label htmlFor="nome-da-pessoa" className="block text-[17px]">
                Seu nome
              </label>
              <input
                id="nome-da-pessoa"
                value={nome}
                onChange={(evento) => definirNome(evento.target.value)}
                className="mt-3 h-12 w-full rounded-lg bg-fundo px-4 text-[17px] outline-none placeholder:text-apagado focus:ring-1 focus:ring-claro/60"
                placeholder="Como aparece no avatar"
              />
            </Cartao>
          </div>

          <Sistema />

          <div className="mt-14">
            <TituloDeSecao>Dados deste navegador</TituloDeSecao>
          </div>
          <div className="mt-6 flex flex-col gap-2.5">
            <Rotulo>Salvos</Rotulo>
            <Cartao>
              <div className="flex items-center justify-between gap-3">
                <span className="text-[17px]">
                  {salvos.length} {salvos.length === 1 ? "conteúdo salvo" : "conteúdos salvos"}
                </span>
                {confirmando ? (
                  <span className="flex gap-2">
                    <Botao tamanho="pequeno" onClick={() => definirConfirmando(false)}>
                      Cancelar
                    </Botao>
                    <Botao
                      tamanho="pequeno"
                      variante="claro"
                      onClick={() => {
                        limparHistorico();
                        definirConfirmando(false);
                      }}
                    >
                      Apagar
                    </Botao>
                  </span>
                ) : (
                  <Botao tamanho="pequeno" disabled={salvos.length === 0} onClick={() => definirConfirmando(true)}>
                    Limpar
                  </Botao>
                )}
              </div>
            </Cartao>
            <Rotulo>Seleção</Rotulo>
            <Cartao>
              <div className="flex items-center justify-between gap-3">
                <span className="text-[17px]">
                  {guardada.length} {guardada.length === 1 ? "notícia guardada" : "notícias guardadas"}
                </span>
                <Botao tamanho="pequeno" disabled={guardada.length === 0} onClick={limparSelecao}>
                  Limpar
                </Botao>
              </div>
            </Cartao>
          </div>
        </>
      }
      direita={
        <>
          <TopoDaPrevia />
          <CorpoDaPrevia>
            <div className="mx-auto max-w-[560px]">
              <TituloDeSecao>Servidor</TituloDeSecao>
              <dl className="mt-6 rounded-xl bg-superficie px-7 py-2">
                <LinhaDeEstado
                  rotulo="API"
                  valor={saude?.ok ? "no ar" : erro ? "sem resposta" : "…"}
                  tom={erro ? "coral" : "claro"}
                />
                <LinhaDeEstado
                  rotulo="Provedor Real"
                  valor={saude ? (saude.real_disponivel ? "configurado" : "sem chave") : "…"}
                  tom={saude && !saude.real_disponivel ? "coral" : "claro"}
                />
                <LinhaDeEstado rotulo="Saídas gravadas" valor={saude ? String(saude.execucoes) : "…"} />
                <LinhaDeEstado rotulo="Janela de notícias" valor={`${JANELA_EM_DIAS} dias`} />
              </dl>
            </div>
          </CorpoDaPrevia>
        </>
      }
    />
  );
}
