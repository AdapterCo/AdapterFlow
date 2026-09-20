import { Button } from "@/components/ui/button";
import { errorMessage } from "@/lib/utils";
export function QueryError({ error, retry }: { error: unknown; retry: () => void }) {
  return <div role="alert" className="rounded border border-red-300 p-4 space-y-2"><p>{errorMessage(error)}</p><Button variant="outline" onClick={retry}>Tentar novamente</Button></div>;
}
export function Pagination({ offset, total, pageSize = 50, onChange }: { offset: number; total: number; pageSize?: number; onChange: (offset: number) => void }) {
  return <div className="flex items-center gap-4 py-4"><Button variant="outline" disabled={offset === 0} onClick={() => onChange(Math.max(0, offset - pageSize))}>Anterior</Button><span>{total ? `${offset + 1}–${Math.min(offset + pageSize, total)} de ${total}` : "Nenhum registro"}</span><Button variant="outline" disabled={offset + pageSize >= total} onClick={() => onChange(offset + pageSize)}>Próxima</Button></div>;
}
