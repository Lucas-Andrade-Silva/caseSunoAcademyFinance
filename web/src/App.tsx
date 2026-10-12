import { Link, Navigate, Route, Routes, useLocation } from "react-router-dom";
import Layout from "./componentes/Layout";
import LimiteDeErro from "./componentes/LimiteDeErro";
import { ProvedorDeSelecao } from "./ganchos/SelecaoDeAtas";
import Curadoria from "./paginas/Curadoria";
import AtaAberta from "./paginas/AtaAberta";
import Fontes from "./paginas/Fontes";
import Saidas from "./paginas/Saidas";
import SaidaAberta from "./paginas/SaidaAberta";
import CelulaAberta from "./paginas/CelulaAberta";
import ReferenciasVisuais from "./paginas/ReferenciasVisuais";

function NaoEncontrada() {
  return (
    <div className="px-5 py-12 text-center">
      <p className="text-lg font-medium">Página não encontrada.</p>
      <Link to="/saidas" className="mt-2 inline-block text-suno hover:underline">
        Voltar para as Saídas
      </Link>
    </div>
  );
}

export default function App() {
  const { pathname } = useLocation();
  return (
    <ProvedorDeSelecao>
      <Layout>
        {/* `key` zera o limite ao trocar de rota: sair da tela quebrada a destrava. */}
        <LimiteDeErro key={pathname}>
        <Routes>
          <Route path="/" element={<Navigate to="/saidas" replace />} />
          <Route path="/fontes" element={<Fontes />} />
          <Route path="/fontes/:id" element={<AtaAberta />} />
          <Route path="/curadoria" element={<Curadoria />} />
          <Route path="/referencias" element={<ReferenciasVisuais />} />
          <Route path="/saidas" element={<Saidas />} />
          <Route path="/saidas/:id" element={<SaidaAberta />} />
          <Route
            path="/saidas/:id/celulas/:audiencia/:formato"
            element={<CelulaAberta />}
          />
          <Route path="*" element={<NaoEncontrada />} />
        </Routes>
        </LimiteDeErro>
      </Layout>
    </ProvedorDeSelecao>
  );
}
