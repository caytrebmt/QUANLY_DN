(function () {
  "use strict";

  const PAGE_SIZES = [10, 20, 50, 100];

  function qs(selector, root) {
    return (root || document).querySelector(selector);
  }

  function qsa(selector, root) {
    return Array.from((root || document).querySelectorAll(selector));
  }

  function escapeHtml(str) {
    if (str == null) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function renderRows(table, data) {
    const tbody = table.tBodies[0];
    if (!tbody) return;
    tbody.innerHTML = "";

    if (!data || !data.length) {
      const tr = document.createElement("tr");
      tr.className = "erp-advanced-empty";
      const td = document.createElement("td");
      td.colSpan = table.tHead.rows[0].cells.length;
      td.className = "text-center";
      td.textContent = "Không tìm thấy dữ liệu phù hợp";
      tr.appendChild(td);
      tbody.appendChild(tr);
      return;
    }

    data.forEach((row) => {
      const tr = document.createElement("tr");
      Object.values(row).forEach((val) => {
        const td = document.createElement("td");
        td.textContent = val;
        tr.appendChild(td);
      });
      tbody.appendChild(tr);
    });
  }

  function buildToolbar() {
    const toolbar = document.createElement("div");
    toolbar.className = "erp-advanced-toolbar";
    toolbar.innerHTML = `
      <div class="erp-advanced-left">
        <input class="erp-advanced-search" type="search" placeholder="Tìm nhanh..." autocomplete="off">
      </div>
      <div class="erp-advanced-right">
        <label class="erp-advanced-info">Hiển thị
          <select class="erp-advanced-size"></select>
        </label>
        <span class="erp-advanced-info" data-role="count"></span>
      </div>
    `;
    return toolbar;
  }

  function buildPagination() {
    const nav = document.createElement("nav");
    nav.setAttribute("aria-label", "Server-side pagination");
    const ul = document.createElement("ul");
    ul.className = "pagination pagination-sm mb-0";
    nav.appendChild(ul);
    return nav;
  }

  function enhanceServerTable(table) {
    if (table.dataset.erpServerReady === "1") return;
    if (!table.dataset.serverSide || table.dataset.serverSide !== "true") return;
    if (!table.tHead || !table.tBodies.length || !table.tHead.rows.length) return;

    table.dataset.erpServerReady = "1";
    const ajaxUrl = (table.dataset.ajaxUrl || "").trim();
    if (!ajaxUrl) {
      console.warn("erp-advanced-table: missing data-ajax-url on server-side table", table);
      return;
    }

    const headers = Array.from(table.tHead.rows[0].cells);
    const wrap = ensureWrapper(table);
    const toolbar = buildToolbar();
    wrap.insertBefore(toolbar, wrap.firstChild);

    const paginationEl = buildPagination();
    wrap.appendChild(paginationEl);

    const searchInput = toolbar.querySelector(".erp-advanced-search");
    const countEl = toolbar.querySelector('[data-role="count"]');
    const sizeSelect = toolbar.querySelector(".erp-advanced-size");

    PAGE_SIZES.forEach((size) => {
      const opt = document.createElement("option");
      opt.value = size;
      opt.textContent = size === "all" ? "Tất cả" : size;
      sizeSelect.appendChild(opt);
    });

    let currentPage = 1;
    let perPage = 20;
    let totalRecords = 0;
    let filteredRecords = 0;
    let sortColumn = "";
    let sortDir = "asc";

    function buildUrl(page) {
      const url = new URL(ajaxUrl, window.location.origin);
      url.searchParams.set("page", String(page));
      url.searchParams.set("per_page", String(perPage));
      if (searchInput.value.trim()) {
        url.searchParams.set("search", searchInput.value.trim());
      }
      if (sortColumn) {
        url.searchParams.set("sort_column", sortColumn);
        url.searchParams.set("sort_dir", sortDir);
      }
      return url.toString();
    }

    function renderPagination() {
      const ul = paginationEl.querySelector("ul");
      ul.innerHTML = "";

      const totalPages = Math.max(1, Math.ceil(filteredRecords / perPage));
      const createItem = (label, page, disabled, active) => {
        const li = document.createElement("li");
        li.className = "page-item" + (active ? " active" : "") + (disabled ? " disabled" : "");
        const a = document.createElement("a");
        a.className = "page-link";
        a.href = disabled ? "#" : "#";
        a.textContent = label;
        a.addEventListener("click", (e) => {
          e.preventDefault();
          if (!disabled && page !== currentPage) {
            currentPage = page;
            loadData();
          }
        });
        li.appendChild(a);
        return li;
      };

      ul.appendChild(createItem("‹", currentPage - 1, currentPage === 1, false));
      for (let p = Math.max(1, currentPage - 2); p <= Math.min(totalPages, currentPage + 2); p++) {
        ul.appendChild(createItem(String(p), p, false, p === currentPage));
      }
      ul.appendChild(createItem("›", currentPage + 1, currentPage === totalPages, false));
    }

    function loadData() {
      const url = buildUrl(currentPage);
      fetch(url, { headers: { "X-Requested-With": "XMLHttpRequest" } })
        .then((res) => {
          if (!res.ok) throw new Error("HTTP " + res.status);
          return res.json();
        })
        .then((json) => {
          totalRecords = json.recordsTotal || 0;
          filteredRecords = json.recordsFiltered || 0;
          renderRows(table, json.data || []);
          countEl.textContent = `${Math.min(perPage, filteredRecords)}/${filteredRecords} dòng`;
          renderPagination();
        })
        .catch((err) => {
          console.error("erp-advanced-table server load failed:", err);
          const tbody = table.tBodies[0];
          if (tbody) {
            tbody.innerHTML = `<tr><td colspan="${headers.length}" class="text-center text-danger">Không tải được dữ liệu</td></tr>`;
          }
        });
    }

    searchInput.addEventListener("input", () => {
      currentPage = 1;
      loadData();
    });

    sizeSelect.addEventListener("change", () => {
      perPage = sizeSelect.value === "all" ? 9999 : Number(sizeSelect.value);
      currentPage = 1;
      loadData();
    });

    headers.forEach((th, index) => {
      th.style.cursor = "pointer";
      th.addEventListener("click", () => {
        if (sortColumn === String(index)) {
          sortDir = sortDir === "asc" ? "desc" : "asc";
        } else {
          sortColumn = String(index);
          sortDir = "asc";
        }
        loadData();
      });
    });

    sizeSelect.value = String(perPage);
    loadData();
  }

  function ensureWrapper(table) {
    const responsive = table.closest(".table-responsive");
    const anchor = responsive || table;
    if (anchor.parentElement && anchor.parentElement.classList.contains("erp-advanced-wrap")) {
      return anchor.parentElement;
    }
    const wrap = document.createElement("div");
    wrap.className = "erp-advanced-wrap";
    anchor.parentNode.insertBefore(wrap, anchor);
    wrap.appendChild(anchor);
    return wrap;
  }

  function init() {
    qsa("table[data-server-side='true']").forEach(enhanceServerTable);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
