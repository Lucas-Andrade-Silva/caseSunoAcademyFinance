import { Link, Navigate, Route, Routes } from "react-router-dom";
import Layout from "./componentes/Layout";
import Curadoria from "./paginas/Curadoria";
import Fontes from "./paginas/Fontes";
import Saidas from "./paginas/Saidas";
import SaidaAberta from "./paginas/SaidaAberta";
import CelulaAberta from "./paginas/CelulaAberta";

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
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Navigate to="/saidas" replace />} />
        <Route path="/fontes" element={<Fontes />} />
        <Route path="/curadoria" element={<Curadoria />} />
        <Route path="/saidas" element={<Saidas />} />
        <Route path="/saidas/:id" element={<SaidaAberta />} />
        <Route
          path="/saidas/:id/celulas/:audiencia/:formato"
          element={<CelulaAberta />}
        />
        <Route path="*" element={<NaoEncontrada />} />
      </Routes>
    </Layout>
  );
}
