export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export type Status = "ACTIVE" | "DRAFT" | "INACTIVE";
export type ImportStatus = "PENDING" | "PROCESSING" | "COMPLETED" | "FAILED" | "REVIEW_NEEDED";
export type ItemStatus = "PENDING" | "APPROVED" | "IGNORED" | "ERROR";

export interface Supplier {
  id: string;
  name: string;
  code?: string | null;
  status: Status;
  is_active?: boolean;
  created_at: string;
  updated_at: string;
}

export interface SupplierCreate {
  name: string;
  code?: string;
  status?: Status;
}

export interface SupplierUpdate {
  name?: string;
  code?: string;
  status?: Status;
}

export interface ProductImage {
  id: string;
  url: string;
  is_primary: boolean;
  order: number;
}

export interface ProductSupplierData {
  id: string;
  supplier_id: string;
  supplier_code: string;
  current_cost: string; // Decimal
  pcs_per_box?: number | null;
  supplier?: Supplier;
}

export interface Product {
  id: string;
  name: string;
  sku: string;
  brand?: string | null;
  model?: string | null;
  ean?: string | null;
  gtin?: string | null;
  color?: string | null;
  dimensions?: string | null;
  weight?: string | null; // Decimal
  status: Status;
  primary_image?: ProductImage | null;
  created_at: string;
  updated_at: string;
  supplier_data?: ProductSupplierData[];
}

export interface ProductWithDetails extends Product {
  images: ProductImage[];
  price_history: SupplierProductPrice[];
}

export interface SupplierProductPrice {
  id: string;
  price: string; // Decimal
  date: string;
  import_job_id?: string | null;
}

export interface ImportJob {
  id: string;
  supplier_id: string;
  status: ImportStatus;
  original_filename: string;
  items_detected: number;
  items_imported: number;
  items_failed: number;
  created_at: string;
  updated_at: string;
  supplier?: Supplier;
}

export interface ImportItem {
  id: string;
  import_job_id: string;
  status: ItemStatus;
  raw_code?: string | null;
  raw_name?: string | null;
  raw_dimensions?: string | null;
  raw_pcs_cx?: string | null;
  raw_price?: string | null;
  normalized_code?: string | null;
  normalized_price?: string | null; // Decimal
  normalized_color?: string | null;
  image_path?: string | null;
  confidence_score?: number | null;
  warnings?: string[] | null;
  created_at: string;
  updated_at: string;
}

export interface ImportItemUpdate {
  normalized_code?: string | null;
  normalized_price?: string | null; // Decimal
  normalized_color?: string | null;
  status?: ItemStatus;
}

export interface ImportConfirmRequest {
  job_id: string;
}

export type RoundingRule = "EXACT" | "ENDS_90" | "ENDS_99" | "ROUND_INTEGER";

export interface PricingProfile {
  id: string;
  name: string;
  description?: string | null;
  channel: string;
  marketplace_commission_percent: string;
  fixed_fee: string;
  fixed_fee_threshold?: string | null;
  tax_percent: string;
  operating_cost_percent: string;
  fixed_cost: string;
  target_margin_percent: string;
  free_shipping_threshold?: string | null;
  free_shipping_cost?: string | null;
  rounding_rule: string;
  is_default: boolean;
  is_active: boolean;
  created_at: string;
  updated_at?: string | null;
}

export interface PricingProfileCreate {
  name: string;
  description?: string | null;
  channel: string;
  marketplace_commission_percent: string;
  fixed_fee: string;
  fixed_fee_threshold?: string | null;
  tax_percent: string;
  operating_cost_percent: string;
  fixed_cost: string;
  target_margin_percent: string;
  free_shipping_threshold?: string | null;
  free_shipping_cost?: string | null;
  rounding_rule: string;
  is_default?: boolean;
  is_active?: boolean;
}

export interface PricingProfileUpdate extends Partial<PricingProfileCreate> {}

export interface DREBreakdown {
  gross_revenue: string;
  cost_basis: string;
  marketplace_commission_percent: string;
  marketplace_commission_value: string;
  marketplace_fixed_fee: string;
  tax_percent: string;
  tax_value: string;
  operating_cost_percent: string;
  operating_cost_value: string;
  fixed_cost: string;
  shipping_cost: string;
  total_deductions: string;
  net_profit_value: string;
  net_margin_percent: string;
  effective_markup: string;
}

export interface PriceSimulationRequest {
  cost_basis: string;
  marketplace_commission_percent: string;
  fixed_fee?: string;
  fixed_fee_threshold?: string | null;
  tax_percent: string;
  operating_cost_percent: string;
  fixed_cost?: string;
  target_margin_percent: string;
  free_shipping_threshold?: string | null;
  free_shipping_cost?: string | null;
  rounding_rule?: string;
  manual_override_price?: string | null;
}

export interface PriceSimulationResponse {
  suggested_price: string;
  cost_basis: string;
  marketplace_commission: string;
  taxes: string;
  operating_costs: string;
  shipping_cost: string;
  fixed_fee: string;
  net_margin_value: string;
  net_margin_percent: string;
  breakdown: DREBreakdown;
}

export interface ProductChannelPrice {
  id: string;
  product_id: string;
  pricing_profile_id: string;
  profile_name?: string | null;
  channel?: string | null;
  calculated_price: string;
  cost_basis: string;
  channel_commission: string;
  taxes: string;
  operating_costs: string;
  shipping_cost: string;
  fixed_fee: string;
  net_margin_value: string;
  net_margin_percent: string;
  breakdown?: DREBreakdown | null;
  is_manual_override: boolean;
  manual_price?: string | null;
  created_at: string;
  updated_at?: string | null;
}
