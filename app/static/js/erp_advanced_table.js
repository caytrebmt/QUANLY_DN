(function () {
  "use strict";

  const MIN_ROWS = 8;
  const PAGE_SIZES = [10, 20, 50, 100, "all"];
  const STORAGE_KEY = "erp_advanced_table_state";
  const RESIZE_MIN_WIDTH = 40;
  const RESIZE_MAX_WIDTH = 600;

  function normalizeText(value) {
    return (value || "")
      .toString()
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .replace(/đ/g, "d")
      .replace(/Đ/g, "D")
      .toLowerCase()
      .trim();
  }

  function cleanHeaderText(th) {
    return (th.textContent || "").replace(/[↕↑↓]/g, "").replace(/\s+/g, " ").trim() || "Cột";
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

  function buildToolbar(lightMode) {
    const toolbar = document.createElement("div");
    toolbar.className = "erp-advanced-toolbar";
  /*  if (lightMode) {
      toolbar.innerHTML = `
        <div class="erp-advanced-left">
          <input class="erp-advanced-search" type="search" placeholder="Tìm nhanh trong bảng..." autocomplete="off">
          <button type="button" class="erp-advanced-btn" data-role="toggle-filters" title="Lọc theo cột">🎚️cột</button>
          <div class="erp-column-menu-wrap">
            <button type="button" class="erp-advanced-btn" data-role="toggle-columns" title="Ẩn hiện cột">⚙️ Ẩn hiện cột</button>
            <div class="erp-column-menu" data-role="column-menu"></div>
          </div>
        </div>
        <div class="erp-advanced-right">
          <button type="button" class="erp-advanced-reset">Xóa lọc</button>
        </div>
      `;
    } else {
      toolbar.innerHTML = `
        <div class="erp-advanced-left">
          <input class="erp-advanced-search" type="search" placeholder="Tìm nhanh trong bảng..." autocomplete="off">
          <button type="button" class="erp-advanced-btn" data-role="toggle-filters" title="Lọc theo cột">🎚️cột</button>
          <div class="erp-column-menu-wrap">
            <button type="button" class="erp-advanced-btn" data-role="toggle-columns" title="Ẩn hiện cột">⚙️ Ẩn hiện cột</button>
            <div class="erp-column-menu" data-role="column-menu"></div>
          </div>
        </div>
        <div class="erp-advanced-right">
          <label class="erp-advanced-info">Hiển thị
            <select class="erp-advanced-size"></select>
          </label>
          <span class="erp-advanced-info" data-role="count"></span>
          <button type="button" class="erp-advanced-reset">Xóa lọc</button>
        </div>
      `;
    }*/
    return toolbar;
  }

  function loadSavedState(tableId) {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return null;
      const all = JSON.parse(raw);
      return all[tableId] || null;
    } catch (e) {
      return null;
    }
  }

  function saveState(tableId, state) {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      const all = raw ? JSON.parse(raw) : {};
      all[tableId] = state;
      localStorage.setItem(STORAGE_KEY, JSON.stringify(all));
    } catch (e) {
      // ignore storage errors
    }
  }

  function setupColumnResize(table, headers) {
    const tableId = table.id || ("tbl_" + Math.random().toString(36).slice(2, 9));
    table.id = tableId;

    const saved = loadSavedState(tableId);
    const colWidths = saved?.colWidths || headers.map(() => null);

    headers.forEach((th, index) => {
      const handle = document.createElement("div");
      handle.className = "erp-col-resize-handle";
      handle.dataset.columnIndex = String(index);
      th.appendChild(handle);
      th.style.position = "relative";

      if (colWidths[index]) {
        th.style.width = colWidths[index];
        th.style.minWidth = colWidths[index];
      }
    });

    let startX = 0;
    let startWidth = 0;
    let thIndex = null;
    let resizing = false;

    function onMouseDown(event) {
      const handle = event.target.closest(".erp-col-resize-handle");
      if (!handle) return;
      event.preventDefault();
      thIndex = Number(handle.dataset.columnIndex);
      startX = event.clientX;
      const th = headers[thIndex];
      startWidth = th.getBoundingClientRect().width;
      resizing = true;
      handle.classList.add("erp-resizing");
      table.classList.add("table-resizing");
    }

    function onMouseMove(event) {
      if (!resizing) return;
      const dx = event.clientX - startX;
      const newWidth = Math.max(RESIZE_MIN_WIDTH, Math.min(RESIZE_MAX_WIDTH, startWidth + dx));
      headers[thIndex].style.width = newWidth + "px";
      headers[thIndex].style.minWidth = newWidth + "px";
    }

    function onMouseUp() {
      if (!resizing) return;
      resizing = false;
      table.classList.remove("table-resizing");
      const widths = headers.map(th => th.style.width || null);
      saveState(tableId, { colWidths: widths });
    }

    table.addEventListener("mousedown", onMouseDown);
    document.addEventListener("mousemove", onMouseMove);
    document.addEventListener("mouseup", onMouseUp);

    return {
      save: function () {
        const widths = headers.map(th => th.style.width || null);
        saveState(tableId, { colWidths: widths });
      },
      destroy: function () {
        table.removeEventListener("mousedown", onMouseDown);
        document.removeEventListener("mousemove", onMouseMove);
        document.removeEventListener("mouseup", onMouseUp);
      },
    };
  }

  function applyColumnVisibility(table, headers, filterRow, columnVisible) {
    headers.forEach((th, index) => th.style.display = columnVisible[index] ? "" : "none");
    if (filterRow) {
      Array.from(filterRow.cells).forEach((th, index) => th.style.display = columnVisible[index] ? "" : "none");
    }
    Array.from(table.tBodies[0].rows).forEach((row) => {
      Array.from(row.children).forEach((cell, index) => {
        if (cell) cell.style.display = columnVisible[index] ? "" : "none";
      });
    });
  }

  function enhanceTable(table) {
    if (table.dataset.erpAdvancedReady === "1") return;
    if (table.dataset.advancedTable === "false") return;
    if (!table.tHead || !table.tBodies.length || !table.tHead.rows.length) return;

    const tbody = table.tBodies[0];
    const headerRow = table.tHead.rows[0];
    const headers = Array.from(headerRow.cells);
    const originalRows = Array.from(tbody.rows).filter((row) => !row.classList.contains("erp-advanced-empty"));
    const lightMode = table.dataset.advancedTable === "light";

    if (!lightMode) {
      if (originalRows.length < MIN_ROWS && table.dataset.advancedTable !== "true") return;
    }

    table.dataset.erpAdvancedReady = "1";
    table.classList.add("erp-sortable");

    const wrap = ensureWrapper(table);
    const toolbar = buildToolbar(lightMode);
    wrap.insertBefore(toolbar, wrap.firstChild);

    const resizeController = setupColumnResize(table, headers);
    const columnToggle = toolbar.querySelector('[data-role="toggle-columns"]');
    const columnMenu = toolbar.querySelector('[data-role="column-menu"]');
    columnMenu.innerHTML = headers.map((th, index) => `
      <label class="erp-column-option">
        <input type="checkbox" data-column-index="${index}" checked>
        <span>${cleanHeaderText(th)}</span>
      </label>
    `).join("");

    columnToggle.addEventListener("click", (event) => {
      event.stopPropagation();
      columnMenu.classList.toggle("open");
    });

    const columnVisible = headers.map(() => true);

    columnMenu.addEventListener("click", (event) => {
      event.stopPropagation();
      const checkbox = event.target.closest('input[type="checkbox"][data-column-index]');
      if (!checkbox) return;
      const index = Number(checkbox.dataset.columnIndex);
      columnVisible[index] = checkbox.checked;
      applyColumnVisibility(table, headers, null, columnVisible);
      resizeController.save();
    });

    document.addEventListener("click", () => columnMenu.classList.remove("open"));

    if (lightMode) {
      const searchInput = toolbar.querySelector(".erp-advanced-search");
      const resetBtn = toolbar.querySelector(".erp-advanced-reset");
      const filterToggle = toolbar.querySelector('[data-role="toggle-filters"]');
      let debounceTimer = null;
      let filtersVisible = false;

      const filterRow = document.createElement("tr");
      filterRow.className = "erp-column-filter-row d-none";
      headers.forEach((th, index) => {
        const filterTh = document.createElement("th");
        const input = document.createElement("input");
        input.type = "search";
        input.className = "erp-column-filter";
        input.placeholder = `${cleanHeaderText(th)}`;
        input.dataset.columnIndex = String(index);
        filterTh.appendChild(input);
        filterRow.appendChild(filterTh);
      });
      table.tHead.appendChild(filterRow);
      const filterInputs = Array.from(filterRow.querySelectorAll(".erp-column-filter"));

      searchInput.addEventListener("input", () => {
        const form = table.closest("form");
        if (!form) return;
        const searchField = form.querySelector('input[name="search"], input[name="q"], input[name="keyword"]');
        if (searchField) {
          searchField.value = searchInput.value;
        }
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => {
          form.requestSubmit();
        }, 400);
      });

      filterToggle.addEventListener("click", () => {
        filtersVisible = !filtersVisible;
        filterRow.classList.toggle("d-none", !filtersVisible);
        filterToggle.classList.toggle("active", filtersVisible);
      });

      filterInputs.forEach((input) => {
        input.addEventListener("input", () => {
          const form = table.closest("form");
          if (!form) return;
          const searchField = form.querySelector('input[name="search"], input[name="q"], input[name="keyword"]');
          if (searchField) {
            searchField.value = input.value;
          }
          clearTimeout(debounceTimer);
          debounceTimer = setTimeout(() => {
            form.requestSubmit();
          }, 400);
        });
      });

      resetBtn.addEventListener("click", () => {
        searchInput.value = "";
        filterInputs.forEach((input) => { input.value = ""; });
        clearTimeout(debounceTimer);
        const form = table.closest("form");
        if (form) {
          const searchField = form.querySelector('input[name="search"], input[name="q"], input[name="keyword"]');
          if (searchField) {
            searchField.value = "";
          }
          form.requestSubmit();
        }
      });

      // Row expansion
      const expandUrl = (table.dataset.expandUrl || "").trim();
      if (expandUrl) {
        tbody.addEventListener("click", (event) => {
          const row = event.target.closest("tr");
          if (!row || row.parentElement !== tbody) return;
          if (event.target.closest("a, button, input, select, textarea")) return;

          const existingDetail = row.nextElementSibling;
          if (existingDetail && existingDetail.classList.contains("erp-row-detail")) {
            existingDetail.remove();
            row.classList.remove("erp-row-expanded");
            return;
          }

          document.querySelectorAll(".erp-row-detail").forEach((el) => el.remove());
          document.querySelectorAll(".erp-row-expanded").forEach((el) => el.classList.remove("erp-row-expanded"));

          const detailRow = document.createElement("tr");
          detailRow.className = "erp-row-detail";
          const detailCell = document.createElement("td");
          detailCell.colSpan = headers.length;
          detailCell.innerHTML = '<div class="erp-row-detail-content text-center text-muted py-3">Đang tải...</div>';
          detailRow.appendChild(detailCell);
          row.after(detailRow);
          row.classList.add("erp-row-expanded");

          const firstCell = row.children[0];
          const recordId = firstCell ? firstCell.textContent.trim() : "";
          if (!recordId) return;

          fetch(`${expandUrl}?id=${encodeURIComponent(recordId)}`, {
            headers: { "X-Requested-With": "XMLHttpRequest" },
          })
            .then((res) => {
              if (!res.ok) throw new Error("HTTP " + res.status);
              return res.text();
            })
            .then((html) => {
              detailCell.innerHTML = html || '<div class="text-center text-muted py-3">Không có dữ liệu chi tiết</div>';
            })
            .catch(() => {
              detailCell.innerHTML = '<div class="text-center text-danger py-3">Không tải được chi tiết</div>';
            });
        });
      }

      return;
    }

    // Full mode: giữ nguyên logic cũ
    const sizeSelect = toolbar.querySelector(".erp-advanced-size");
    const searchInput = toolbar.querySelector(".erp-advanced-search");
    const countEl = toolbar.querySelector('[data-role="count"]');
    const resetBtn = toolbar.querySelector(".erp-advanced-reset");
    const filterToggle = toolbar.querySelector('[data-role="toggle-filters"]');

    let sortIndex = null;
    let sortDir = "asc";
    let filtersVisible = false;
    const columnVisibleFull = headers.map(() => true);

    PAGE_SIZES.forEach(size => {
      const opt = document.createElement("option");
      opt.value = size;
      opt.textContent = size === "all" ? "Tất cả" : size;
      sizeSelect.appendChild(opt);
    });

    const filterRow = document.createElement("tr");
    filterRow.className = "erp-column-filter-row d-none";
    headers.forEach((th, index) => {
      const filterTh = document.createElement("th");
      const input = document.createElement("input");
      input.type = "search";
      input.className = "erp-column-filter";
      input.placeholder = `${cleanHeaderText(th)}`;
      input.dataset.columnIndex = String(index);
      filterTh.appendChild(input);
      filterRow.appendChild(filterTh);
    });
    table.tHead.appendChild(filterRow);
    const filterInputs = Array.from(filterRow.querySelectorAll(".erp-column-filter"));

    function visibleColumnCount() {
      return columnVisibleFull.filter(Boolean).length || headers.length;
    }

    function applyColumnVisibilityFull(targetRows) {
      headers.forEach((th, index) => th.style.display = columnVisibleFull[index] ? "" : "none");
      Array.from(filterRow.cells).forEach((th, index) => th.style.display = columnVisibleFull[index] ? "" : "none");
      targetRows.forEach((row) => {
        Array.from(row.children).forEach((cell, index) => {
          if (cell) cell.style.display = columnVisibleFull[index] ? "" : "none";
        });
      });
    }

    function rowMatchesFilters(row) {
      return filterInputs.every((input) => {
        const term = normalizeText(input.value);
        if (!term) return true;
        const index = Number(input.dataset.columnIndex);
        return cellValue(row, index).includes(term);
      });
    }

    function apply() {
      const term = normalizeText(searchInput.value);
      let visibleRows = originalRows.filter((row) => {
        const globalMatch = !term || normalizeText(row.textContent).includes(term);
        return globalMatch && rowMatchesFilters(row);
      });

      if (sortIndex !== null) {
        visibleRows.sort((ra, rb) => {
          const result = smartCompare(cellValue(ra, sortIndex), cellValue(rb, sortIndex));
          return sortDir === "asc" ? result : -result;
        });
      }

      const size = sizeSelect.value === "all" ? visibleRows.length : Number(sizeSelect.value || 20);
      const shownRows = visibleRows.slice(0, size);

      tbody.innerHTML = "";
      shownRows.forEach((row) => tbody.appendChild(row));

      if (!shownRows.length) {
        const tr = document.createElement("tr");
        tr.className = "erp-advanced-empty";
        const td = document.createElement("td");
        td.colSpan = visibleColumnCount();
        td.className = "text-center";
        td.textContent = "Không tìm thấy dữ liệu phù hợp";
        tr.appendChild(td);
        tbody.appendChild(tr);
      }

      applyColumnVisibilityFull(shownRows);
      countEl.textContent = `${shownRows.length}/${visibleRows.length} dòng`;
      resizeController.save();
    }

    headers.forEach((th, index) => {
      if (th.classList.contains("no-sort") || th.classList.contains("no-print")) return;
      th.dataset.erpSort = "1";
      th.addEventListener("click", (event) => {
        if (event.target.closest("input, button, select, a")) return;
        headers.forEach((cell) => { if(cell !== th) cell.removeAttribute("data-erp-sort-dir"); });
        if (sortIndex === index) {
          sortDir = sortDir === "asc" ? "desc" : "asc";
        } else {
          sortIndex = index;
          sortDir = "asc";
        }
        th.dataset.erpSortDir = sortDir;
        apply();
      });
    });

    searchInput.addEventListener("input", apply);
    filterInputs.forEach((input) => input.addEventListener("input", apply));
    sizeSelect.addEventListener("change", apply);

    filterToggle.addEventListener("click", () => {
      filtersVisible = !filtersVisible;
      filterRow.classList.toggle("d-none", !filtersVisible);
      filterToggle.classList.toggle("active", filtersVisible);
    });

    columnToggle.addEventListener("click", (event) => {
      event.stopPropagation();
      columnMenu.classList.toggle("open");
    });

    columnMenu.addEventListener("click", (event) => {
      event.stopPropagation();
      const checkbox = event.target.closest('input[type="checkbox"][data-column-index]');
      if (!checkbox) return;
      const index = Number(checkbox.dataset.columnIndex);
      columnVisibleFull[index] = checkbox.checked;
      apply();
    });

    document.addEventListener("click", () => columnMenu.classList.remove("open"));

    resetBtn.addEventListener("click", () => {
      searchInput.value = "";
      filterInputs.forEach((input) => { input.value = ""; });
      sizeSelect.value = originalRows.length > 20 ? "20" : "all";
      sortIndex = null;
      sortDir = "asc";
      filtersVisible = false;
      filterRow.classList.add("d-none");
      filterToggle.classList.remove("active");
      columnMenu.classList.remove("open");
      columnVisibleFull.fill(true);
      columnMenu.querySelectorAll('input[type="checkbox"]').forEach((input) => { input.checked = true; });
      headers.forEach((cell) => cell.removeAttribute("data-erp-sort-dir"));
      apply();
    });

    const expandUrl = (table.dataset.expandUrl || "").trim();
    if (expandUrl) {
      originalRows.forEach((row) => row.setAttribute("data-expandable", "true"));

      tbody.addEventListener("click", (event) => {
        const row = event.target.closest("tr[data-expandable]");
        if (!row || row.parentElement !== tbody) return;
        if (event.target.closest("a, button, input, select, textarea")) return;

        const existingDetail = row.nextElementSibling;
        if (existingDetail && existingDetail.classList.contains("erp-row-detail")) {
          existingDetail.remove();
          row.classList.remove("erp-row-expanded");
          return;
        }

        document.querySelectorAll(".erp-row-detail").forEach((el) => el.remove());
        document.querySelectorAll(".erp-row-expanded").forEach((el) => el.classList.remove("erp-row-expanded"));

        const detailRow = document.createElement("tr");
        detailRow.className = "erp-row-detail";
        const detailCell = document.createElement("td");
        detailCell.colSpan = headers.length;
        detailCell.innerHTML = '<div class="erp-row-detail-content text-center text-muted py-3">Đang tải...</div>';
        detailRow.appendChild(detailCell);
        row.after(detailRow);
        row.classList.add("erp-row-expanded");

        const firstCell = row.children[0];
        let recordId = "";
        if (firstCell) {
          const link = firstCell.querySelector("a[href]");
          if (link) {
            const m = link.getAttribute("href").match(/\/(\d+)(?:\/|$)/);
            recordId = m ? m[1] : "";
          }
          if (!recordId) {
            recordId = firstCell.textContent.trim();
          }
        }
        if (!recordId) return;

        fetch(`${expandUrl}?id=${encodeURIComponent(recordId)}`, {
          headers: { "X-Requested-With": "XMLHttpRequest" },
        })
          .then((res) => {
            if (!res.ok) throw new Error("HTTP " + res.status);
            return res.text();
          })
          .then((html) => {
            detailCell.innerHTML = html || '<div class="text-center text-muted py-3">Không có dữ liệu chi tiết</div>';
          })
          .catch(() => {
            detailCell.innerHTML = '<div class="text-center text-danger py-3">Không tải được chi tiết</div>';
          });
      });
    }

    sizeSelect.value = originalRows.length > 20 ? "20" : "all";
    apply();
  }

  function init() {
    document.querySelectorAll("table.table-erp.table-hover").forEach(enhanceTable);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
