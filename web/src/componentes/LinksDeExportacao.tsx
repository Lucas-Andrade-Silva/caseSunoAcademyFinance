// Os três formatos de exportação de uma Saída. O navegador baixa direto da API.
import { urlDeExportacao, type FormatoExportacao } from "../dados/cliente";

const OPCOES: ReadonlyArray<{ formato: FormatoExportacao; rotulo: string }> = [
  { formato: "json", rotulo: "JSON (dados completos)" },
  { formato: "md", rotulo: "Markdown (para ler)" },
  { formato: "zip", rotulo: "ZIP (tudo, com o Pacote)" },
];

export default function LinksDeExportacao({ identificador }: { identificador: string }) {
  return (
    <ul className="space-y-1">
      {OPCOES.map((opcao) => (
        <li key={opcao.formato}>
          <a
            href={urlDeExportacao(identificador, opcao.formato)}
            download
            className="text-sm text-texto underline-offset-2 hover:underline"
          >
            {opcao.rotulo}
          </a>
        </li>
      ))}
    </ul>
  );
}
