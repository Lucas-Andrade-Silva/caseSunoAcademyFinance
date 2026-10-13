// A guia Carrossel. O fluxo comum (popup, "Gerando…", falha) vem de `FluxoDaGuia`; com o carrossel
// pronto, `Editor` mostra os quadros, as configurações visuais e a prévia no celular. Também abre
// um carrossel salvo no Histórico sem precisar de geração: os slides vêm no próprio salvo.
import { useEffect, useMemo, useState } from "react";
import { listarReferenciasVisuais, type Audiencia } from "../../dados/cliente";
import Botao from "../../interface/Botao";
import FluxoDaGuia from "../../interface/FluxoDaGuia";
import { IconeAtualizar, IconeFechar } from "../../interface/Icones";
import Vazio from "../../interface/Vazio";
import { usarDados } from "../../nucleo/dados";
import { usarHistorico } from "../../nucleo/historico";
import { CHAVES } from "../../nucleo/precarga";
import { lerDadosSalvos, type DadosDoCarrossel } from "./dadosSalvos";
import { extrasDoDesign, gravarDesign, gravarIdDaPaleta, lerDesign, lerIdDaPaleta } from "./design";
import Editor, { type OrigemDoEditor } from "./Editor";
import type { Design } from "./modelo";

interface SalvoAberto {
  id: string;
  titulo: string;
  audiencia: Audiencia;
  execucaoId: string | null;
  /** `null` quando o salvo não tem o formato esperado. */
  dados: DadosDoCarrossel | null;
}

export default function GuiaCarrossel() {
  const { paraAbrir, consumirAbertura } = usarHistorico();
  const { dados: referencias } = usarDados(CHAVES.referencias, listarReferenciasVisuais);
  const [design, definirDesign] = useState<Design | null>(lerDesign);
  const [idDaPaleta, definirIdDaPaleta] = useState(lerIdDaPaleta);
  const [aberto, definirAberto] = useState<SalvoAberto | null>(null);

  useEffect(() => {
    if (paraAbrir?.especie !== "carrossel") return;
    definirAberto({
      id: paraAbrir.id,
      titulo: paraAbrir.titulo,
      audiencia: paraAbrir.audiencia,
      execucaoId: paraAbrir.execucaoId,
      dados: lerDadosSalvos(paraAbrir.dados),
    });
    consumirAbertura();
  }, [paraAbrir, consumirAbertura]);

  // O design salvo vale como padrão ao gerar: o pedido ao servidor leva composição e referência.
  const extras = useMemo(() => extrasDoDesign(design, referencias), [design, referencias]);

  function salvarDesign(novo: Design) {
    gravarDesign(novo);
    definirDesign(novo);
  }

  function escolherPaleta(id: string) {
    gravarIdDaPaleta(id);
    definirIdDaPaleta(id);
  }

  if (aberto) {
    const { dados } = aberto;
    const sair = { rotulo: "Sair do salvo", icone: <IconeFechar size={22} />, aoClicar: () => definirAberto(null) };
    if (!dados) {
      return (
        <div className="flex min-h-full items-center justify-center lg:pl-[var(--area-da-rail)]">
          <Vazio
            tom="coral"
            titulo="Este carrossel salvo está incompleto."
            acao={
              <Botao variante="escuro" tamanho="pequeno" onClick={sair.aoClicar}>
                Voltar
              </Botao>
            }
          />
        </div>
      );
    }
    return (
      <Editor
        key={`salvo-${aberto.id}`}
        titulo={aberto.titulo}
        execucaoId={aberto.execucaoId}
        origens={[{ audiencia: aberto.audiencia, slides: dados.slides, laudo: dados.laudo, ancoras: dados.ancoras }]}
        restaurado={{
          audiencia: aberto.audiencia,
          slides: dados.slides,
          composicao: dados.composicao,
          referenciaId: dados.referenciaId,
          paleta: dados.paleta,
          icones: dados.icones,
          ancoras: dados.ancoras,
        }}
        design={design}
        idDaPaleta={idDaPaleta}
        aoSalvarDesign={salvarDesign}
        aoEscolherPaleta={escolherPaleta}
        acaoDoTitulo={sair}
      />
    );
  }

  return (
    <FluxoDaGuia formato="carrossel" rotuloGerando="Gerando o carrossel…" extras={extras}>
      {(sessao) => {
        const origens: OrigemDoEditor[] = sessao.audiencias.flatMap((audiencia) => {
          const celula = sessao.celulas[audiencia];
          const slides = celula?.conteudo.slides ?? [];
          return celula && slides.length > 0 ? [{ audiencia, slides, laudo: celula.laudo }] : [];
        });
        if (origens.length === 0) {
          return (
            <div className="flex min-h-full items-center justify-center lg:pl-[var(--area-da-rail)]">
              <Vazio
                titulo="Esta Saída não tem quadros."
                acao={
                  <Botao variante="claro" tamanho="pequeno" onClick={sessao.limpar}>
                    Nova geração
                  </Botao>
                }
              />
            </div>
          );
        }
        return (
          <Editor
            key={sessao.execucaoId ?? "sessao"}
            titulo={sessao.nome.replace(/ · Carrossel$/, "")}
            execucaoId={sessao.execucaoId}
            origens={origens}
            design={design}
            idDaPaleta={idDaPaleta}
            aoSalvarDesign={salvarDesign}
            aoEscolherPaleta={escolherPaleta}
            acaoDoTitulo={{
              rotulo: "Nova geração",
              icone: <IconeAtualizar size={22} />,
              aoClicar: sessao.limpar,
            }}
          />
        );
      }}
    </FluxoDaGuia>
  );
}
