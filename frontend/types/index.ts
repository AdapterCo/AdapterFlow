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
