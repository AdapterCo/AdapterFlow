"""Shopee Open API v2 client with HMAC-SHA256 signing and shop OAuth."""
import hashlib
import hmac
import logging
import time
from urllib.parse import urlencode

import httpx
from fastapi import HTTPException

from app.core.config import settings

logger = logging.getLogger(__name__)


class ShopeeClient:
    def __init__(
        self,
        partner_id: int | None = None,
        partner_key: str | None = None,
        redirect_uri: str | None = None,
        base_url: str | None = None,
    ):
        self.partner_id = partner_id or settings.SHOPEE_PARTNER_ID
        self.partner_key = partner_key or settings.SHOPEE_PARTNER_KEY
        self.redirect_uri = redirect_uri or settings.SHOPEE_REDIRECT_URI
        self.base_url = (base_url or settings.SHOPEE_API_URL or "https://partner.shopeemobile.com").rstrip("/")
        self._http_client = None

    async def close(self):
        if self._http_client is not None:
            await self._http_client.aclose()
            self._http_client = None

    def is_configured(self) -> bool:
        return bool(self.partner_id and self.partner_key and self.redirect_uri)

    def _generate_sign(
        self,
        path: str,
        timestamp: int,
        access_token: str | None = None,
        shop_id: int | None = None,
    ) -> str:
        """Calculate HMAC-SHA256 signature according to Shopee Open API v2 specification."""
        if not self.partner_key:
            raise HTTPException(503, "Shopee não está configurada no servidor (falta SHOPEE_PARTNER_KEY).")

        partner_id_str = str(self.partner_id)
        if access_token and shop_id is not None:
            base_string = f"{partner_id_str}{path}{timestamp}{access_token}{shop_id}"
        elif shop_id is not None and not access_token:
            base_string = f"{partner_id_str}{path}{timestamp}{shop_id}"
        else:
            base_string = f"{partner_id_str}{path}{timestamp}"

        return hmac.new(
            self.partner_key.encode("utf-8"),
            base_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    def get_authorization_url(self, state: str) -> str:
        """Generate official Shopee OAuth authorization URL."""
        if not self.is_configured():
            raise HTTPException(503, "Shopee não está configurada no servidor (verifique SHOPEE_PARTNER_ID, SHOPEE_PARTNER_KEY e SHOPEE_REDIRECT_URI).")

        path = "/api/v2/shop/auth_partner"
        timestamp = int(time.time())
        sign = self._generate_sign(path, timestamp)

        query = {
            "partner_id": self.partner_id,
            "timestamp": timestamp,
            "sign": sign,
            "redirect": self.redirect_uri,
        }
        return f"{self.base_url}{path}?{urlencode(query)}"

    async def _request(
        self,
        method: str,
        path: str,
        access_token: str | None = None,
        shop_id: int | None = None,
        params: dict | None = None,
        json_body: dict | None = None,
        files: dict | None = None,
    ) -> dict:
        if not self.is_configured():
            raise HTTPException(503, "Shopee não está configurada no servidor.")

        timestamp = int(time.time())
        sign = self._generate_sign(path, timestamp, access_token=access_token, shop_id=shop_id)

        query_params = {
            "partner_id": self.partner_id,
            "timestamp": timestamp,
            "sign": sign,
        }
        if access_token:
            query_params["access_token"] = access_token
        if shop_id is not None:
            query_params["shop_id"] = shop_id

        if params:
            query_params.update(params)

        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=30, limits=httpx.Limits(max_connections=20, max_keepalive_connections=10))

        url = f"{self.base_url}{path}"
        try:
            response = await self._http_client.request(
                method,
                url,
                params=query_params,
                json=json_body,
                files=files,
            )
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            logger.warning("Falha de rede Shopee tipo=%s", type(exc).__name__)
            raise HTTPException(503, "Não foi possível conectar com os servidores da Shopee. Tente novamente.") from None

        if response.status_code >= 500:
            raise HTTPException(502, f"Shopee retornou erro no servidor (HTTP {response.status_code}).")

        try:
            data = response.json()
        except ValueError:
            raise HTTPException(502, "Resposta inválida retornada pela Shopee.")

        error_code = data.get("error")
        if error_code:
            logger.warning("Shopee recusou operação no endpoint %s", path)
            if "invalid_access_token" in str(error_code).lower() or "token_expired" in str(error_code).lower():
                raise HTTPException(401, "Token de acesso da Shopee expirado. Reconecte ou atualize a conta.")
            raise HTTPException(422, "Shopee recusou a operação. Verifique os dados e permissões da conta.")

        return data.get("response") or data

    async def exchange_token(self, code: str, shop_id: int) -> dict:
        """Exchange authorization code for access and refresh tokens."""
        path = "/api/v2/auth/token/get"
        body = {
            "code": code,
            "partner_id": self.partner_id,
            "shop_id": shop_id,
        }
        return await self._request("POST", path, json_body=body)

    async def refresh_token(self, refresh_token: str, shop_id: int) -> dict:
        """Renew expired access token using refresh token."""
        path = "/api/v2/auth/access_token/get"
        body = {
            "refresh_token": refresh_token,
            "partner_id": self.partner_id,
            "shop_id": shop_id,
        }
        return await self._request("POST", path, json_body=body)

    async def get_shop_info(self, access_token: str, shop_id: int) -> dict:
        """Fetch shop profile from Shopee."""
        path = "/api/v2/shop/get_shop_info"
        return await self._request("GET", path, access_token=access_token, shop_id=shop_id)

    async def get_categories(self, access_token: str, shop_id: int, language: str = "pt-BR") -> list[dict]:
        """Fetch available category tree for the shop."""
        path = "/api/v2/product/get_category"
        result = await self._request("GET", path, access_token=access_token, shop_id=shop_id, params={"language": language})
        return result.get("category_list", [])

    async def get_category_attributes(self, access_token: str, shop_id: int, category_id: int, language: str = "pt-BR") -> list[dict]:
        """Fetch mandatory and optional attributes for a given category."""
        path = "/api/v2/product/get_attributes"
        result = await self._request("GET", path, access_token=access_token, shop_id=shop_id, params={"category_id": category_id, "language": language})
        return result.get("attribute_list", [])

    async def upload_image(self, access_token: str, shop_id: int, image_bytes: bytes, filename: str = "photo.jpg") -> str:
        """Upload image to Shopee media space and return image_id."""
        path = "/api/v2/media_space/upload_image"
        files = {"image": (filename, image_bytes, "image/jpeg")}
        result = await self._request("POST", path, access_token=access_token, shop_id=shop_id, files=files)
        image_info = result.get("image_info") or {}
        image_id = image_info.get("image_id")
        if not image_id:
            raise HTTPException(502, "Shopee não retornou o identificador da imagem enviada.")
        return image_id

    async def add_item(self, access_token: str, shop_id: int, payload: dict) -> dict:
        """Publish a product listing on Shopee."""
        path = "/api/v2/product/add_item"
        return await self._request("POST", path, access_token=access_token, shop_id=shop_id, json_body=payload)

    async def get_item_base_info(self, access_token: str, shop_id: int, item_id_list: list[int]) -> list[dict]:
        """Fetch basic information for listings."""
        path = "/api/v2/product/get_item_base_info"
        item_id_csv = ",".join(map(str, item_id_list))
        result = await self._request("GET", path, access_token=access_token, shop_id=shop_id, params={"item_id_list": item_id_csv})
        return result.get("item_list", [])
