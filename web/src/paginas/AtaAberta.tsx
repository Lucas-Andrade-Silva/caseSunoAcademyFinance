// A Ata aberta ("/fontes/:id"): o texto integral do comunicado, para conferir a fonte antes de
// selecioná-la na Curadoria. Lê `GET /api/atas/{id}`, o mesmo arquivo em `data/atas/`.
import { Link, useParams } from "react-router-dom";
import { obterAta } from "../dados/cliente";
import { usarRequisicao } from "../ganchos/usarRequisicao";
import { Carregando, MensagemErro } from "../componentes/EstadoRequisicao";
import { usarSelecaoDeAtas } from "../ganchos/SelecaoDeAtas";
import TextoDaAta from "../componentes/TextoDaAta";
import { formatarDataDoDia } from "../texto/rotulos";

export default function AtaAberta() {
  const { id } = useParams<{ id: string }>();
  const identificador = id ?? "";
  const estado = usarRequisicao(() => obterAta(identificador), [identificador]);
  const { selecao, alternar } = usarSelecaoDeAtas();

  if (estado.situacao === "carregando") return <Carregando rotulo="Carregando Ata…" />;
  if (estado.situacao === "erro") return <MensagemErro erro={estado.erro} />;

  const ata = estado.dados;
  const selecionada = selecao.includes(ata.identificador);

  return (
    <div className="px-5 py-4">
      <nav className="mb-1 text-[11.5px] text-suave">
        <Link to="/fontes" className="hover:text-texto">
          Fontes
        </Link>{" "}
        › {ata.titulo}
      </nav>
      <div className="mb-3 flex flex-wrap items-center gap-3">
        <h1 className="text-[17px] font-bold">{ata.titulo}</h1>
        <small className="text-xs text-suave">{formatarDataDoDia(ata.data_referencia)}</small>
        <div className="flex-1" />
        {ata.origem_url && (
          <a
            href={ata.origem_url}
            target="_blank"
            rel="noreferrer"
            className="text-xs font-semibold text-suave hover:text-texto hover:underline"
          >
            Abrir original
          </a>
        )}
        <button
          type="button"
          onClick={() => alternar(ata.identificador)}
          className="rounded-full bg-suno px-4 py-1.5 text-xs font-bold uppercase tracking-wide text-white"
        >
          {selecionada ? "Remover da seleção" : "Selecionar"}
        </button>
      </div>
      <TextoDaAta texto={ata.texto} />
    </div>
  );
}
