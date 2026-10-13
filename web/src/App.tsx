// A casca do app: a barra lateral e as seis vistas (guias). Todas as vistas ficam montadas o
// tempo todo, e a troca de guia é só um deslize com desvanecer (`.vista`, em global.css): o
// que cada guia já leu, digitou ou gerou continua lá, e nada recarrega. A vista que entra
// desliza do lado em que a guia está na barra.
import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";
import BarraLateral from "./interface/BarraLateral";
import LimiteDeErro from "./interface/LimiteDeErro";
import { ProvedorDeConfiguracoes } from "./nucleo/configuracoes";
import { GUIAS, guiaDoCaminho, type IdDaGuia } from "./nucleo/guias";
import { ProvedorDeHistorico } from "./nucleo/historico";
import { usarPrecarga } from "./nucleo/precarga";
import { ProvedorDeSelecao } from "./nucleo/selecao";
import { ProvedorDeSessoes } from "./nucleo/sessao";
import GuiaCarrossel from "./guias/carrossel";
import GuiaConfiguracoes from "./guias/configuracoes";
import GuiaHistorico from "./guias/historico";
import GuiaIngestao from "./guias/ingestao";
import GuiaTexto from "./guias/texto";
import GuiaVideo from "./guias/video";

const VISTAS: Record<IdDaGuia, ReactNode> = {
  ingestao: <GuiaIngestao />,
  texto: <GuiaTexto />,
  carrossel: <GuiaCarrossel />,
  video: <GuiaVideo />,
  historico: <GuiaHistorico />,
  configuracoes: <GuiaConfiguracoes />,
};

function Vistas() {
  const { pathname } = useLocation();
  usarPrecarga();
  const ativa = guiaDoCaminho(pathname);
  if (!ativa) return <Navigate to="/ingestao" replace />;
  const indiceAtivo = GUIAS.findIndex((guia) => guia.id === ativa.id);

  return (
    <>
      <BarraLateral />
      <main className="absolute inset-0 overflow-clip max-lg:bottom-[76px]">
        {GUIAS.map((guia, indice) => (
          <div
            key={guia.id}
            className="vista"
            data-posicao={indice < indiceAtivo ? "antes" : indice > indiceAtivo ? "depois" : "ativa"}
            aria-hidden={indice !== indiceAtivo}
            inert={indice !== indiceAtivo}
          >
            <LimiteDeErro>{VISTAS[guia.id]}</LimiteDeErro>
          </div>
        ))}
      </main>
    </>
  );
}

export default function App() {
  return (
    <ProvedorDeConfiguracoes>
      <ProvedorDeSelecao>
        <ProvedorDeSessoes>
          <ProvedorDeHistorico>
            <Vistas />
          </ProvedorDeHistorico>
        </ProvedorDeSessoes>
      </ProvedorDeSelecao>
    </ProvedorDeConfiguracoes>
  );
}
