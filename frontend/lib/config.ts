// URL del backend — en producción viene de la variable de entorno NEXT_PUBLIC_API_URL
// En local usa localhost:8000
export const API_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
