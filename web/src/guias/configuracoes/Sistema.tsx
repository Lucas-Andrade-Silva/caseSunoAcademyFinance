// O que o sistema liga e desliga e quem atende cada papel de LLM: Jev, checador de fidelidade, teto de
// requisições por minuto, e provedor e modelo de cada papel. Tudo vive no servidor (`/api/configuracoes`)
// e vale na próxima chamada, sem reiniciar. As chaves ficam no `.env`: aqui só se vê se existem.
import { useEffect, useState } from "react";
import {
  mensagemDeFalha,
  obterConfiguracoesDoSistema,
  obterSaude,
  restaurarConfiguracoesDoSistema,
  salvarConfiguracoesDoSistema,
  type ConfiguracoesComEstado,
  type ConfiguracoesDoSistema,
} from "../../dados/cliente";
import Botao from "../../interface/Botao";
import { Rotulo, TituloDeSecao } from "../../interface/Divisao";
import { Pilulas } from "../../interface/Pilulas";
import { buscar, usarDados } from "../../nucleo/dados";
import { CHAVES } from "../../nucleo/precarga";

type Provedor = "gemini" | "groq";
type Entrada = { provedor: Provedor; modelo: string };

const PAPEIS: { papel: string; titulo: string; descricao: string }[] = [
  { papel: "gerador", titulo: "Geração e recriação", descricao: "Escreve as nove Células e as refaz quando o Laudo reprova." },
  { papel: "checador", titulo: "Checador de fidelidade", descricao: "Lê a Ata inteira e confere a Célula contra ela." },
  { papel: "video", titulo: "Prompt do vídeo", descricao: "Dirige a atuação do avatar cena a cena." },
  { papel: "juiz_visao", titulo: "Juiz de visão", descricao: "Diz se a foto da web ilustra o slide." },
  { papel: "diretor_arte", titulo: "Diretor de arte", descricao: "Escolhe a composição visual do carrossel." },
  { papel: "analista_visual", titulo: "Analista visual", descricao: "Lê as imagens de referência." },
];

const NOME: Record<Provedor, string> = { gemini: "Gemini", groq: "Groq" };

const CAMPO =
  "h-11 w-full rounded-lg bg-fundo px-4 text-[15px] outline-none placeholder:text-apagado focus:ring-1 focus:ring-claro/60";

function Cartao({ children }: { children: React.ReactNode }) {
  return <div className="rounded-lg bg-superficie p-5">{children}</div>;
}

function Interruptor({ rotulo, valor, onMudar }: { rotulo: string; valor: boolean; onMudar: (v: boolean) => void }) {
  return (
    <Pilulas
      rotuloAcessivel={rotulo}
      valor={valor ? "sim" : "nao"}
      onMudar={(v) => onMudar(v === "sim")}
      opcoes={[
        { valor: "sim", rotulo: "Ligado" },
        { valor: "nao", rotulo: "Desligado" },
      ]}
    />
  );
}

function Selecao({
  rotulo,
  valor,
  onMudar,
  children,
}: {
  rotulo: string;
  valor: string;
  onMudar: (v: string) => void;
  children: React.ReactNode;
}) {
  return (
    <select aria-label={rotulo} value={valor} onChange={(e) => onMudar(e.target.value)} className={`${CAMPO} appearance-none`}>
      {children}
    </select>
  );
}

export default function Sistema() {
  const { dados, erro } = usarDados(CHAVES.configuracoesDoSistema, obterConfiguracoesDoSistema);
  const [rascunho, definirRascunho] = useState<ConfiguracoesDoSistema | null>(null);
  const [falha, definirFalha] = useState<string | null>(null);
  const [ocupado, definirOcupado] = useState(false);

  useEffect(() => {
    if (dados && rascunho === null) definirRascunho(dados.configuracoes);
  }, [dados, rascunho]);

  if (erro && !dados) {
    return <p className="mt-8 text-[13px] text-coral-claro">Sem resposta do servidor: {erro.message}</p>;
  }
  if (!dados || !rascunho) return <div className="mt-8 h-40 rounded-lg bg-superficie" aria-busy="true" />;

  const sujo = JSON.stringify(rascunho) !== JSON.stringify(dados.configuracoes);
  const mudar = (parcial: Partial<ConfiguracoesDoSistema>) => definirRascunho({ ...rascunho, ...parcial });

  async function aplicar(acao: () => Promise<ConfiguracoesComEstado>) {
    definirOcupado(true);
    definirFalha(null);
    try {
      const resposta = await acao();
      await buscar(CHAVES.configuracoesDoSistema, async () => resposta);
      definirRascunho(resposta.configuracoes);
      void buscar(CHAVES.saude, obterSaude);
    } catch (e) {
      definirFalha(mensagemDeFalha(e));
    } finally {
      definirOcupado(false);
    }
  }

  const fila = (papel: string): Entrada[] => (rascunho.papeis[papel] ?? []) as Entrada[];
  const trocarFila = (papel: string, nova: Entrada[]) => mudar({ papeis: { ...rascunho.papeis, [papel]: nova } });

  return (
    <>
      <div className="mt-14">
        <TituloDeSecao>Avaliação</TituloDeSecao>
      </div>
      <div className="mt-6 flex flex-col gap-2.5">
        <Cartao>
          <div className="flex items-center justify-between gap-3">
            <div>
              <span className="text-[17px]">Qualidade pelo Jev</span>
              <p className="mt-1 text-[13px] text-apagado">
                Nota o desenvolvimento, o corte e a leitura. Roda depois do determinístico, em créditos da Netlify.
                {!dados.chaves.jev && " Falta JEV_API_KEY no .env: com provedor real a geração não começa."}
              </p>
            </div>
            <Interruptor rotulo="Qualidade pelo Jev" valor={rascunho.jev_ligado} onMudar={(v) => mudar({ jev_ligado: v })} />
          </div>
          {rascunho.jev_ligado && (
            <div className="mt-4 grid gap-3 sm:grid-cols-[1fr_140px]">
              <input
                aria-label="Endereço do Jev"
                value={rascunho.jev_url}
                onChange={(e) => mudar({ jev_url: e.target.value })}
                className={CAMPO}
                placeholder="https://… (vazio usa a TypeSafe)"
              />
              <input
                aria-label="Nota mínima do Jev"
                inputMode="decimal"
                value={rascunho.jev_limiar ?? ""}
                onChange={(e) => {
                  const bruto = e.target.value.replace(",", ".").trim();
                  mudar({ jev_limiar: bruto === "" || Number.isNaN(Number(bruto)) ? null : Number(bruto) });
                }}
                className={CAMPO}
                placeholder="Nota mínima"
              />
            </div>
          )}
        </Cartao>
        <Cartao>
          <div className="flex items-center justify-between gap-3">
            <div>
              <span className="text-[17px]">Checador de fidelidade</span>
              <p className="mt-1 text-[13px] text-apagado">Um LLM confere a Célula contra a Ata e o código confere a citação.</p>
            </div>
            <Interruptor
              rotulo="Checador de fidelidade"
              valor={rascunho.fidelidade_ligada}
              onMudar={(v) => mudar({ fidelidade_ligada: v })}
            />
          </div>
        </Cartao>
      </div>

      <div className="mt-14">
        <TituloDeSecao>Ritmo da geração</TituloDeSecao>
      </div>
      <div className="mt-6 flex flex-col gap-2.5">
        <Cartao>
          <label htmlFor="rodadas" className="block text-[17px]">
            Rodadas de correção por Célula
          </label>
          <p className="mt-1 text-[13px] text-apagado">
            Reprovou no Laudo, o Ciclo regenera e roda o determinístico (Flesch-BR, densidade, aderência, integridade,
            compliance) de novo. Só quando ele aprova entram o Jev e o checador. Cada rodada gasta chamadas: de 0 a 10.
          </p>
          <input
            id="rodadas"
            type="number"
            min={0}
            max={10}
            value={rascunho.rodadas_de_correcao}
            onChange={(e) => mudar({ rodadas_de_correcao: Math.max(0, Math.min(10, Math.trunc(Number(e.target.value) || 0))) })}
            className={`${CAMPO} mt-3 w-32`}
          />
        </Cartao>
        <Cartao>
          <label htmlFor="rpm" className="block text-[17px]">
            Requisições por minuto aos LLMs
          </label>
          <p className="mt-1 text-[13px] text-apagado">
            Gemini e Groq somados, no servidor inteiro. Passou do teto, a chamada espera. 0 não limita.
          </p>
          <input
            id="rpm"
            type="number"
            min={0}
            max={600}
            value={rascunho.requisicoes_por_minuto}
            onChange={(e) =>
              mudar({ requisicoes_por_minuto: Math.max(0, Math.min(600, Math.trunc(Number(e.target.value) || 0))) })
            }
            className={`${CAMPO} mt-3 w-32`}
          />
        </Cartao>
      </div>

      <div className="mt-14">
        <TituloDeSecao>Provedores e modelos</TituloDeSecao>
      </div>
      <div className="mt-6 flex flex-col gap-2.5">
        <Rotulo>Modelo padrão de cada provedor</Rotulo>
        <Cartao>
          <div className="grid gap-3 sm:grid-cols-2">
            {(["gemini", "groq"] as const).map((p) => (
              <div key={p}>
                <label htmlFor={`padrao-${p}`} className="mb-1.5 block text-[13px] text-apagado">
                  {NOME[p]}
                  {dados.chaves[p] ? "" : " — sem chave no .env"}
                </label>
                <input
                  id={`padrao-${p}`}
                  list={`modelos-${p}`}
                  value={rascunho.modelo_padrao[p] ?? ""}
                  onChange={(e) => mudar({ modelo_padrao: { ...rascunho.modelo_padrao, [p]: e.target.value } })}
                  className={CAMPO}
                />
                <datalist id={`modelos-${p}`}>
                  {(dados.modelos_sugeridos[p] ?? []).map((m) => (
                    <option key={m} value={m} />
                  ))}
                </datalist>
              </div>
            ))}
          </div>
        </Cartao>

        <Rotulo>Cada papel: quem tenta primeiro e quem reserva</Rotulo>
        {PAPEIS.map(({ papel, titulo, descricao }) => {
          const entradas = fila(papel);
          const principal: Entrada = entradas[0] ?? { provedor: "gemini", modelo: "" };
          const reserva = entradas[1] ?? null;
          const outro: Provedor = principal.provedor === "gemini" ? "groq" : "gemini";
          return (
            <Cartao key={papel}>
              <span className="text-[17px]">{titulo}</span>
              <p className="mt-1 text-[13px] text-apagado">{descricao}</p>
              <div className="mt-4 grid gap-3 sm:grid-cols-[170px_1fr]">
                <Selecao
                  rotulo={`${titulo}: provedor principal`}
                  valor={principal.provedor}
                  onMudar={(v) => {
                    const novo = v as Provedor;
                    const par: Provedor = novo === "gemini" ? "groq" : "gemini";
                    trocarFila(papel, [
                      { provedor: novo, modelo: "" },
                      ...(reserva ? [{ provedor: par, modelo: reserva.modelo }] : []),
                    ]);
                  }}
                >
                  <option value="gemini">Gemini</option>
                  <option value="groq">Groq</option>
                </Selecao>
                <input
                  aria-label={`${titulo}: modelo do principal`}
                  list={`modelos-${principal.provedor}`}
                  value={principal.modelo}
                  onChange={(e) => trocarFila(papel, [{ ...principal, modelo: e.target.value }, ...(reserva ? [reserva] : [])])}
                  className={CAMPO}
                  placeholder={`Padrão: ${rascunho.modelo_padrao[principal.provedor] || "—"}`}
                />
                <Selecao
                  rotulo={`${titulo}: reserva`}
                  valor={reserva ? reserva.provedor : "nenhuma"}
                  onMudar={(v) =>
                    trocarFila(papel, v === "nenhuma" ? [principal] : [principal, { provedor: outro, modelo: reserva?.modelo ?? "" }])
                  }
                >
                  <option value="nenhuma">Sem reserva</option>
                  <option value={outro}>Reserva: {NOME[outro]}</option>
                </Selecao>
                {reserva ? (
                  <input
                    aria-label={`${titulo}: modelo da reserva`}
                    list={`modelos-${reserva.provedor}`}
                    value={reserva.modelo}
                    onChange={(e) => trocarFila(papel, [principal, { ...reserva, modelo: e.target.value }])}
                    className={CAMPO}
                    placeholder={`Padrão: ${rascunho.modelo_padrao[reserva.provedor] || "—"}`}
                  />
                ) : (
                  <span />
                )}
              </div>
            </Cartao>
          );
        })}
      </div>

      <div className="sticky bottom-4 z-10 mt-8 flex items-center justify-between gap-3 rounded-lg bg-superficie-alta p-4 shadow-lg">
        <span className={`text-[13px] ${falha ? "text-coral-claro" : "text-apagado"}`} role="status">
          {falha ?? (sujo ? "Alterações não salvas" : dados.salvas ? "Salvo no servidor" : "Valendo o .env e os padrões")}
        </span>
        <span className="flex gap-2">
          <Botao tamanho="pequeno" disabled={ocupado || !dados.salvas} onClick={() => void aplicar(restaurarConfiguracoesDoSistema)}>
            Restaurar padrão
          </Botao>
          <Botao
            tamanho="pequeno"
            variante="claro"
            disabled={ocupado || !sujo}
            onClick={() => void aplicar(() => salvarConfiguracoesDoSistema(rascunho))}
          >
            Salvar
          </Botao>
        </span>
      </div>
    </>
  );
}
