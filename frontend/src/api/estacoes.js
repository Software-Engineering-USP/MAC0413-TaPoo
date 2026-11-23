const API_URL = (
  import.meta.env.VITE_API_URL?.trim() || "http://localhost:8000"
).replace(/\/$/, "");

export async function listarEstacoes({ texto, uf = "SP", signal } = {}) {
  const consulta = texto?.trim();
  if (!consulta || consulta.length < 2) {
    throw new RangeError(
      "Informe ao menos 2 caracteres para pesquisar estações.",
    );
  }

  const url = new URL(`${API_URL}/estacoes`);
  url.searchParams.set("uf", uf);
  url.searchParams.set("apenas_telemetricas", "true");
  url.searchParams.set("q", consulta);

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
    throw new TypeError("A API retornou uma lista de estações inválida.");
  }
  return estacoes;
}
