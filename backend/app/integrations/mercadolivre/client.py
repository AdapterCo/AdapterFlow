"""Cliente assíncrono oficial para a API do Mercado Livre Brasil (MLB).

Utiliza httpx para chamadas REST, em total conformidade com a documentação
oficial de desenvolvedores do Mercado Livre (developers.mercadolivre.com.br).
"""

from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode
import httpx
from fastapi import HTTPException, status
from app.core.config import settings

AUTH_URL_MLB = "https://auth.mercadolivre.com.br/authorization"
API_BASE_URL = "https://api.mercadolibre.com"


class MercadoLivreClient:
    def __init__(
        self,
        app_id: str | None = None,
        client_secret: str | None = None,
        redirect_uri: str | None = None,
    ) -> None:
        self.app_id = app_id or settings.MERCADOLIVRE_APP_ID
        self.client_secret = client_secret or settings.MERCADOLIVRE_CLIENT_SECRET
        self.redirect_uri = redirect_uri or settings.MERCADOLIVRE_REDIRECT_URI

    def is_configured(self) -> bool:
        """Verifica se as credenciais de desenvolvedor estão preenchidas no backend."""
        return bool(self.app_id and self.client_secret and self.redirect_uri)

    def get_authorization_url(self, state: str = "adapterflow_oauth") -> str:
        """Gera a URL de autorização oficial do Mercado Livre Brasil."""
        if not self.is_configured():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Mercado Livre não está configurado no servidor. Configure MERCADOLIVRE_APP_ID e MERCADOLIVRE_CLIENT_SECRET no .env.",
            )

        params = {
            "response_type": "code",
            "client_id": self.app_id,
            "redirect_uri": self.redirect_uri,
            "state": state,
        }
        return f"{AUTH_URL_MLB}?{urlencode(params)}"

    async def exchange_code_for_token(self, code: str) -> dict:
        """Troca o authorization code pelo access_token e refresh_token."""
        if not self.is_configured():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Credenciais do Mercado Livre não configuradas no servidor.",
            )

        payload = {
            "grant_type": "authorization_code",
            "client_id": self.app_id,
            "client_secret": self.client_secret,
            "code": code,
            "redirect_uri": self.redirect_uri,
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            res = await client.post(
                f"{API_BASE_URL}/oauth/token",
                data=payload,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            if res.status_code != 200:
                detail_msg = res.json().get("message", res.text) if res.content else "Erro desconhecido"
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Falha na autenticação com o Mercado Livre: {detail_msg}",
                )

            data = res.json()
            # Calcula data de expiração (UTC)
            expires_in = data.get("expires_in", 21600)
            data["token_expires_at"] = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
            return data

    async def refresh_access_token(self, refresh_token: str) -> dict:
        """Renova o access_token utilizando o refresh_token."""
        if not self.is_configured():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Credenciais do Mercado Livre não configuradas no servidor.",
            )

        payload = {
            "grant_type": "refresh_token",
            "client_id": self.app_id,
            "client_secret": self.client_secret,
            "refresh_token": refresh_token,
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            res = await client.post(
                f"{API_BASE_URL}/oauth/token",
                data=payload,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            if res.status_code != 200:
                detail_msg = res.json().get("message", res.text) if res.content else "Token expirado ou revogado"
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"Não foi possível renovar a sessão com o Mercado Livre: {detail_msg}",
                )

            data = res.json()
            expires_in = data.get("expires_in", 21600)
            data["token_expires_at"] = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
            return data

    async def get_user_info(self, access_token: str) -> dict:
        """Obtém os dados do vendedor autenticado (/users/me)."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.get(
                f"{API_BASE_URL}/users/me",
                headers={"Authorization": f"Bearer {access_token}"},
            )

            if res.status_code != 200:
                raise HTTPException(
                    status_code=res.status_code,
                    detail="Falha ao obter dados da conta do Mercado Livre.",
                )

            return res.json()

    async def predict_category(self, title: str, access_token: str | None = None) -> list[dict]:
        """Prevê categorias adequadas no site MLB a partir do título do produto."""
        headers = {}
        if access_token:
            headers["Authorization"] = f"Bearer {access_token}"

        params = {"limit": 4, "q": title}

        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.get(
                f"{API_BASE_URL}/sites/MLB/domain_discovery/search",
                params=params,
                headers=headers,
            )

            if res.status_code == 200:
                return res.json()
            return []

    async def get_category_attributes(self, category_id: str) -> list[dict]:
        """Retorna os atributos obrigatórios e recomendados da categoria."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.get(
                f"{API_BASE_URL}/categories/{category_id}/attributes"
            )

            if res.status_code == 200:
                return res.json()
            return []

    async def validate_item(self, item_data: dict, access_token: str) -> dict:
        """Executa a validação prévia de um anúncio (POST /items/validate)."""
        async with httpx.AsyncClient(timeout=15.0) as client:
            res = await client.post(
                f"{API_BASE_URL}/items/validate",
                json=item_data,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
            )

            if res.status_code not in (200, 204):
                error_body = res.json() if res.content else {}
                detail = error_body.get("message", res.text)
                causes = error_body.get("cause", [])
                cause_msgs = [c.get("message", str(c)) for c in causes if isinstance(c, dict)]
                full_msg = f"{detail}: {', '.join(cause_msgs)}" if cause_msgs else detail
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Validação do anúncio recusada pelo Mercado Livre: {full_msg}",
                )

            return {"valid": True}

    async def publish_item(self, item_data: dict, access_token: str) -> dict:
        """Publica o anúncio definitivamente (POST /items)."""
        # Executa validação prévia obrigatória
        await self.validate_item(item_data, access_token)

        async with httpx.AsyncClient(timeout=20.0) as client:
            res = await client.post(
                f"{API_BASE_URL}/items",
                json=item_data,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
            )

            if res.status_code not in (200, 201):
                error_body = res.json() if res.content else {}
                detail = error_body.get("message", res.text)
                raise HTTPException(
                    status_code=res.status_code,
                    detail=f"Erro ao publicar item no Mercado Livre: {detail}",
                )

            return res.json()

    async def update_item(self, item_id: str, item_data: dict, access_token: str) -> dict:
        """Atualiza preço ou estoque de um anúncio existente (PUT /items/{id})."""
        async with httpx.AsyncClient(timeout=15.0) as client:
            res = await client.put(
                f"{API_BASE_URL}/items/{item_id}",
                json=item_data,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
            )

            if res.status_code != 200:
                error_body = res.json() if res.content else {}
                detail = error_body.get("message", res.text)
                raise HTTPException(
                    status_code=res.status_code,
                    detail=f"Erro ao atualizar anúncio no Mercado Livre: {detail}",
                )

            return res.json()
