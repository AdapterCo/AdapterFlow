"use client";

import React, { useState, useEffect } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  PricingProfile,
  PricingProfileCreate,
  PricingProfileUpdate,
} from "@/types";
import { toast } from "sonner";
import {
  useCreatePricingProfile,
  useUpdatePricingProfile,
} from "@/hooks/use-pricing";

interface ProfileDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  profileToEdit?: PricingProfile | null;
}

export function ProfileDialog({
  open,
  onOpenChange,
  profileToEdit,
}: ProfileDialogProps) {
  const isEditing = !!profileToEdit;
  const createMutation = useCreatePricingProfile();
  const updateMutation = useUpdatePricingProfile();

  const [formData, setFormData] = useState({
    name: "",
    description: "",
    channel: "MERCADO_LIVRE",
    marketplace_commission_percent: "14.0",
    fixed_fee: "6.00",
    fixed_fee_threshold: "79.00",
    tax_percent: "6.0",
    operating_cost_percent: "3.0",
    fixed_cost: "3.50",
    target_margin_percent: "15.0",
    free_shipping_threshold: "79.00",
    free_shipping_cost: "18.00",
    rounding_rule: "ENDS_90",
    is_default: false,
    is_active: true,
  });

  useEffect(() => {
    if (profileToEdit) {
      setFormData({
        name: profileToEdit.name || "",
        description: profileToEdit.description || "",
        channel: profileToEdit.channel || "CUSTOM",
        marketplace_commission_percent:
          profileToEdit.marketplace_commission_percent || "0.0",
        fixed_fee: profileToEdit.fixed_fee || "0.0",
        fixed_fee_threshold: profileToEdit.fixed_fee_threshold || "",
        tax_percent: profileToEdit.tax_percent || "0.0",
        operating_cost_percent: profileToEdit.operating_cost_percent || "0.0",
        fixed_cost: profileToEdit.fixed_cost || "0.0",
        target_margin_percent: profileToEdit.target_margin_percent || "15.0",
        free_shipping_threshold: profileToEdit.free_shipping_threshold || "",
        free_shipping_cost: profileToEdit.free_shipping_cost || "",
        rounding_rule: profileToEdit.rounding_rule || "ENDS_90",
        is_default: profileToEdit.is_default ?? false,
        is_active: profileToEdit.is_active ?? true,
      });
    } else {
      setFormData({
        name: "",
        description: "",
        channel: "MERCADO_LIVRE",
        marketplace_commission_percent: "14.0",
        fixed_fee: "6.00",
        fixed_fee_threshold: "79.00",
        tax_percent: "6.0",
        operating_cost_percent: "3.0",
        fixed_cost: "3.50",
        target_margin_percent: "15.0",
        free_shipping_threshold: "79.00",
        free_shipping_cost: "18.00",
        rounding_rule: "ENDS_90",
        is_default: false,
        is_active: true,
      });
    }
  }, [profileToEdit, open]);

  const handleChange = (field: string, value: any) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!formData.name.trim()) {
      toast.error("Informe o nome do perfil.");
      return;
    }

    try {
      const payload: PricingProfileCreate = {
        name: formData.name.trim(),
        description: formData.description.trim() || null,
        channel: formData.channel,
        marketplace_commission_percent: formData.marketplace_commission_percent || "0",
        fixed_fee: formData.fixed_fee || "0",
        fixed_fee_threshold: formData.fixed_fee_threshold.trim()
          ? formData.fixed_fee_threshold.trim()
          : null,
        tax_percent: formData.tax_percent || "0",
        operating_cost_percent: formData.operating_cost_percent || "0",
        fixed_cost: formData.fixed_cost || "0",
        target_margin_percent: formData.target_margin_percent || "0",
        free_shipping_threshold: formData.free_shipping_threshold.trim()
          ? formData.free_shipping_threshold.trim()
          : null,
        free_shipping_cost: formData.free_shipping_cost.trim()
          ? formData.free_shipping_cost.trim()
          : null,
        rounding_rule: formData.rounding_rule,
        is_default: formData.is_default,
        is_active: formData.is_active,
      };

      if (isEditing && profileToEdit) {
        await updateMutation.mutateAsync({
          id: profileToEdit.id,
          data: payload as PricingProfileUpdate,
        });
        toast.success("Perfil de precificação atualizado com sucesso!");
      } else {
        await createMutation.mutateAsync(payload);
        toast.success("Perfil de precificação criado com sucesso!");
      }
      onOpenChange(false);
    } catch (err: any) {
      toast.error(err.message || "Erro ao salvar perfil.");
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>
            {isEditing ? "Editar Perfil de Precificação" : "Novo Perfil de Canal / Precificação"}
          </DialogTitle>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4 py-2">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-1 sm:col-span-2">
              <Label htmlFor="name">Nome do Perfil *</Label>
              <Input
                id="name"
                value={formData.name}
                onChange={(e) => handleChange("name", e.target.value)}
                placeholder="Ex: Mercado Livre - Clássico (14%)"
                required
              />
            </div>

            <div className="space-y-1">
              <Label htmlFor="channel">Canal / Marketplace</Label>
              <select
                id="channel"
                className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-xs transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                value={formData.channel}
                onChange={(e) => handleChange("channel", e.target.value)}
              >
                <option value="MERCADO_LIVRE">Mercado Livre</option>
                <option value="SHOPEE">Shopee</option>
                <option value="AMAZON">Amazon</option>
                <option value="TIKTOK">TikTok Shop</option>
                <option value="CUSTOM">Outro / Customizado</option>
              </select>
            </div>

            <div className="space-y-1">
              <Label htmlFor="rounding_rule">Regra de Arredondamento</Label>
              <select
                id="rounding_rule"
                className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-xs transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                value={formData.rounding_rule}
                onChange={(e) => handleChange("rounding_rule", e.target.value)}
              >
                <option value="ENDS_90">Terminar em .90 (R$ XX,90)</option>
                <option value="ENDS_99">Terminar em .99 (R$ XX,99)</option>
                <option value="ROUND_INTEGER">Inteiro Acima (R$ XX,00)</option>
                <option value="EXACT">Exato (Centavos Naturais)</option>
              </select>
            </div>

            <div className="space-y-1">
              <Label htmlFor="marketplace_commission_percent">Comissão do Marketplace (%)</Label>
              <Input
                id="marketplace_commission_percent"
                type="number"
                step="0.01"
                value={formData.marketplace_commission_percent}
                onChange={(e) =>
                  handleChange("marketplace_commission_percent", e.target.value)
                }
              />
            </div>

            <div className="space-y-1">
              <Label htmlFor="target_margin_percent">Margem Líquida Alvo (%)</Label>
              <Input
                id="target_margin_percent"
                type="number"
                step="0.01"
                value={formData.target_margin_percent}
                onChange={(e) =>
                  handleChange("target_margin_percent", e.target.value)
                }
              />
            </div>

            <div className="space-y-1">
              <Label htmlFor="tax_percent">Impostos sobre Faturamento (%)</Label>
              <Input
                id="tax_percent"
                type="number"
                step="0.01"
                value={formData.tax_percent}
                onChange={(e) => handleChange("tax_percent", e.target.value)}
              />
            </div>

            <div className="space-y-1">
              <Label htmlFor="operating_cost_percent">Custo Operacional Percentual (%)</Label>
              <Input
                id="operating_cost_percent"
                type="number"
                step="0.01"
                value={formData.operating_cost_percent}
                onChange={(e) =>
                  handleChange("operating_cost_percent", e.target.value)
                }
              />
            </div>

            <div className="space-y-1">
              <Label htmlFor="fixed_cost">Custo Fixo Embalagem / Manuseio (R$)</Label>
              <Input
                id="fixed_cost"
                type="number"
                step="0.01"
                value={formData.fixed_cost}
                onChange={(e) => handleChange("fixed_cost", e.target.value)}
              />
            </div>

            <div className="space-y-1">
              <Label htmlFor="fixed_fee">Taxa Fixa do Marketplace (R$)</Label>
              <Input
                id="fixed_fee"
                type="number"
                step="0.01"
                value={formData.fixed_fee}
                onChange={(e) => handleChange("fixed_fee", e.target.value)}
              />
            </div>

            <div className="space-y-1">
              <Label htmlFor="fixed_fee_threshold">Limiar de Taxa Fixa (R$)</Label>
              <Input
                id="fixed_fee_threshold"
                type="number"
                step="0.01"
                placeholder="Ex: 79.00 (aplica se < 79)"
                value={formData.fixed_fee_threshold}
                onChange={(e) =>
                  handleChange("fixed_fee_threshold", e.target.value)
                }
              />
            </div>

            <div className="space-y-1">
              <Label htmlFor="free_shipping_threshold">Limiar de Frete Grátis (R$)</Label>
              <Input
                id="free_shipping_threshold"
                type="number"
                step="0.01"
                placeholder="Ex: 79.00 (aplica se >= 79)"
                value={formData.free_shipping_threshold}
                onChange={(e) =>
                  handleChange("free_shipping_threshold", e.target.value)
                }
              />
            </div>

            <div className="space-y-1 sm:col-span-2">
              <Label htmlFor="free_shipping_cost">Custo Médio de Frete do Vendedor (R$)</Label>
              <Input
                id="free_shipping_cost"
                type="number"
                step="0.01"
                placeholder="Ex: 18.00"
                value={formData.free_shipping_cost}
                onChange={(e) =>
                  handleChange("free_shipping_cost", e.target.value)
                }
              />
            </div>

            <div className="space-y-1 sm:col-span-2">
              <Label htmlFor="description">Descrição / Notas Internas</Label>
              <Input
                id="description"
                value={formData.description}
                onChange={(e) => handleChange("description", e.target.value)}
                placeholder="Ex: Anúncio clássico sem parcelamento sem juros"
              />
            </div>

            <div className="flex items-center gap-2 pt-2 sm:col-span-2">
              <input
                type="checkbox"
                id="is_default"
                checked={formData.is_default}
                onChange={(e) => handleChange("is_default", e.target.checked)}
                className="h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary"
              />
              <Label htmlFor="is_default" className="cursor-pointer font-normal">
                Definir como perfil padrão para este canal
              </Label>
            </div>
          </div>

          <DialogFooter className="pt-4 border-t">
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
            >
              Cancelar
            </Button>
            <Button
              type="submit"
              disabled={createMutation.isPending || updateMutation.isPending}
            >
              {isEditing ? "Salvar Alterações" : "Criar Perfil"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
