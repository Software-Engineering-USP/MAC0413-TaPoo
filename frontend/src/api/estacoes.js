const API_URL = (
  import.meta.env.VITE_API_URL?.trim() || "http://localhost:8000"
).replace(/\/+$/, "");

export async function listarEstacoes({ texto, signal } = {}) {
  const url = new URL(`${API_URL}/estacoes`);
  if (texto) url.searchParams.set("q", texto);

  const resposta = await fetch(url, { signal });
  if (!resposta.ok) {
    let detalhe = `Não foi possível consultar as estações (HTTP ${resposta.status}).`;
    try {
      const corpo = await resposta.json();
      if (typeof corpo.detail === "string") detalhe = corpo.detail;
    } catch {
      // Mantém a mensagem HTTP quando a API não envia JSON.
    }
    throw new Error(detalhe);
  }

  const estacoes = await resposta.json();
  if (!Array.isArray(estacoes)) {
    throw new Error("A API retornou uma lista de estações inválida.");
  }
  return estacoes;
}
