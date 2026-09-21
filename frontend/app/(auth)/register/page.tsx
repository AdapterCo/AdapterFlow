import Link from "next/link";

export default function RegisterPage() {
  return <div className="space-y-4"><h2 className="text-2xl font-bold">Acesso administrativo</h2>
    <p>O AdapterFlow utiliza o operador configurado pelo administrador do servidor. O cadastro público de contas ainda não está disponível.</p>
    <Link href="/login" className="underline">Entrar com o acesso existente</Link></div>;
}
