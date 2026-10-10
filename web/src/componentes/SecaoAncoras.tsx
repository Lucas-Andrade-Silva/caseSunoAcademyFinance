// As Âncoras citadas pela Célula, sempre visíveis ao lado do conteúdo.
import type { AncoraNumerica } from "../dados/cliente";
import Ancoras from "./Ancoras";
import Chip from "./Chip";

export default function SecaoAncoras({ ancoras }: { ancoras: AncoraNumerica[] }) {
  return (
    <section className="rounded-2xl bg-cartao p-3.5">
      <h2 className="mb-2 flex items-center gap-2 text-[12.5px] font-bold">
        Âncoras citadas <Chip>{ancoras.length}</Chip>
      </h2>
      <Ancoras ancoras={ancoras} />
    </section>
  );
}
