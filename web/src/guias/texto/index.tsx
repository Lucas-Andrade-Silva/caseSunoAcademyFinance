// A guia Texto analítico. O fluxo comum (popup de confirmação, "Gerando o texto…", falha) é da
// interface; aqui fica o que acontece com o texto pronto: o formato, a audiência, as edições e o que
// o Histórico guarda e devolve. Um texto reaberto do Histórico aparece direto, sem popup, mesmo
// que a Saída de onde ele veio já não esteja na sessão.
import { useEffect, useMemo, useState } from "react";
import { AUDIENCIAS, type Audiencia } from "../../dados/cliente";
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

export default function GuiaTexto() {
  const sessao = usarSessao("texto_analitico");
  const { paraAbrir, consumirAbertura, salvar } = usarHistorico();
  const [formato, definirFormato] = useState<FormatoDoTexto>("email");
  const [escolhida, definirEscolhida] = useState<Audiencia | null>(null);
  const [edicoes, definirEdicoes] = useState<EdicoesDaSessao>(lerEdicoes);
  // Sobe quando o texto muda por fora (reabrir do Histórico): a tela recomeça do texto novo.
  const [rodada, definirRodada] = useState(0);

  const execucaoId = sessao.execucaoId;

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
    definirEdicoes((atuais) => comEdicao(atuais, execucaoId, paraAbrir.audiencia, dados.html));
    definirRodada((atual) => atual + 1);
  }, [paraAbrir, consumirAbertura, execucaoId]);

  const originais = useMemo(() => {
    const mapa: HtmlPorAudiencia = {};
    for (const audiencia of AUDIENCIAS) {
      const texto = sessao.celulas[audiencia]?.conteudo.texto;
      if (texto) mapa[audiencia] = markdownParaHtml(texto);
    }
    return mapa;
  }, [sessao.celulas]);

  const aplicados = valemPara(edicoes, execucaoId);
  const htmlDe = (audiencia: Audiencia) => aplicados[audiencia] ?? originais[audiencia] ?? "";
  const audiencias = AUDIENCIAS.filter((audiencia) => htmlDe(audiencia) !== "");
  const audiencia: Audiencia | undefined = escolhida && audiencias.includes(escolhida) ? escolhida : audiencias[0];

  function guardar(dona: Audiencia, formatoEscolhido: FormatoDoTexto, html: string) {
    const dados: DadosDoTexto = { formato: formatoEscolhido, html };
    salvar({
      especie: "texto",
      titulo: derivarEstrutura(html).titulo,
      resumo: resumoDoTexto(formatoEscolhido, html),
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
        key={rodada}
        audiencias={audiencias}
        audiencia={audiencia}
        onMudarAudiencia={definirEscolhida}
        formato={formato}
        onMudarFormato={definirFormato}
        html={htmlDe(audiencia)}
        onAplicar={(html) => definirEdicoes((atuais) => comEdicao(atuais, execucaoId, audiencia, html))}
        onSalvar={(formatoEscolhido, html) => guardar(audiencia, formatoEscolhido, html)}
      />
    );

  if (sessao.fase === "vazia" && audiencia !== undefined) return tela;
  return (
    <FluxoDaGuia formato="texto_analitico" rotuloGerando="Gerando o texto…">
      {() => tela}
    </FluxoDaGuia>
  );
}
