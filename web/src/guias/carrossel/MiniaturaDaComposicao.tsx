// O desenho esquemático de cada composição, em traço de uma cor só (`currentColor`): serve de
// miniatura na escolha dos tipos e de ícone nas linhas dos exemplos.
import type { Composicao } from "./modelo";

function Desenho({ composicao }: { composicao: Composicao }) {
  switch (composicao) {
    case "minimalista":
      return (
        <>
          <rect x="9" y="15" width="18" height="4" rx="1" />
          <rect x="13" y="22" width="10" height="1.6" rx="0.8" />
          <rect x="11" y="27" width="14" height="2" rx="1" opacity=".55" />
          <rect x="14" y="31" width="8" height="2" rx="1" opacity=".55" />
        </>
      );
    case "infografico":
      return (
        <>
          <rect x="5" y="8" width="22" height="3.2" rx="1" />
          <rect x="5" y="17" width="11" height="19" rx="1.8" opacity=".5" />
          <rect x="19" y="29" width="4" height="7" rx="1" />
          <rect x="24.5" y="22" width="4" height="14" rx="1" />
          <rect x="30" y="26" width="3" height="10" rx="1" opacity=".6" />
        </>
      );
    case "comparativo":
      return (
        <>
          <rect x="8" y="7" width="20" height="3.2" rx="1" />
          <rect x="5" y="15" width="12.5" height="16" rx="2" opacity=".5" />
          <rect x="18.5" y="15" width="12.5" height="16" rx="2" />
          <rect x="5" y="34" width="26" height="5" rx="1.5" opacity=".35" />
        </>
      );
    case "estatistico":
      return (
        <>
          <rect x="9" y="7" width="18" height="3.2" rx="1" />
          <rect x="7" y="16" width="22" height="9" rx="2.5" />
          <rect x="9" y="31" width="18" height="2" rx="1" opacity=".55" />
          <rect x="11" y="35" width="14" height="2" rx="1" opacity=".55" />
        </>
      );
    case "narrativo":
      return (
        <>
          <rect x="6" y="7" width="5" height="19" rx="1" opacity=".3" />
          <rect x="6" y="28" width="22" height="3.5" rx="1" />
          <rect x="6" y="34" width="24" height="6" rx="1.8" opacity=".5" />
        </>
      );
    default:
      return (
        <>
          <rect x="5" y="8" width="15" height="4" rx="1" />
          <rect x="5" y="14" width="11" height="4" rx="1" />
          <rect x="19" y="21" width="12" height="16" rx="2" opacity=".5" />
          <circle cx="8" cy="37" r="4" opacity=".35" />
        </>
      );
  }
}

export default function MiniaturaDaComposicao({
  composicao,
  altura = 46,
}: {
  composicao: Composicao;
  altura?: number;
}) {
  return (
    <svg
      viewBox="0 0 36 46"
      height={altura}
      width={(altura * 36) / 46}
      fill="currentColor"
      aria-hidden="true"
    >
      <rect x="0.75" y="0.75" width="34.5" height="44.5" rx="3.5" fill="none" stroke="currentColor" strokeOpacity=".45" strokeWidth="1.5" />
      <Desenho composicao={composicao} />
    </svg>
  );
}
