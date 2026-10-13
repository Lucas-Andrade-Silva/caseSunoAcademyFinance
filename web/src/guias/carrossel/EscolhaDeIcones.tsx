// Os ícones que não podem faltar: o catálogo do vídeo, em SVG. Escolhe um, vários ou nenhum.
import { desenhoDoIcone } from "./icones";
import { IDS_DE_ICONES } from "./idsDeIcones";
import type { IdDoIcone } from "./modelo";
import Opcao, { Opcoes } from "./Opcao";

export default function EscolhaDeIcones({
  marcados,
  aoAlternar,
}: {
  marcados: readonly IdDoIcone[];
  aoAlternar: (id: IdDoIcone) => void;
}) {
  return (
    <Opcoes rotuloAcessivel="Ícones do carrossel" largura={92}>
      {IDS_DE_ICONES.map(({ id, rotulo }) => {
        const Desenho = desenhoDoIcone(id);
        return (
          <Opcao
            key={id}
            rotulo={rotulo}
            selecionada={marcados.includes(id)}
            onClick={() => aoAlternar(id)}
            className="h-[84px]"
          >
            <Desenho size={24} />
          </Opcao>
        );
      })}
    </Opcoes>
  );
}
