import { useEffect, useState } from "react";
import { listarEstacoesProximas } from "../api/cliente";
import { RAIO_LOCAL_KM, chaveLocal, resumirSituacao } from "../situacaoLocal";

/** Situação de cada local salvo, indexada por `chaveLocal(place)`. */
export default function useSituacaoLocais(places) {
  const [situacoes, setSituacoes] = useState({});
  const chaves = [...new Set(places.map(chaveLocal))].join("|");

  useEffect(() => {
    const controller = new AbortController();
    const lista = chaves ? chaves.split("|") : [];
    setSituacoes((atuais) =>
      Object.fromEntries(
        lista.map((chave) => [
          chave,
          atuais[chave] ?? { estado: "carregando" },
        ]),
      ),
    );

    lista.forEach((chave) => {
      const [lat, lon] = chave.split(",").map(Number);
      listarEstacoesProximas({
        lat,
        lon,
        raioKm: RAIO_LOCAL_KM,
        signal: controller.signal,
      })
        .then(resumirSituacao, () => ({ estado: "erro" }))
        .then((situacao) => {
          if (controller.signal.aborted) return;
          setSituacoes((atuais) => ({ ...atuais, [chave]: situacao }));
        });
    });

    return () => controller.abort();
  }, [chaves]);

  return situacoes;
}
