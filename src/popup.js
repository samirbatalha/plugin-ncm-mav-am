// Mapa de dígitos puros -> entrada NCM (construído ao carregar os dados)
let ncmMap = null;

async function loadData() {
  if (ncmMap) return;
  const response = await fetch("./data/ncm_data.json");
  const entries = await response.json();
  ncmMap = {};
  for (const entry of entries) {
    const key = entry.ncm.replace(/\D/g, "");
    // Se houver duplicata de chave, manter a de NCM mais longo (mais específica)
    if (!ncmMap[key] || entry.ncm.length > ncmMap[key].ncm.length) {
      ncmMap[key] = entry;
    }
  }
}

function normalize(input) {
  return input.replace(/\D/g, "");
}

/**
 * Busca hierárquica: tenta o NCM completo, depois prefixos progressivamente menores.
 * Retorna { entry, matchType } ou null.
 */
function lookup(ncmInput) {
  const digits = normalize(ncmInput);
  if (!digits) return null;

  for (let len = digits.length; len >= 1; len--) {
    const prefix = digits.slice(0, len);
    if (ncmMap[prefix]) {
      const matchType = len === digits.length ? "exact" : "partial";
      return { entry: ncmMap[prefix], matchType, matchedDigits: len };
    }
  }
  return null;
}

function formatMva(mva) {
  // Formata número: substitui ponto por vírgula se tiver decimal
  return mva.includes(".") ? mva.replace(".", ",") : mva;
}

function showResult(ncmInput) {
  const resultEl = document.getElementById("result");
  resultEl.className = "result";

  if (!ncmInput.trim()) {
    resultEl.classList.add("hidden");
    return;
  }

  const found = lookup(ncmInput.trim());

  if (!found) {
    resultEl.classList.add("notfound");
    resultEl.innerHTML = `
      <div class="result-mva-zero">MVA: 0%</div>
      <div class="result-notfound-msg">NCM n&atilde;o encontrado na lei.</div>
    `;
    return;
  }

  const { entry, matchType } = found;
  const mvaFormatted = formatMva(entry.mva);
  const matchLabel = matchType === "exact" ? "Correspond&ecirc;ncia exata" : "Correspond&ecirc;ncia por prefixo";
  const matchClass = matchType === "exact" ? "exact" : "partial";

  resultEl.classList.add(matchClass);
  resultEl.innerHTML = `
    <div class="result-mva">${mvaFormatted}<span>%</span></div>
    <div class="result-match">${matchLabel}: <strong>${entry.ncm}</strong></div>
    ${entry.descricao ? `<div class="result-desc">${entry.descricao}</div>` : ""}
  `;
}

document.addEventListener("DOMContentLoaded", async () => {
  await loadData();

  const input = document.getElementById("ncmInput");
  const btn = document.getElementById("searchBtn");

  btn.addEventListener("click", () => showResult(input.value));
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter") showResult(input.value);
  });

  input.focus();
});
