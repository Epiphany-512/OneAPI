/* ── OneAPI Dashboard — app.js ───────────────────────────────────── */

(function () {
  "use strict";

  const API = "/dashboard/api";
  const AUTH_KEY = () => localStorage.getItem("oneapi_key") || "";

  // ── Helpers ──────────────────────────────────────────────────────

  function $(sel) { return document.querySelector(sel); }
  function $$(sel) { return document.querySelectorAll(sel); }

  async function api(path, opts = {}) {
    const key = AUTH_KEY();
    const headers = { "Content-Type": "application/json" };
    if (key) headers["Authorization"] = "Bearer " + key;
    const res = await fetch(API + path, { ...opts, headers });
    if (res.status === 401) {
      promptAuth();
      throw new Error("Unauthorized");
    }
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body.detail || body.error?.message || res.statusText);
    }
    return res.json();
  }

  function promptAuth() {
    const key = localStorage.getItem("oneapi_key");
    const input = prompt("请输入 OneAPI 管理密钥 (oneapi_api_key):", key || "");
    if (input !== null) {
      localStorage.setItem("oneapi_key", input.trim());
      location.reload();
    }
  }

  function toast(msg, type = "") {
    const el = $("#toast");
    el.textContent = msg;
    el.className = "toast show" + (type ? " toast-" + type : "");
    clearTimeout(el._timer);
    el._timer = setTimeout(() => { el.className = "toast"; }, 3000);
  }

  function showModal(title, body) {
    $("#modalTitle").textContent = title;
    $("#modalBody").textContent = body;
    $("#modalOverlay").classList.add("show");
  }

  function fmtTime(ts) {
    if (!ts) return "--";
    const d = new Date(ts * 1000);
    return d.toLocaleString("zh-CN", { hour12: false });
  }

  function badge(text, cls) {
    return `<span class="badge ${cls}">${text}</span>`;
  }

  // ── Navigation ──────────────────────────────────────────────────

  function initNav() {
    const navItems = $$(".nav-item");
    const pages = $$(".page");

    navItems.forEach(item => {
      item.addEventListener("click", e => {
        e.preventDefault();
        const page = item.dataset.page;
        navItems.forEach(n => n.classList.remove("active"));
        item.classList.add("active");
        pages.forEach(p => p.classList.remove("active"));
        const target = $(`#page-${page}`);
        if (target) target.classList.add("active");
        // Close mobile sidebar
        $("#sidebar").classList.remove("open");
        // Load page data
        loadPage(page);
      });
    });

    // Mobile menu
    $("#menuBtn")?.addEventListener("click", () => {
      $("#sidebar").classList.toggle("open");
    });

    // Close modal
    $("#modalClose")?.addEventListener("click", () => {
      $("#modalOverlay").classList.remove("show");
    });
    $("#modalOverlay")?.addEventListener("click", e => {
      if (e.target === e.currentTarget) $("#modalOverlay").classList.remove("show");
    });
  }

  let currentPage = "overview";

  function loadPage(page) {
    currentPage = page;
    switch (page) {
      case "overview": loadOverview(); break;
      case "models": loadModels(); break;
      case "routes": loadRoutes(); break;
      case "logs": loadLogs(); break;
      case "keys": loadKeys(); break;
    }
  }

  // ── Overview ─────────────────────────────────────────────────────

  async function loadOverview() {
    try {
      const [status, usage] = await Promise.all([
        api("/status"),
        api("/usage"),
      ]);

      // Version
      $("#version").textContent = "v" + status.version;

      // Cards
      $("#uptime").textContent = status.uptime;
      $("#modelCount").textContent = status.total_models;
      $("#providerCount").textContent = status.total_providers;
      $("#totalRequests").textContent = usage.total_requests;

      // Provider table
      const tbody = $("#providerTable tbody");
      tbody.innerHTML = status.all_providers.map(p => {
        const cls = p.status === "active" ? "badge-ok" : "badge-warn";
        const label = p.status === "active" ? "✅ 已激活" : "⚠️ 无密钥";
        // Get base_url from registered providers
        const reg = (status.registered_providers || []).find(r => r.name === p.name);
        const url = reg ? reg.base_url : "--";
        return `<tr>
          <td><strong>${p.name}</strong></td>
          <td style="color:var(--text-dim);font-size:.82rem">${url}</td>
          <td>${badge(label, cls)}</td>
        </tr>`;
      }).join("");

      // Usage stats
      $("#successCount").textContent = usage.success_count;
      $("#errorCount").textContent = usage.error_count;
      const rate = usage.total_requests > 0
        ? ((usage.success_count / usage.total_requests) * 100).toFixed(1) + "%"
        : "--";
      $("#successRate").textContent = rate;

      // Connection status
      $("#statusDot").className = "status-dot ok";
      $("#statusText").textContent = "已连接";
    } catch (e) {
      $("#statusDot").className = "status-dot err";
      $("#statusText").textContent = "连接失败";
      toast("加载失败: " + e.message, "error");
    }
  }

  // ── Models ───────────────────────────────────────────────────────

  let allModels = [];

  async function loadModels() {
    try {
      const data = await api("/models");
      allModels = data.models || [];
      renderModels(allModels);
    } catch (e) {
      toast("加载模型失败: " + e.message, "error");
    }
  }

  function renderModels(models) {
    const tbody = $("#modelTable tbody");
    tbody.innerHTML = models.map(m => {
      const statusBadge = m.active
        ? badge("✅ 可用", "badge-ok")
        : badge("⚠️ 不可用", "badge-warn");
      const fallback = m.fallback && m.fallback.length
        ? m.fallback.join(" → ")
        : "<span style='color:var(--text-muted)'>无</span>";
      return `<tr>
        <td><strong>${m.id}</strong></td>
        <td>${m.provider}</td>
        <td>${fallback}</td>
        <td>${statusBadge}</td>
      </tr>`;
    }).join("");
  }

  // Model search
  function initModelSearch() {
    $("#modelSearch")?.addEventListener("input", e => {
      const q = e.target.value.toLowerCase();
      const filtered = allModels.filter(m =>
        m.id.toLowerCase().includes(q) ||
        m.provider.toLowerCase().includes(q)
      );
      renderModels(filtered);
    });
  }

  // ── Routes ───────────────────────────────────────────────────────

  let currentRoutes = {};

  async function loadRoutes() {
    try {
      const data = await api("/routes");
      currentRoutes = data.routes || {};
      renderRoutes(currentRoutes);
    } catch (e) {
      toast("加载路由失败: " + e.message, "error");
    }
  }

  function renderRoutes(routes) {
    const tbody = $("#routeTable tbody");
    tbody.innerHTML = Object.entries(routes).map(([model, info]) => {
      const fallback = info.fallback && info.fallback.length
        ? info.fallback.join(", ")
        : "<span style='color:var(--text-muted)'>无</span>";
      return `<tr>
        <td><strong>${model}</strong></td>
        <td>${info.provider}</td>
        <td>${fallback}</td>
        <td><button class="btn btn-danger btn-sm" data-route-del="${model}">删除</button></td>
      </tr>`;
    }).join("");

    // Delete buttons
    tbody.querySelectorAll("[data-route-del]").forEach(btn => {
      btn.addEventListener("click", () => {
        const model = btn.dataset.routeDel;
        delete currentRoutes[model];
        renderRoutes(currentRoutes);
        toast(`已移除路由: ${model}`);
      });
    });
  }

  function initRouteForm() {
    // Add route
    $("#routeAddBtn")?.addEventListener("click", () => {
      const model = $("#routeModel").value.trim();
      const provider = $("#routeProvider").value.trim();
      const fallbackStr = $("#routeFallback").value.trim();

      if (!model || !provider) {
        toast("请填写模型 ID 和 Provider", "error");
        return;
      }

      const fallback = fallbackStr
        ? fallbackStr.split(",").map(s => s.trim()).filter(Boolean)
        : [];
      currentRoutes[model] = { provider, fallback };
      renderRoutes(currentRoutes);

      // Clear inputs
      $("#routeModel").value = "";
      $("#routeProvider").value = "";
      $("#routeFallback").value = "";
      toast(`路由已添加: ${model} → ${provider}`, "success");
    });

    // Save all routes
    $("#saveRoutesBtn")?.addEventListener("click", async () => {
      try {
        // Convert to flat format for API
        const flatRoutes = {};
        for (const [model, info] of Object.entries(currentRoutes)) {
          if (info.fallback && info.fallback.length) {
            flatRoutes[model] = [info.provider, ...info.fallback];
          } else {
            flatRoutes[model] = info.provider;
          }
        }
        const res = await api("/routes", {
          method: "POST",
          body: JSON.stringify({ routes: flatRoutes }),
        });
        toast(`路由已保存 (${res.routes_count} 条)`, "success");
        loadRoutes();
      } catch (e) {
        toast("保存失败: " + e.message, "error");
      }
    });
  }

  // ── Logs ─────────────────────────────────────────────────────────

  async function loadLogs() {
    try {
      const data = await api("/logs?limit=200");
      const logs = data.logs || [];
      const filter = ($("#logFilter")?.value || "all");

      const filtered = filter === "all"
        ? logs
        : logs.filter(l => l.status === filter);

      renderLogs(filtered);

      const empty = $("#logEmpty");
      if (filtered.length === 0) {
        empty.style.display = "block";
      } else {
        empty.style.display = "none";
      }
    } catch (e) {
      toast("加载日志失败: " + e.message, "error");
    }
  }

  function renderLogs(logs) {
    const tbody = $("#logTable tbody");
    tbody.innerHTML = logs.reverse().map(l => {
      const statusBadge = l.status === "success"
        ? badge("成功", "badge-ok")
        : badge("失败", "badge-err");
      return `<tr>
        <td style="white-space:nowrap">${l.time_str || fmtTime(l.timestamp)}</td>
        <td>${l.model}</td>
        <td>${l.provider}</td>
        <td>${statusBadge}</td>
        <td>${l.total_tokens || 0}</td>
        <td>${l.latency_ms ? l.latency_ms + "ms" : "--"}</td>
      </tr>`;
    }).join("");
  }

  function initLogControls() {
    $("#refreshLogs")?.addEventListener("click", loadLogs);
    $("#logFilter")?.addEventListener("change", loadLogs);
  }

  // ── Keys ─────────────────────────────────────────────────────────

  async function loadKeys() {
    try {
      const data = await api("/keys");
      const keys = data.keys || [];
      renderKeys(keys);

      const empty = $("#keyEmpty");
      empty.style.display = keys.length === 0 ? "block" : "none";
    } catch (e) {
      toast("加载 Key 失败: " + e.message, "error");
    }
  }

  function renderKeys(keys) {
    const tbody = $("#keyTable tbody");
    tbody.innerHTML = keys.map(k => {
      const statusBadge = k.active
        ? badge("✅ 活跃", "badge-ok")
        : badge("已吊销", "badge-err");
      return `<tr>
        <td>${k.name}</td>
        <td><code style="font-size:.82rem;color:var(--accent)">${k.key}</code></td>
        <td style="white-space:nowrap">${fmtTime(k.created)}</td>
        <td>${statusBadge}</td>
        <td>
          ${k.active
            ? `<button class="btn btn-secondary btn-sm" data-key-action="revoke" data-key-id="${k.id}">吊销</button>`
            : ""}
          <button class="btn btn-danger btn-sm" data-key-action="delete" data-key-id="${k.id}" style="margin-left:.3rem">删除</button>
        </td>
      </tr>`;
    }).join("");

    // Action buttons
    tbody.querySelectorAll("[data-key-action]").forEach(btn => {
      btn.addEventListener("click", async () => {
        const action = btn.dataset.keyAction;
        const id = btn.dataset.keyId;
        try {
          await api("/keys", {
            method: "POST",
            body: JSON.stringify({ action, id }),
          });
          toast(action === "revoke" ? "Key 已吊销" : "Key 已删除", "success");
          loadKeys();
        } catch (e) {
          toast("操作失败: " + e.message, "error");
        }
      });
    });
  }

  function initKeyControls() {
    $("#createKeyBtn")?.addEventListener("click", async () => {
      const name = ($("#keyName")?.value || "").trim() || "unnamed";
      try {
        const res = await api("/keys", {
          method: "POST",
          body: JSON.stringify({ action: "create", name }),
        });
        showModal("API Key 已创建", `Key: ${res.key}\n名称: ${res.name}`);
        $("#keyName").value = "";
        loadKeys();
      } catch (e) {
        toast("创建失败: " + e.message, "error");
      }
    });
  }

  // ── Init ─────────────────────────────────────────────────────────

  function init() {
    if (!AUTH_KEY()) {
      promptAuth();
      return;
    }
    initNav();
    initModelSearch();
    initRouteForm();
    initLogControls();
    initKeyControls();
    loadOverview();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
