// Guia que ainda não tem conteúdo: avisa e diz o que vai fazer.
export default function EmConstrucao({
  titulo,
  descricao,
}: {
  titulo: string;
  descricao: string;
}) {
  return (
    <div className="px-5 py-4">
      <h1 className="text-[17px] font-bold">{titulo}</h1>
      <div className="mt-4 rounded-2xl border border-dashed border-linha p-6 text-sm text-suave">
        <p className="font-semibold text-texto">Esta guia chega em breve.</p>
        <p className="mt-1">{descricao}</p>
      </div>
    </div>
  );
}
