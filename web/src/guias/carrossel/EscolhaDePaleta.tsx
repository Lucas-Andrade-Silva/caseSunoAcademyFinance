// As paletas prontas: nome e as quatro cores (fundo, texto, destaque, apoio). Escolha única.
import type { Paleta } from "./modelo";
import Opcao, { Opcoes } from "./Opcao";
import { PALETAS } from "./paletas";

function Cores({ paleta, selecionada }: { paleta: Paleta; selecionada: boolean }) {
  return (
    <span className="flex items-center gap-1.5" aria-hidden="true">
      {[paleta.fundo, paleta.texto, paleta.destaque, paleta.apoio].map((cor) => (
        <span
          key={cor}
          className={`h-[18px] w-[18px] rounded-full ring-1 ring-inset ${selecionada ? "ring-black/30" : "ring-white/30"}`}
          style={{ background: cor }}
        />
      ))}
    </span>
  );
}

export default function EscolhaDePaleta({
  valor,
  aoEscolher,
}: {
  valor: string;
  aoEscolher: (paleta: Paleta) => void;
}) {
  return (
    <Opcoes rotuloAcessivel="Paleta de cores" largura={112}>
      {PALETAS.map((paleta) => (
        <Opcao
          key={paleta.id}
          rotulo={paleta.nome}
          selecionada={paleta.id === valor}
          onClick={() => aoEscolher(paleta)}
          className="h-[76px]"
        >
          <Cores paleta={paleta} selecionada={paleta.id === valor} />
        </Opcao>
      ))}
    </Opcoes>
  );
}
