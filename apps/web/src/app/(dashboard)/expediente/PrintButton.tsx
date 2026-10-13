"use client";

export function PrintButton() {
  return (
    <button
      type="button"
      onClick={() => window.print()}
      className="min-h-11 rounded-md bg-lexi px-4 text-sm font-medium text-white"
    >
      Imprimir / Guardar como PDF
    </button>
  );
}
