export default function PlaceholderPage() {
  return (
    <div className="flex flex-col items-center justify-center h-[60vh] text-center space-y-4">
      <div className="h-20 w-20 bg-zinc-100 rounded-full flex items-center justify-center">
        <div className="h-10 w-10 border-4 border-zinc-200 border-t-zinc-400 rounded-full animate-spin" />
      </div>
      <h2 className="text-2xl font-bold tracking-tight text-zinc-800">Em Desenvolvimento</h2>
      <p className="text-muted-foreground max-w-md">
        Esta funcionalidade estará disponível em uma versão futura. Estamos trabalhando para trazer os melhores recursos para você.
      </p>
    </div>
  );
}
