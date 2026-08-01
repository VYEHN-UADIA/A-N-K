(() => {
  "use strict";

  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => Array.from(root.querySelectorAll(selector));
  const endpoint = "./AnankeAI/Ananke_spin.php";
  const MAX_UPLOAD = 50 * 1024 * 1024;
  const STORAGE_KEY = "ananke_conversations_v3";

  const state = {
    csrf: "",
    access: null,
    conversations: [],
    currentId: null,
    selectedFile: null,
    analysisId: null,
  };

  function toast(message) {
    if (window.ChatUI?.toast) return window.ChatUI.toast(message);
    const element = $("#toast");
    if (!element) return;
    element.textContent = message;
    element.classList.add("show");
    setTimeout(() => element.classList.remove("show"), 1800);
  }

  function formatNumber(value) {
    return new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 2 }).format(Number(value || 0));
  }

  function formatBytes(value) {
    const bytes = Number(value || 0);
    if (bytes < 1024) return `${bytes} o`;
    if (bytes < 1024 ** 2) return `${(bytes / 1024).toFixed(1)} Ko`;
    return `${(bytes / 1024 ** 2).toFixed(2)} Mo`;
  }

  async function api(action, payload = {}, options = {}) {
    const headers = { "X-Ananke-CSRF": state.csrf };
    let body;
    if (options.formData) {
      body = options.formData;
    } else {
      headers["Content-Type"] = "application/json; charset=utf-8";
      body = JSON.stringify({ action, ...payload });
    }
    const response = await fetch(endpoint, { method: "POST", credentials: "same-origin", headers, body });
    const data = await response.json().catch(() => ({ error: "invalid_response" }));
    if (!response.ok) {
      const error = new Error(data.detail || data.error || `HTTP ${response.status}`);
      error.status = response.status;
      error.data = data;
      throw error;
    }
    return data;
  }

  async function checkAccess() {
    const response = await fetch(`${endpoint}?action=access_status`, { credentials: "same-origin", cache: "no-store" });
    const data = await response.json().catch(() => ({}));
    state.access = data;
    state.csrf = data.csrf_token || "";
    const gate = $("#accessGate");
    const gateText = $("#accessGateText");
    const composer = $("#composer");
    if (!data.authenticated) {
      gate?.classList.add("show");
      if (gateText) gateText.textContent = "Connectez-vous à Cercle pour utiliser ANANKÉ.";
      composer?.querySelectorAll("textarea,button").forEach(el => { el.disabled = true; });
      return false;
    }
    if (!data.granted) {
      gate?.classList.add("show");
      if (gateText) gateText.textContent = "Votre compte est reconnu, mais l’accès ANANKÉ est actuellement refusé.";
      composer?.querySelectorAll("textarea,button").forEach(el => { el.disabled = true; });
      return false;
    }
    gate?.classList.remove("show");
    $$(".admin-only").forEach(element => element.classList.add("visible"));
    composer?.querySelectorAll("textarea,button").forEach(el => { el.disabled = false; });
    return true;
  }

  function loadConversations() {
    try {
      const parsed = JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]");
      state.conversations = Array.isArray(parsed) ? parsed : [];
    } catch {
      state.conversations = [];
    }
    if (!state.conversations.length) createConversation(false);
    state.currentId = state.currentId || state.conversations[0]?.id || null;
    renderConversationList();
    renderCurrentConversation();
  }

  function saveConversations() {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state.conversations.slice(0, 100)));
  }

  function createConversation(render = true) {
    const id = crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random()}`;
    state.conversations.unshift({ id, title: "Nouvelle conversation", messages: [], createdAt: Date.now() });
    state.currentId = id;
    saveConversations();
    if (render) {
      renderConversationList();
      renderCurrentConversation();
      $("#input")?.focus();
    }
  }

  function currentConversation() {
    return state.conversations.find(item => item.id === state.currentId) || null;
  }

  function deleteConversation(conversationId) {
    const conversation = state.conversations.find(item => item.id === conversationId);
    if (!conversation) return;
    const label = conversation.title || "cette conversation";
    if (!window.confirm(`Supprimer « ${label} » ? Cette action efface la conversation de ce navigateur.`)) return;

    const removedIndex = state.conversations.findIndex(item => item.id === conversationId);
    state.conversations = state.conversations.filter(item => item.id !== conversationId);

    if (!state.conversations.length) {
      createConversation(false);
    } else if (state.currentId === conversationId) {
      const nextIndex = Math.min(Math.max(removedIndex, 0), state.conversations.length - 1);
      state.currentId = state.conversations[nextIndex].id;
    }

    saveConversations();
    renderConversationList();
    renderCurrentConversation();
    toast("Conversation supprimée.");
  }

  function renderConversationList() {
    const list = $("#convList");
    if (!list) return;
    list.innerHTML = "";
    for (const conversation of state.conversations) {
      const item = document.createElement("div");
      item.className = `conv-item${conversation.id === state.currentId ? " active" : ""}`;
      item.tabIndex = 0;
      item.setAttribute("role", "button");
      item.setAttribute("aria-label", `Ouvrir ${conversation.title || "la conversation"}`);

      const title = document.createElement("span");
      title.className = "conv-title";
      title.textContent = conversation.title || "Conversation";

      const remove = document.createElement("button");
      remove.type = "button";
      remove.className = "conv-delete";
      remove.setAttribute("aria-label", `Supprimer ${conversation.title || "la conversation"}`);
      remove.title = "Supprimer la conversation";
      remove.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18"/><path d="M8 6V4h8v2"/><path d="M19 6l-1 14H6L5 6"/><path d="M10 11v5M14 11v5"/></svg>';
      remove.addEventListener("click", event => {
        event.stopPropagation();
        deleteConversation(conversation.id);
      });

      const activate = () => {
        state.currentId = conversation.id;
        renderConversationList();
        renderCurrentConversation();
      };
      item.addEventListener("click", activate);
      item.addEventListener("keydown", event => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          activate();
        }
      });
      item.append(title, remove);
      list.appendChild(item);
    }
  }

  function appendMessageElement(role, content, pending = false) {
    const wrap = $("#chat .chat-wrap") || $("#chat");
    const message = document.createElement("div");
    message.className = `msg ${role}`;
    const avatar = document.createElement("div");
    avatar.className = "avatar";
    avatar.textContent = role === "user" ? "V" : "A";
    const bubble = document.createElement("div");
    bubble.className = "bubble";
    bubble.textContent = content;
    if (pending) bubble.style.opacity = ".6";
    message.append(avatar, bubble);
    wrap.appendChild(message);
    $("#chat")?.scrollTo({ top: $("#chat").scrollHeight, behavior: "smooth" });
    if (!pending) window.ChatUI?.finalize?.(bubble);
    return { message, bubble };
  }

  function renderCurrentConversation() {
    const wrap = $("#chat .chat-wrap") || $("#chat");
    if (!wrap) return;
    wrap.innerHTML = "";
    const conversation = currentConversation();
    if (!conversation || !conversation.messages.length) {
      const intro = appendMessageElement("assistant", "ANANKÉ est prête. Chaque sortie est construite depuis le référentiel relationnel actif.");
      intro.message.dataset.intro = "1";
    } else {
      conversation.messages.forEach(message => appendMessageElement(message.role, message.content));
    }
    $(".header-title").textContent = conversation?.title || "Conversation";
  }

  function abstentionMessage(data) {
    const reason = data.stop_reason || data.reason || "no_resolved_relation";
    if (reason === "unknown_object") {
      const value = data.unknown_object || "?";
      return `⊥ — le caractère « ${value} » n’est pas encore encodé dans le référentiel actif.`;
    }
    if (reason === "insufficient_relational_context") {
      return "⊥ — la ligne ne contient pas encore deux éléments connus permettant de former une relation.";
    }
    if (reason === "contingent_frontier") {
      return "⊥ — plusieurs continuations restent également compatibles : aucune nécessité unique n’est démontrée.";
    }
    return "⊥ — aucune continuation relationnelle n’est démontrée dans la version actuelle.";
  }

  async function sendMessage(text) {
    const conversation = currentConversation();
    if (!conversation) return;
    conversation.messages.push({ role: "user", content: text });
    if (conversation.messages.length === 1) conversation.title = text.trim().slice(0, 48) || "Conversation";
    appendMessageElement("user", text);
    const pending = appendMessageElement("assistant", "Calcul relationnel…", true);
    renderConversationList();
    saveConversations();
    try {
      const data = await api("infer", {
        objective: $("#modelSelect")?.value || "general",
        max_characters: 1200,
        messages: conversation.messages,
      });
      const output = data.output || abstentionMessage(data);
      pending.bubble.style.opacity = "";
      pending.bubble.textContent = output;
      window.ChatUI?.finalize?.(pending.bubble);
      conversation.messages.push({ role: "assistant", content: output });
      $("#pillModel").textContent = `model: ${data.model || "ANANKÉ"}`;
      $("#pillCost").textContent = `chars: ${formatNumber(data.characters)}`;
      $("#headerSub").textContent = `Référentiel v${data.version ?? "—"} · ${data.decisions ?? 0} décisions`;
      saveConversations();
    } catch (error) {
      pending.bubble.style.opacity = "";
      pending.bubble.textContent = `Erreur ANANKÉ : ${error.message}`;
      window.ChatUI?.finalize?.(pending.bubble);
    }
  }

  function bindChat() {
    const model = $("#modelSelect");
    if (model) {
      model.innerHTML = '<option value="general">ANANKÉ · Génératrice relationnelle</option><option value="grammaire">ANANKÉ · Grammaire</option><option value="strategie">ANANKÉ · Stratégie</option>';
    }
    $("#newChatBtn")?.addEventListener("click", () => createConversation(true));
    $("#composer")?.addEventListener("submit", async event => {
      event.preventDefault();
      const input = $("#input");
      const text = input?.value.trim();
      if (!text) return;
      input.value = "";
      input.dispatchEvent(new Event("input"));
      $("#sendBtn").disabled = true;
      try { await sendMessage(text); } finally { $("#sendBtn").disabled = false; input.focus(); }
    });
    $("#input")?.addEventListener("keydown", event => {
      if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        $("#composer")?.requestSubmit();
      }
    });
  }

  function openLearning() {
    $("#learningDrawer")?.classList.add("show");
    $("#learningDrawer")?.setAttribute("aria-hidden", "false");
    $("#learningScrim")?.classList.add("show");
  }

  function closeLearning() {
    $("#learningDrawer")?.classList.remove("show");
    $("#learningDrawer")?.setAttribute("aria-hidden", "true");
    $("#learningScrim")?.classList.remove("show");
  }

  function selectFile(file) {
    if (!file) return;
    if (file.size > MAX_UPLOAD) {
      state.selectedFile = null;
      $("#learningAnalyze").disabled = true;
      toast("Le fichier dépasse la limite de 50 Mo.");
      return;
    }
    state.selectedFile = file;
    $("#learningDropMain").textContent = file.name;
    $("#learningDropSub").textContent = `${formatBytes(file.size)} · prêt pour l’analyse comparative`;
    $("#learningAnalyze").disabled = false;
    $("#learningResult").innerHTML = "";
    state.analysisId = null;
  }

  function kpi(label, value) {
    return `<div class="kpi-card"><div class="kpi-value">${value}</div><div class="kpi-label">${label}</div></div>`;
  }

  function renderAnalysis(data) {
    state.analysisId = data.analysis_id;
    const contradictions = Array.isArray(data.contradictions) ? data.contradictions : [];
    const status = contradictions.length
      ? `<div class="analysis-warning">${contradictions.length} contradiction(s) détectée(s). La synchronisation est bloquée jusqu’à correction.</div>`
      : `<div class="analysis-ok">Analyse cohérente avec la version ${data.base_version}. La validation peut créer une nouvelle version transactionnelle.</div>`;
    const dimensions = (data.dimensions_to_add || []).map(value => `<code>${value}</code>`).join(", ") || "aucune";
    $("#learningResult").innerHTML = `
      ${status}
      <div class="kpi-grid">
        ${kpi("Volume", formatBytes(data.file?.bytes))}
        ${kpi("Caractères", formatNumber(data.characters))}
        ${kpi("Objets nouveaux", formatNumber(data.objects_new))}
        ${kpi("Relations observées", formatNumber(data.relations_observed))}
        ${kpi("Réutilisation", `${formatNumber(data.relation_reuse_percent)} %`)}
        ${kpi("Compression", `× ${formatNumber(data.compression_ratio)}`)}
        ${kpi("Familles nouvelles", formatNumber(data.relation_families_new))}
        ${kpi("Coordonnées proposées", formatNumber(data.coordinates_proposed))}
        ${kpi("Contradictions", formatNumber(contradictions.length))}
      </div>
      <div class="analysis-warning" style="background:var(--fill);border-color:var(--line);color:var(--muted)">
        Dimensions proposées : ${dimensions}<br>Temps d’analyse : ${formatNumber(data.elapsed_ms)} ms.
      </div>
      <div class="analysis-actions">
        <button class="secondary-action" type="button" id="analysisDiscard">Écarter</button>
        <button class="primary-action" type="button" id="analysisCommit" ${data.commit_allowed ? "" : "disabled"}>Synchroniser</button>
      </div>`;
    $("#analysisDiscard")?.addEventListener("click", async () => {
      try {
        await api("learning_discard", { analysis_id: state.analysisId });
        state.analysisId = null;
        $("#learningResult").innerHTML = "";
        toast("Analyse écartée.");
      } catch (error) {
        toast(`Échec de suppression : ${error.message}`);
      }
    });
    $("#analysisCommit")?.addEventListener("click", commitAnalysis);
  }

  async function analyzeFile() {
    if (!state.selectedFile) return;
    const progress = $("#learningProgress");
    progress?.classList.add("show");
    $("#learningAnalyze").disabled = true;
    try {
      const form = new FormData();
      form.append("action", "learning_analyze");
      form.append("objective", $("#learningObjective").value.trim() || "general");
      form.append("learning_file", state.selectedFile, state.selectedFile.name);
      const data = await api("learning_analyze", {}, { formData: form });
      renderAnalysis(data);
    } catch (error) {
      $("#learningResult").innerHTML = `<div class="analysis-warning">Analyse impossible : ${error.message}</div>`;
    } finally {
      progress?.classList.remove("show");
      $("#learningAnalyze").disabled = false;
    }
  }

  async function commitAnalysis() {
    if (!state.analysisId) return;
    const button = $("#analysisCommit");
    button.disabled = true;
    button.textContent = "Synchronisation…";
    try {
      const result = await api("learning_commit", { analysis_id: state.analysisId });
      $("#learningResult").innerHTML = `
        <div class="analysis-ok">Apprentissage intégré dans la version ${result.version_after}. Le cycle a été journalisé intégralement.</div>
        <div class="kpi-grid">
          ${kpi("Objets ajoutés", formatNumber(result.objects_added))}
          ${kpi("Dimensions ajoutées", formatNumber(result.dimensions_added))}
          ${kpi("Coordonnées ajoutées", formatNumber(result.coordinates_added))}
          ${kpi("Lois relationnelles", formatNumber(result.relation_rules_added))}
          ${kpi("Relations explicites", formatNumber(result.relations_added))}
          ${kpi("Version", formatNumber(result.version_after))}
        </div>`;
      state.analysisId = null;
      await loadReferential();
      await refreshStats();
    } catch (error) {
      $("#learningResult").insertAdjacentHTML("afterbegin", `<div class="analysis-warning">Synchronisation refusée : ${error.message}</div>`);
      button.disabled = false;
      button.textContent = "Synchroniser";
    }
  }

  function renderReferential(data) {
    const stats = data.stats || {};
    $("#referentialStats").innerHTML = [
      ["Version", stats.version], ["Objets", stats.objects], ["Dimensions", stats.dimensions], ["Coordonnées", stats.coordinates], ["Relations", stats.relations]
    ].map(([label, value]) => `<span class="chip">${label}: ${formatNumber(value)}</span>`).join("");
    const dimensions = data.dimensions || [];
    const objects = data.objects || [];
    $("#xyzGrid").innerHTML = ["x", "y", "z"].map(axis => {
      const count = objects.filter(object => object.coordinates?.[axis]).length;
      return `<div class="axis-card"><div class="axis-name">${axis}</div><div class="axis-count">${formatNumber(count)} objets</div></div>`;
    }).join("");
    $("#dimensionList").innerHTML = dimensions.filter(item => !["x", "y", "z"].includes(item.address)).map(item => `
      <div class="dimension-row">
        <div class="dimension-address">${item.address}</div>
        <div class="dimension-label">${item.label || "Dimension sans étiquette"}</div>
        <div class="dimension-logic">${item.logic}</div>
      </div>`).join("") || '<div class="analysis-warning">Aucune dimension logique supplémentaire dans cette vue.</div>';
    $("#objectGrid").innerHTML = objects.map(object => {
      const dynamic = Object.entries(object.coordinates || {}).filter(([address]) => !["x", "y", "z"].includes(address));
      const conceptual = [object.label, ...dynamic.slice(0, 12).map(([address, value]) => `${address} = ${value}`)].filter(Boolean).join(" · ");
      const xyz = ["x", "y", "z"].map(axis => `${axis}:${object.coordinates?.[axis] || "∅"}`).join("  ");
      return `<div class="object-card" data-tooltip="${escapeAttribute(conceptual || "Aucune étiquette conceptuelle")}">
        <div class="object-value">${escapeHtml(object.value)}</div>
        <div class="object-kind">${escapeHtml(object.kind)}</div>
        <div class="object-xyz">${escapeHtml(xyz)}</div>
      </div>`;
    }).join("") || '<div class="analysis-warning">Aucun objet trouvé.</div>';
  }

  function escapeHtml(value) {
    return String(value).replace(/[&<>"']/g, character => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[character]);
  }

  function escapeAttribute(value) {
    return escapeHtml(value).replace(/\n/g, " ");
  }

  async function loadReferential() {
    try {
      const data = await api("referential_view", {
        query: $("#referentialSearch")?.value.trim() || "",
        object_limit: 100,
        dimension_limit: 120,
      });
      renderReferential(data);
    } catch (error) {
      $("#objectGrid").innerHTML = `<div class="analysis-warning">Référentiel indisponible : ${error.message}</div>`;
    }
  }

  async function refreshStats() {
    try {
      const response = await fetch(`${endpoint}?action=stats`, { credentials: "same-origin", cache: "no-store" });
      const data = await response.json();
      if (!response.ok) return;
      $("#usageText").textContent = `${formatNumber(data.objects)} objets`;
      $("#usageFill").style.width = `${Math.min(100, Number(data.objects || 0) / 100)}%`;
      $("#version").textContent = `ANANKÉ v${data.version}`;
      $("#pillProvider").textContent = "provider: ANANKÉ";
      $("#headerSub").textContent = `Référentiel v${data.version} · ${formatNumber(data.dimensions)} dimensions`;
    } catch { /* état visuel conservé */ }
  }

  function bindLearning() {
    $("#learningBtn")?.addEventListener("click", () => { openLearning(); loadReferential(); });
    $("#learningClose")?.addEventListener("click", closeLearning);
    $("#learningScrim")?.addEventListener("click", closeLearning);
    $$('[data-learning-tab]').forEach(button => button.addEventListener("click", () => {
      $$('[data-learning-tab]').forEach(item => item.classList.toggle("active", item === button));
      const target = button.dataset.learningTab;
      $("#learningPaneIngestion").classList.toggle("active", target === "ingestion");
      $("#learningPaneReferential").classList.toggle("active", target === "referential");
      if (target === "referential") loadReferential();
    }));
    const dropZone = $("#learningDropZone");
    const input = $("#learningFile");
    input?.addEventListener("change", () => selectFile(input.files?.[0]));
    ["dragenter", "dragover"].forEach(type => dropZone?.addEventListener(type, event => {
      event.preventDefault(); dropZone.classList.add("dragover");
    }));
    ["dragleave", "drop"].forEach(type => dropZone?.addEventListener(type, event => {
      event.preventDefault(); dropZone.classList.remove("dragover");
    }));
    dropZone?.addEventListener("drop", event => selectFile(event.dataTransfer?.files?.[0]));
    $("#learningAnalyze")?.addEventListener("click", analyzeFile);
    $("#referentialRefresh")?.addEventListener("click", loadReferential);
    $("#referentialSearch")?.addEventListener("keydown", event => {
      if (event.key === "Enter") loadReferential();
    });
  }

  async function initialize() {
    bindChat();
    bindLearning();
    loadConversations();
    const granted = await checkAccess();
    if (granted) await refreshStats();
  }

  document.readyState === "loading" ? document.addEventListener("DOMContentLoaded", initialize) : initialize();
})();
