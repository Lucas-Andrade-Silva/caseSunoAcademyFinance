import { Link, Route, Routes } from "react-router-dom";
import Layout from "./componentes/Layout";
import Execucoes from "./paginas/Execucoes";
import Matriz from "./paginas/Matriz";
import CelulaVista from "./paginas/CelulaVista";
import Filas from "./paginas/Filas";
import Pacotes from "./paginas/Pacotes";

function NaoEncontrada() {
  return (
    <div className="py-12 text-center">
      <p className="text-lg font-medium">Página não encontrada.</p>
      <Link to="/" className="mt-2 inline-block text-indigo-600 hover:underline dark:text-indigo-400">
        Voltar para as execuções
      </Link>
    </div>
  );
}

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Execucoes />} />
        <Route path="/execucoes/:id" element={<Matriz />} />
        <Route path="/execucoes/:id/celulas/:audiencia/:formato" element={<CelulaVista />} />
        <Route path="/execucoes/:id/filas" element={<Filas />} />
        <Route path="/execucoes/:id/pacotes" element={<Pacotes />} />
        <Route path="*" element={<NaoEncontrada />} />
      </Routes>
    </Layout>
  );
}
