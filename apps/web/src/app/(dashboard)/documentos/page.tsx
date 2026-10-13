export default function DocumentosPage() {
  // TODO(Yubel/Yosvanni): subida a POST /documents y listado desde Prisma
  return (
    <div className="flex flex-col gap-6">
      <h1 className="font-serif text-3xl font-semibold">Biblioteca de documentos</h1>
      <div className="rounded-xl border-2 border-dashed border-[#B9B4A6] bg-white p-7">
        <p className="font-semibold">Arrastra PDFs aquí o selecciónalos</p>
        <p className="text-sm text-muted">Se conservan página y cláusula para las citas.</p>
      </div>
    </div>
  );
}
