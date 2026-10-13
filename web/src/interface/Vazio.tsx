// O estado vazio e o de falha: uma frase curta e, se houver, a saída. Sem ilustração nem
// explicação do que a tela faz.
import type { ReactNode } from "react";

export default function Vazio({
  titulo,
  detalhe,
  acao,
  tom = "mudo",
}: {
  titulo: string;
  detalhe?: string;
  acao?: ReactNode;
  tom?: "mudo" | "coral";
}) {
  return (
    <div
      role={tom === "coral" ? "alert" : undefined}
      className="surge mx-auto flex max-w-[420px] flex-col items-center gap-5 px-6 py-20 text-center"
    >
      <p className={`text-[20px] leading-snug ${tom === "coral" ? "text-coral-claro" : "text-claro"}`}>{titulo}</p>
      {detalhe && <p className="text-[15px] leading-relaxed text-etiqueta">{detalhe}</p>}
      {acao}
    </div>
  );
}
