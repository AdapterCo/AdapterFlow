import type { components } from "./api.generated";
type Schema = components["schemas"];
export interface PaginatedResponse<T> { items: T[]; total: number; }
export type Status = Schema["ProductWithDetailsResponse"]["status"];
export type ImportStatus = Schema["ImportJobResponse"]["status"];
export type ItemStatus = Schema["ImportItemResponse"]["status"];
export type RoundingRule = Schema["PricingProfileResponse"]["rounding_rule"];
export type Supplier = Schema["SupplierResponse"];
export type SupplierCreate = Schema["SupplierCreate"];
export type SupplierUpdate = Schema["SupplierUpdate"];
export type ProductImage = Schema["ProductImageResponse"];
export type ProductSupplierData = Schema["ProductSupplierDataResponse"];
export type Product = Schema["ProductWithDetailsResponse"];
export type ProductWithDetails = Schema["ProductWithDetailsResponse"];
export type SupplierProductPrice = Schema["SupplierProductPriceResponse"];
export type ImportJob = Schema["ImportJobResponse"];
export type ImportItem = Schema["ImportItemResponse"];
export type ImportItemUpdate = Schema["ImportItemUpdateRequest"];
export type ImportConfirmRequest = Schema["ImportConfirmRequest"];
export type PricingProfile = Schema["PricingProfileResponse"];
export type PricingProfileCreate = Schema["PricingProfileCreate"];
export type PricingProfileUpdate = Schema["PricingProfileUpdate"];
export type DREBreakdown = Schema["DREBreakdown"];
export type PriceSimulationRequest = Schema["PriceSimulationRequest"];
export type PriceSimulationResponse = Schema["PriceSimulationResponse"];
export type ProductChannelPrice = Schema["ProductChannelPriceResponse"];
export type MarketplaceAccount = Schema["MarketplaceAccountResponse"];
export type MarketplaceChannelStatus = Schema["MarketplaceChannelStatus"];
export type MarketplacesOverviewResponse = Schema["MarketplacesOverviewResponse"];
export type CategoryPredictionItem = Schema["CategoryPredictionItem"];
export type PublishProductRequest = Schema["PublishProductRequest"];
export type MarketplaceListing = Schema["MarketplaceListingResponse"];
export type MarketplaceListingListResponse = Schema["MarketplaceListingListResponse"];

export interface ShopeeConfigurationResponse {
  partner_id: number | null;
  redirect_uri: string | null;
  ready: boolean;
  issues: string[];
}

export interface ShopeeOAuthCallbackRequest {
  code: string;
  shop_id: number;
  state: string;
}

export interface ShopeeCategoryItem {
  category_id: number;
  parent_category_id: number;
  original_category_name: string;
  display_category_name: string;
  has_children: boolean;
}

export interface ShopeeAttributeValue {
  value_id: number;
  original_value_name: string;
  display_value_name: string;
  value_unit?: string | null;
}

export interface ShopeeAttributeItem {
  attribute_id: number;
  original_attribute_name: string;
  display_attribute_name: string;
  is_mandatory: boolean;
  input_validation_type?: string | null;
  format_type?: string | null;
  date_format_type?: string | null;
  input_type?: string | null;
  attribute_unit?: string[] | null;
  attribute_value_list?: ShopeeAttributeValue[] | null;
}

export interface PublishShopeeProductRequest {
  product_id: string;
  account_id: string;
  pricing_profile_id: string;
  request_id: string;
  title: string;
  category_id: number;
  available_quantity: number;
  description?: string | null;
  attributes?: Record<string, any>[] | null;
}

export interface ClonePreviewRequest {
  url_or_id: string;
}

export interface ClonePreviewResponse {
  mlb_id: string;
  name: string;
  price?: number | null;
  original_price?: number | null;
  brand?: string | null;
  model?: string | null;
  ean?: string | null;
  gtin?: string | null;
  color?: string | null;
  dimensions?: string | null;
  weight?: number | null;
  category_id?: string | null;
  pictures: string[];
  description?: string | null;
  permalink?: string | null;
}

export interface CloneProductRequest {
  url_or_id: string;
  supplier_id?: string | null;
  cost_price?: number | null;
  status?: "ACTIVE" | "DRAFT";
}

