// A guia Texto analítico. O fluxo comum (popup de confirmação, "Gerando o texto…", falha) é da
// interface; aqui fica o que acontece com o texto pronto: o formato, a audiência, as edições e o que
// o Histórico guarda e devolve. Um texto reaberto do Histórico aparece direto, sem popup, mesmo
// que a Saída de onde ele veio já não esteja na sessão.
import { useEffect, useMemo, useState } from "react";
import { AUDIENCIAS, type Audiencia, type Laudo } from "../../dados/cliente";
import FluxoDaGuia from "../../interface/FluxoDaGuia";
import Vazio from "../../interface/Vazio";
import { gravar } from "../../nucleo/armazenamento";
import { usarHistorico } from "../../nucleo/historico";
import { usarSessao } from "../../nucleo/sessao";
import AreaDoTexto from "./AreaDoTexto";
import { markdownParaHtml } from "./conversao";
import {
  CHAVE_DAS_EDICOES,
  comEdicao,
  lerEdicoes,
  valemPara,
  type EdicoesDaSessao,
  type HtmlPorAudiencia,
} from "./edicoes";
import { derivarEstrutura } from "./estrutura";
import { lerDados, resumoDoTexto, type DadosDoTexto, type FormatoDoTexto } from "./formatos";

interface TextoAberto {
  id: string;
  execucaoId: string | null;
  audiencia: Audiencia;
  html: string;
  laudo: Laudo | null;
}

function laudoDoSalvo(bruto: unknown, html: string, audiencia: Audiencia): Laudo | null {
  if (typeof bruto !== "object" || bruto === null) return null;
  const dados = bruto as Record<string, unknown>;
  if (dados.textoAvaliado !== html || typeof dados.laudo !== "object" || dados.laudo === null) return null;
  const laudo = dados.laudo as Laudo;
  return laudo.audiencia === audiencia && laudo.formato === "texto_analitico"
    && Array.isArray(laudo.medidas) && Array.isArray(laudo.motivos)
    && ["aprovado", "reprovado_corrigivel", "reprovado_revisao_humana"].includes(laudo.destino)
      ? laudo : null;
}

export default function GuiaTexto() {
  const sessao = usarSessao("texto_analitico");
  const { paraAbrir, consumirAbertura, salvar } = usarHistorico();
  const [formato, definirFormato] = useState<FormatoDoTexto>("email");
  const [escolhida, definirEscolhida] = useState<Audiencia | null>(null);
  const [edicoes, definirEdicoes] = useState<EdicoesDaSessao>(lerEdicoes);
  const [aberto, definirAberto] = useState<TextoAberto | null>(null);
  // Sobe quando o texto muda por fora (reabrir do Histórico): a tela recomeça do texto novo.
  const [rodada, definirRodada] = useState(0);

  const execucaoId = aberto ? aberto.execucaoId : sessao.execucaoId;

  useEffect(() => {
    gravar("sessao", CHAVE_DAS_EDICOES, edicoes);
  }, [edicoes]);

  useEffect(() => {
    if (!paraAbrir || paraAbrir.especie !== "texto") return;
    const dados = lerDados(paraAbrir.dados);
    consumirAbertura();
    if (!dados) return;
    definirFormato(dados.formato);
    definirEscolhida(paraAbrir.audiencia);
    definirAberto({
      id: paraAbrir.id,
      execucaoId: paraAbrir.execucaoId,
      audiencia: paraAbrir.audiencia,
      html: dados.html,
      laudo: laudoDoSalvo(paraAbrir.dados, dados.html, paraAbrir.audiencia),
    });
    definirRodada((atual) => atual + 1);
  }, [paraAbrir, consumirAbertura]);

  const originais = useMemo(() => {
    const mapa: HtmlPorAudiencia = {};
    for (const audiencia of AUDIENCIAS) {
      const texto = sessao.celulas[audiencia]?.conteudo.texto;
      if (texto) mapa[audiencia] = markdownParaHtml(texto);
    }
    return mapa;
  }, [sessao.celulas]);

  const aplicados = valemPara(edicoes, execucaoId);
  const htmlDe = (audiencia: Audiencia) => aberto
    ? (audiencia === aberto.audiencia ? aberto.html : "")
    : aplicados[audiencia] ?? originais[audiencia] ?? "";
  const audiencias = AUDIENCIAS.filter((audiencia) => htmlDe(audiencia) !== "");
  const audiencia: Audiencia | undefined = escolhida && audiencias.includes(escolhida) ? escolhida : audiencias[0];

  function guardar(dona: Audiencia, formatoEscolhido: FormatoDoTexto, html: string, laudo: Laudo | null) {
    const dados: DadosDoTexto & { laudo: Laudo | null; textoAvaliado: string | null } = {
      formato: formatoEscolhido, html, laudo, textoAvaliado: laudo ? html : null,
    };
    salvar({
      especie: "texto",
      titulo: derivarEstrutura(html).titulo,
      resumo: `${laudo?.destino === "aprovado" ? "Aprovado" : "Rascunho"} · ${resumoDoTexto(formatoEscolhido, html)}`,
      audiencia: dona,
      execucaoId,
      dados,
    });
  }

  const tela =
    audiencia === undefined ? (
      <Vazio titulo="Não há texto para mostrar." />
    ) : (
      <AreaDoTexto
        key={`${aberto?.id ?? sessao.execucaoId ?? "sessao"}:${rodada}`}
        execucaoId={execucaoId}
        laudo={aberto ? aberto.laudo : htmlDe(audiencia) === originais[audiencia] ? sessao.celulas[audiencia]?.laudo ?? null : null}
        onFecharSalvo={aberto ? () => definirAberto(null) : undefined}
        audiencias={audiencias}
        audiencia={audiencia}
        onMudarAudiencia={definirEscolhida}
        formato={formato}
        onMudarFormato={definirFormato}
        html={htmlDe(audiencia)}
        onAplicar={(html) => {
          if (aberto) definirAberto((atual) => atual ? { ...atual, html, laudo: null } : null);
          else definirEdicoes((atuais) => comEdicao(atuais, execucaoId, audiencia, html));
        }}
        onSalvar={(formatoEscolhido, html, laudo) => guardar(audiencia, formatoEscolhido, html, laudo)}
      />
    );

  if (aberto || (sessao.fase === "vazia" && audiencia !== undefined)) return tela;
  return (
    <FluxoDaGuia formato="texto_analitico" rotuloGerando="Gerando o texto…">
      {() => tela}
    </FluxoDaGuia>
  );
}
