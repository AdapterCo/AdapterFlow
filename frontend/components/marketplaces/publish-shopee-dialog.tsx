"use client";

import { useState } from "react";
import { useForm, useWatch } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { QueryError } from "@/components/data-state";
import {
  useMarketplacesOverview,
  useShopeeCategories,
  useShopeeCategoryAttributes,
  usePublishToShopee,
} from "@/hooks/use-marketplaces";
import { ProductWithDetails, ProductChannelPrice } from "@/types";
import { errorMessage, formatCurrency } from "@/lib/utils";
import { toast } from "sonner";
import Link from "next/link";
import { ShoppingBag, Loader2 } from "lucide-react";

const schema = z.object({
  account_id: z.string().uuid("Selecione uma conta válida da Shopee."),
  title: z.string().trim().min(1, "Título obrigatório.").max(120, "Máximo de 120 caracteres."),
  category_id: z.string().regex(/^[1-9][0-9]*$/, "Selecione ou informe uma categoria válida."),
  available_quantity: z.string().regex(/^[1-9][0-9]*$/, "Informe quantidade maior que zero."),
  description: z.string().optional(),
  attributes: z.record(z.string(), z.string()).optional(),
});

type Values = z.infer<typeof schema>;

type Props = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  product: ProductWithDetails;
  selectedChannelPrice?: ProductChannelPrice | null;
};

export function PublishShopeeDialog(props: Props) {
  return props.open ? <ShopeeEditor {...props} /> : null;
}

function ShopeeEditor({ open, onOpenChange, product, selectedChannelPrice: price }: Props) {
  const overview = useMarketplacesOverview();
  const publish = usePublishToShopee();
  const [requestId] = useState(() => crypto.randomUUID());

  const shopeeAccounts =
    overview.data?.accounts.filter(
      (a) =>
        a.marketplace === "SHOPEE" &&
        a.is_active &&
        a.verified_at &&
        !a.connection_error
    ) || [];

  const {
    register,
    control,
    handleSubmit,
    formState: { errors },
  } = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: {
      account_id: shopeeAccounts[0]?.id || "",
      title: product.name.slice(0, 120),
      category_id: "",
      available_quantity: "10",
      description: product.description || product.name,
      attributes: {},
    },
  });

  const accountId = useWatch({ control, name: "account_id" });
  const categoryIdStr = useWatch({ control, name: "category_id" });
  const categoryIdNum = categoryIdStr ? parseInt(categoryIdStr, 10) : 0;

  const categoriesQuery = useShopeeCategories(accountId);
  const attributesQuery = useShopeeCategoryAttributes(categoryIdNum, accountId);

  const submit = handleSubmit(async (values) => {
    if (!price || price.is_stale) {
      toast.error("Recalcule o preço da Shopee antes de publicar.");
      return;
    }
    try {
      const attributesPayload = values.attributes
        ? Object.entries(values.attributes)
            .filter(([, v]) => v.trim())
            .map(([attr_id, val]) => ({
              attribute_id: parseInt(attr_id, 10),
              attribute_value_list: [{ original_value_name: val.trim() }],
            }))
        : [];

      const result = await publish.mutateAsync({
        product_id: product.id,
        account_id: values.account_id,
        pricing_profile_id: price.pricing_profile_id,
        request_id: requestId,
        title: values.title,
        category_id: parseInt(values.category_id, 10),
        available_quantity: parseInt(values.available_quantity, 10),
        description: values.description || product.name,
        attributes: attributesPayload,
      });

      toast.success(`Anúncio publicado na Shopee! Status: ${result.status}`);
      if (result.error_message) toast.warning(result.error_message);
      onOpenChange(false);
    } catch (e) {
      toast.error(errorMessage(e));
    }
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] overflow-y-auto max-w-xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <ShoppingBag className="h-5 w-5 text-orange-500" />
            Publicar na Shopee
          </DialogTitle>
          <DialogDescription>
            Confirme os dados para anúncio oficial na Shopee. Preço calculado:{" "}
            <span className="font-semibold text-foreground">
              {formatCurrency(price?.calculated_price)}
            </span>
          </DialogDescription>
        </DialogHeader>

        {overview.isError ? (
          <QueryError error={overview.error} retry={() => overview.refetch()} />
        ) : (
          <form onSubmit={submit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1">
                Loja Shopee Conectada
              </label>
              {shopeeAccounts.length === 0 ? (
                <div className="p-3 border border-amber-200 bg-amber-50 dark:bg-amber-950/20 rounded-md text-sm text-amber-800 dark:text-amber-300">
                  Nenhuma loja Shopee conectada. Vá em{" "}
                  <Link href="/marketplaces" className="underline font-semibold">
                    Marketplaces
                  </Link>{" "}
                  para conectar sua loja.
                </div>
              ) : (
                <select
                  className="w-full border rounded-md p-2 text-sm bg-background"
                  {...register("account_id")}
                >
                  <option value="">Selecione uma loja</option>
                  {shopeeAccounts.map((acc) => (
                    <option key={acc.id} value={acc.id}>
                      {acc.account_name} (ID: {acc.seller_id})
                    </option>
                  ))}
                </select>
              )}
              {errors.account_id && (
                <p className="text-xs text-destructive mt-1">
                  {errors.account_id.message}
                </p>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">
                Título do Anúncio (máx. 120 caracteres)
              </label>
              <Input maxLength={120} {...register("title")} />
              {errors.title && (
                <p className="text-xs text-destructive mt-1">
                  {errors.title.message}
                </p>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">
                Categoria Shopee
              </label>
              {categoriesQuery.isLoading ? (
                <div className="flex items-center gap-2 text-sm text-muted-foreground p-2">
                  <Loader2 className="h-4 w-4 animate-spin" /> Carregando categorias...
                </div>
              ) : categoriesQuery.data && categoriesQuery.data.length > 0 ? (
                <select
                  className="w-full border rounded-md p-2 text-sm bg-background"
                  {...register("category_id")}
                >
                  <option value="">Selecione uma categoria da Shopee</option>
                  {categoriesQuery.data
                    .filter((cat) => !cat.has_children)
                    .map((cat) => (
                      <option key={cat.category_id} value={cat.category_id}>
                        {cat.display_category_name || cat.original_category_name} (ID: {cat.category_id})
                      </option>
                    ))}
                </select>
              ) : (
                <Input
                  type="number"
                  placeholder="ID numérico da categoria Shopee"
                  {...register("category_id")}
                />
              )}
              {errors.category_id && (
                <p className="text-xs text-destructive mt-1">
                  {errors.category_id.message}
                </p>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">
                Estoque Disponível
              </label>
              <Input inputMode="numeric" {...register("available_quantity")} />
              {errors.available_quantity && (
                <p className="text-xs text-destructive mt-1">
                  {errors.available_quantity.message}
                </p>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">
                Descrição Detalhada
              </label>
              <Textarea rows={4} {...register("description")} />
            </div>

            {attributesQuery.isLoading && (
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <Loader2 className="h-3.5 w-3.5 animate-spin" /> Carregando atributos obrigatórios...
              </div>
            )}

            {attributesQuery.data && attributesQuery.data.length > 0 && (
              <div className="space-y-3 pt-2 border-t">
                <p className="text-sm font-medium">Atributos da Categoria</p>
                {attributesQuery.data
                  .filter((attr) => attr.is_mandatory)
                  .map((attr) => (
                    <div key={attr.attribute_id}>
                      <label className="block text-xs font-medium mb-1">
                        {attr.display_attribute_name || attr.original_attribute_name} *
                      </label>
                      {attr.attribute_value_list && attr.attribute_value_list.length > 0 ? (
                        <select
                          className="w-full border rounded-md p-2 text-sm bg-background"
                          {...register(`attributes.${attr.attribute_id}`)}
                        >
                          <option value="">Selecione</option>
                          {attr.attribute_value_list.map((val) => (
                            <option
                              key={val.value_id}
                              value={val.display_value_name || val.original_value_name}
                            >
                              {val.display_value_name || val.original_value_name}
                            </option>
                          ))}
                        </select>
                      ) : (
                        <Input {...register(`attributes.${attr.attribute_id}`)} />
                      )}
                    </div>
                  ))}
              </div>
            )}

            {publish.isError && (
              <p className="text-sm text-destructive" role="alert">
                {errorMessage(publish.error)}{" "}
                <Link className="underline font-semibold" href="/publications">
                  Consultar publicações
                </Link>
              </p>
            )}

            <div className="pt-2 flex justify-end gap-2">
              <Button
                type="button"
                variant="outline"
                onClick={() => onOpenChange(false)}
              >
                Cancelar
              </Button>
              <Button
                type="submit"
                className="bg-orange-600 hover:bg-orange-700 text-white"
                disabled={
                  publish.isPending ||
                  publish.isSuccess ||
                  !price ||
                  price.is_stale ||
                  shopeeAccounts.length === 0
                }
              >
                {publish.isPending ? "Publicando na Shopee..." : "Publicar Anúncio na Shopee"}
              </Button>
            </div>
          </form>
        )}
      </DialogContent>
    </Dialog>
  );
}
