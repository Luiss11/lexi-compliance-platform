export default function EvidenciasPage() {
  // TODO(Yosvanni): POST /evidence/{taskId} devuelve el SHA-256 y el veredicto del agente
  return (
    <div className="flex flex-col gap-6">
      <h1 className="font-serif text-3xl font-semibold">Evidencias</h1>
      <p className="text-sm text-muted">Cada archivo se sella con SHA-256 al subirse.</p>
    </div>
  );
}
