// Estrutura o texto corrido que o `pypdf` extrai de uma Ata: título da capa, ficha da reunião,
// seções ("A) …"), parágrafos numerados e notas de rodapé. Lógica pura, sem React nem rede, por
// isso o Vitest cobre. O texto de origem nunca é alterado em `data/atas/`; isto é só apresentação.

type BlocoDaAta =
  | { tipo: "secao"; texto: string }
  | { tipo: "paragrafo"; numero: string | null; texto: string }
  | { tipo: "tabela"; legenda: string[]; cabecalho: string[]; linhas: string[][] };

interface AtaEstruturada {
  /** Linhas da capa ("Ata da Reunião do / Comitê… / data"); vazio se o texto não tem capa. */
  capa: string[];
  /** Data, local, horários e presentes, linha a linha. */
  ficha: string[];
  corpo: BlocoDaAta[];
  notas: string[];
}

const CABECALHO_DE_PAGINA = /^\d+\s+bcb\.gov\.br\s*$/;
const REUNIAO_NO_RODAPE = /^\d+ª Reunião\s*$/;
const DATA_NO_RODAPE = /^\d{1,2}( e \d{1,2})? de \p{L}+\s*$/u;
const SECAO = /^[A-Z]\)\s+\S/;
const NUMERADO = /^(\d+)\.\s+(\S.*)$/;
const NOTA = /^\d+\s+\p{Lu}/u;
const TABELA = /^Tabela \d+\s*$/;
const CELULA = /\d+º tri \d{4}|[\d.,]+/g;
const INICIO_DO_CORPO = /^(Os membros\b|[A-Z]\)\s+\S)/;

/** Tira o cabeçalho que se repete a cada página ("N bcb.gov.br", "281ª Reunião / COPOM / data"). */
function semCabecalhos(linhas: string[]): string[] {
  const saida: string[] = [];
  for (let i = 0; i < linhas.length; i++) {
    const linha = linhas[i].trim();
    if (CABECALHO_DE_PAGINA.test(linha)) continue;
    if (REUNIAO_NO_RODAPE.test(linha) && linhas[i + 1]?.trim() === "COPOM") {
      i += 1;
      if (DATA_NO_RODAPE.test(linhas[i + 1]?.trim() ?? "")) i += 1;
      continue;
    }
    saida.push(linhas[i]);
  }
  return saida;
}

/** Junta linhas quebradas pela largura do PDF e conserta o espaço solto antes de pontuação. */
export function juntarLinhas(linhas: string[]): string {
  return linhas
    .map((l) => l.trim())
    .filter(Boolean)
    .join(" ")
    .replace(/\s+([,.;:)])/g, "$1")
    .replace(/\s+-(se|lhe|nos|la|lo|los|las)\b/g, "-$1")
    .replace(/\s{2,}/g, " ");
}

/** "IPCA livres  5,2  4,1" → ["IPCA livres", "5,2", "4,1"]; o rótulo vai até o primeiro número. */
function celulasDaLinha(linha: string): string[] {
  const t = linha.trim();
  const inicio = t.search(/\s\d/);
  if (inicio < 0) return [t];
  return [t.slice(0, inicio).trim(), ...(t.slice(inicio).match(CELULA) ?? [])];
}

export function estruturarAta(texto: string): AtaEstruturada {
  const todas = semCabecalhos(texto.replace(/\r\n?/g, "\n").split("\n"));
  const iData = todas.findIndex((l) => l.trim().startsWith("Data:"));
  const iCorpo = todas.findIndex((l, i) => i > Math.max(iData, -1) && INICIO_DO_CORPO.test(l.trim()));
  const temFicha = iData >= 0 && iCorpo > iData;

  const capa = iData > 0 ? todas.slice(0, iData).map((l) => l.trim()).filter(Boolean) : [];
  const ficha = temFicha ? todas.slice(iData, iCorpo).map((l) => l.trimEnd()) : [];
  const linhasDoCorpo = temFicha ? todas.slice(iCorpo) : todas;

  const corpo: BlocoDaAta[] = [];
  const notas: string[] = [];
  let atual: { numero: string | null; linhas: string[] } | null = null;

  const fechar = () => {
    if (atual) {
      const texto = juntarLinhas(atual.linhas);
      if (texto) corpo.push({ tipo: "paragrafo", numero: atual.numero, texto });
    }
    atual = null;
  };

  let legenda: string[] | null = null;
  const trechos = linhasDoCorpo.join("\n").split(/\n\s*\n/);
  for (const trecho of trechos) {
    const linhas = trecho.split("\n").filter((l) => l.trim() !== "");
    if (linhas.length === 0) continue;
    const primeira = linhas[0].trim();

    if (legenda) {
      const [cabecalho, ...resto] = linhas.map(celulasDaLinha);
      corpo.push({ tipo: "tabela", legenda, cabecalho, linhas: resto });
      legenda = null;
      continue;
    }
    if (TABELA.test(primeira)) {
      fechar();
      legenda = linhas.map((l) => l.trim());
      continue;
    }

    if (NOTA.test(primeira) && !NUMERADO.test(primeira)) {
      notas.push(juntarLinhas(linhas));
      continue;
    }
    // Um trecho que começa em minúscula é a continuação do parágrafo cortado pela quebra de página.
    const continuacao = /^\p{Ll}/u.test(primeira) && atual !== null;
    if (!continuacao) fechar();

    for (const crua of linhas) {
      const linha = crua.trim();
      const numerado = NUMERADO.exec(linha);
      if (SECAO.test(linha)) {
        fechar();
        corpo.push({ tipo: "secao", texto: linha });
      } else if (numerado) {
        fechar();
        atual = { numero: numerado[1], linhas: [numerado[2]] };
      } else {
        atual = atual ?? { numero: null, linhas: [] };
        atual.linhas.push(linha);
      }
    }
  }
  fechar();

  return { capa, ficha, corpo, notas };
}
