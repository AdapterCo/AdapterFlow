function getApiBaseUrl(): string {
  if (typeof window !== "undefined") {
    // In browser: if NEXT_PUBLIC_API_URL is set to an external absolute URL (not localhost), use it
    if (
      process.env.NEXT_PUBLIC_API_URL &&
      !process.env.NEXT_PUBLIC_API_URL.includes("localhost") &&
      !process.env.NEXT_PUBLIC_API_URL.includes("127.0.0.1")
    ) {
      return process.env.NEXT_PUBLIC_API_URL;
    }
    // Otherwise use relative URL so Next.js rewrites proxy to the backend container
    return "";
  }
  // Server-side: use internal Docker service name
  return process.env.INTERNAL_BACKEND_URL || "http://localhost:8000";
}

const DEFAULT_TIMEOUT_MS = 120000;

async function fetchWithTimeout(url: string, options: RequestInit = {}): Promise<Response> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), DEFAULT_TIMEOUT_MS);
  
  try {
    const res = await fetch(url, {
      ...options,
      signal: controller.signal,
    });
    return res;
  } catch (err: unknown) {
    if (err instanceof Error && err.name === "AbortError") {
      throw new Error("Tempo limite da requisição esgotado (timeout de 120s). Verifique sua conexão.");
    }
    throw err;
  } finally {
    clearTimeout(timeoutId);
  }
}

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const errorBody = await res.json().catch(() => null);
    const message = (Array.isArray(errorBody?.detail) ? errorBody.detail.map((item: { msg: string }) => item.msg).join("; ") : errorBody?.detail) || (res.status >= 500 ? "A API do AdapterFlow está indisponível ou não respondeu a tempo. Verifique os serviços na VPS; esta falha não indica recusa do Mercado Livre." : `Erro na requisição: ${res.status} ${res.statusText}`);
    throw new Error(message);
  }
  return res.json();
}

export const apiClient = {
  async get<T>(path: string): Promise<T> {
    const baseUrl = getApiBaseUrl();
    const res = await fetchWithTimeout(`${baseUrl}${path}`, {
      headers: {
        "Content-Type": "application/json",
      },
    });
    return handleResponse<T>(res);
  },

  async post<T>(path: string, body?: unknown): Promise<T> {
    const baseUrl = getApiBaseUrl();
    const res = await fetchWithTimeout(`${baseUrl}${path}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: body ? JSON.stringify(body) : undefined,
    });
    return handleResponse<T>(res);
  },

  async patch<T>(path: string, body: unknown): Promise<T> {
    const baseUrl = getApiBaseUrl();
    const res = await fetchWithTimeout(`${baseUrl}${path}`, {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
    });
    return handleResponse<T>(res);
  },

  async put<T>(path: string, body: unknown): Promise<T> {
    const baseUrl = getApiBaseUrl();
    const res = await fetchWithTimeout(`${baseUrl}${path}`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
    });
    return handleResponse<T>(res);
  },

  async delete(path: string): Promise<void> {
    const baseUrl = getApiBaseUrl();
    const res = await fetchWithTimeout(`${baseUrl}${path}`, {
      method: "DELETE",
    });
    if (!res.ok) {
      const errorBody = await res.json().catch(() => null);
      const message = (Array.isArray(errorBody?.detail) ? errorBody.detail.map((item: { msg: string }) => item.msg).join("; ") : errorBody?.detail) || `Erro ao deletar: ${res.status} ${res.statusText}`;
      throw new Error(message);
    }
  },

  upload<T>(
    path: string,
    formData: FormData,
    onProgress?: (progress: number) => void
  ): Promise<T> {
    return new Promise((resolve, reject) => {
      const baseUrl = getApiBaseUrl();
      const xhr = new XMLHttpRequest();
      xhr.open("POST", `${baseUrl}${path}`);
      xhr.timeout = 600000; // bounded large catalog upload
      
      if (onProgress && xhr.upload) {
        xhr.upload.onprogress = (event) => {
          if (event.lengthComputable) {
            const percentComplete = Math.round((event.loaded / event.total) * 100);
            onProgress(percentComplete);
          }
        };
      }

      xhr.onload = () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          try {
            resolve(JSON.parse(xhr.responseText));
          } catch {
            resolve(xhr.responseText as unknown as T);
          }
        } else {
          try {
            const errData = JSON.parse(xhr.responseText);
            reject(new Error(errData?.detail || `Upload error: ${xhr.statusText}`));
          } catch {
            reject(new Error(`Upload error: ${xhr.statusText}`));
          }
        }
      };

      xhr.ontimeout = () => reject(new Error("Tempo limite do upload esgotado."));
      xhr.onerror = () => reject(new Error("Erro de conexão ao fazer upload. Verifique o servidor."));
      xhr.send(formData);
    });
  },
};
