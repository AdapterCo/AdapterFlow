const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const apiClient = {
  async get<T>(path: string): Promise<T> {
    const res = await fetch(`${API_BASE_URL}${path}`, {
      headers: {
        "Content-Type": "application/json",
      },
    });
    if (!res.ok) throw new Error(`API error: ${res.statusText}`);
    return res.json();
  },

  async post<T>(path: string, body?: any): Promise<T> {
    const res = await fetch(`${API_BASE_URL}${path}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: body ? JSON.stringify(body) : undefined,
    });
    if (!res.ok) throw new Error(`API error: ${res.statusText}`);
    return res.json();
  },

  async patch<T>(path: string, body: any): Promise<T> {
    const res = await fetch(`${API_BASE_URL}${path}`, {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(`API error: ${res.statusText}`);
    return res.json();
  },

  async delete(path: string): Promise<void> {
    const res = await fetch(`${API_BASE_URL}${path}`, {
      method: "DELETE",
    });
    if (!res.ok) throw new Error(`API error: ${res.statusText}`);
  },

  upload<T>(
    path: string,
    formData: FormData,
    onProgress?: (progress: number) => void
  ): Promise<T> {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      xhr.open("POST", `${API_BASE_URL}${path}`);
      
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
          resolve(JSON.parse(xhr.responseText));
        } else {
          reject(new Error(`Upload error: ${xhr.statusText}`));
        }
      };

      xhr.onerror = () => reject(new Error("Network Error"));
      xhr.send(formData);
    });
  },
};
