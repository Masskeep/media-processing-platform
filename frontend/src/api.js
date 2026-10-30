const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "";

export async function apiRequest(path, options = {}){
    const token = sessionStorage.getItem("access_token");

    const headers = {
        ...options.headers,
    };

    if(token){
        headers["Authorization"] = `Bearer ${token}`;
    }

    const response = await fetch(`${API_BASE_URL}${path}`, {
        ...options,
        headers,
    });

    const contentType = response.headers.get("content-type");

    let data  = null;

    if(contentType && contentType.includes("application/json")){
        data = await response.json();
    }

    if(!response.ok){
        throw new Error(
          data?.error || `Request failed with status ${response.status}`
        );
    }
    return data;
}