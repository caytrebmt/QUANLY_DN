$(function () {
  const unitConvMap = window.unitConvMap || {};
  const fmt = (v) => new Intl.NumberFormat("vi-VN").format(Math.round(v || 0));
  const CARTON_KEYWORDS = ["thung", "carton", "case", "box"];

  // --- Core Logic ---

  function fetchStock(productId, stockEl) {
    const wid = $("#warehouseSel").val();
    if (!productId || !wid) {
      stockEl.val("-").removeClass("text-danger text-success fw-bold");
      return;
    }
    fetch(`/api/products/${productId}/stock?warehouse_id=${wid}`)
      .then((r) => r.json())
      .then((d) => {
        const inv = d.stock.find((s) => s.warehouse_id == parseInt(wid));
        const qty = inv ? inv.quantity : 0;
        stockEl.val(new Intl.NumberFormat("vi-VN").format(qty));

        stockEl.removeClass("text-danger text-success fw-bold");
        if (qty <= 0) stockEl.addClass("text-danger fw-bold");
        else stockEl.addClass("text-success");
      })
      .catch(() => stockEl.val("-"));
  }

  function updateUnitOptions($row, productId, baseUnitName) {
    const $unitSel = $row.find(".unit-sel");
    const currentVal = $unitSel.val();

    $unitSel
      .find('option[value=""]')
      .text(`${baseUnitName || "-- ĐVT --"} (Gốc)`);
    $unitSel.find("option").attr("data-factor", 1);
    // Lọc các đơn vị quy đổi theo product_id.
    const convByProduct = unitConvMap[String(productId)] || {};
    Object.entries(convByProduct).forEach(([unitId, factor]) => {
      $unitSel.find(`option[value="${unitId}"]`).attr("data-factor", factor);
    });
    if (!$unitSel.val()) {
      $unitSel.val("");
    }
    $unitSel.val(currentVal);
  }

  function isCartonUnitText(text) {
    const raw = String(text || "");
    const normalized = raw
      .toLowerCase()
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .replace(/đ/g, "d");
    return CARTON_KEYWORDS.some((k) => normalized.includes(k));
  }

  function toNiceQty(n) {
    const num = Number(n || 0);
    if (!Number.isFinite(num) || num <= 0) return "";
    if (Math.abs(num - Math.round(num)) < 1e-9) return String(Math.round(num));
    return String(Number(num.toFixed(3)));
  }

  function suggestBoxCount($row) {
    const $boxInput = $row.find(".box-note-input");
    if ($boxInput.length === 0) return;
    if ($boxInput.attr("data-manual") === "1") return;

    const qty = parseFloat($row.find(".qty-input").val()) || 0;
    const selectedFactor = parseFloat($row.find(".factor-input").val()) || 1;
    const baseQty = qty * selectedFactor;
    if (baseQty <= 0) {
      if ($boxInput.attr("data-auto") === "1") $boxInput.val("");
      $boxInput.attr("placeholder", "VD: 1 thùng");
      return;
    }

    const $unitSel = $row.find(".unit-sel");
    const unitText = $unitSel.find("option:selected").text() || "";
    let suggested = null;
    if (isCartonUnitText(unitText)) {
      suggested = qty;
    } else {
      $unitSel.find("option").each(function () {
        const text = $(this).text() || "";
        const factor = parseFloat($(this).attr("data-factor")) || 0;
        if (factor > 0 && isCartonUnitText(text)) {
          suggested = baseQty / factor;
          return false;
        }
      });
    }

    const nice = toNiceQty(suggested);
    if (!nice) {
      if ($boxInput.attr("data-auto") === "1") $boxInput.val("");
      $boxInput.attr("placeholder", "VD: 1 thùng");
      return;
    }

    $boxInput.attr("placeholder", `Gợi ý: ${nice} thùng`);
    if (!$boxInput.val() || $boxInput.attr("data-auto") === "1") {
      $boxInput.val(nice);
      $boxInput.attr("data-auto", "1");
    }
  }

  function calcRow(row) {
    const $row = $(row);
    const qty = parseFloat($row.find(".qty-input").val()) || 0;
    const factor = parseFloat($row.find(".factor-input").val()) || 1;
    const price = parseFloat($row.find(".price-input").val()) || 0;
    const vatRate = parseFloat($row.find(".vat-sel").val()) || 0;

    // Thành tiền = Số lượng * Đơn giá
    const amt = qty * price;

    // VAT từng dòng chỉ tính nếu đang ở chế độ per_item
    const mode = $('input[name="vat_mode"]:checked').val();
    const vatAmt = mode === "per_item" ? (amt * vatRate) / 100 : 0;

    const total = amt + vatAmt;

    $row.find(".amount-txt").val(fmt(amt));
    $row.find(".vat-txt").val(fmt(vatAmt));
    $row.find(".total-txt").val(fmt(total));

    return { amt, vatAmt };
  }

  function calcTotals() {
    let subtotal = 0;
    const lines = [];
    const mode = $('input[name="vat_mode"]:checked').val();
    const isManualVat = $("#vatManualChk").is(":checked");

    $("#itemsBody .item-row").each(function () {
      const r = calcRow(this);
      subtotal += r.amt;
      lines.push({
        amount: r.amt,
        rate: parseFloat($(this).find(".vat-sel").val()) || 0,
      });
    });

    const discount = Math.min(Math.max(parseFloat($("#discountInput").val()) || 0, 0), subtotal);
    const taxable = Math.max(subtotal - discount, 0);
    let finalVat = 0;

    // Xử lý UI theo Mode
    if (mode === "grouped") {
      $("#vatGroupedSection").show();
      $("#vatManualCheckDiv").hide();
      $("#groupedVatRow").show();
      $("#vatAutoRow, #vatManualRow").hide();
      $(".vat-auto-col").hide(); // Ẩn cột VAT trên lưới

      const rate = parseFloat($("#vatRateGrouped").val()) || 0;
      finalVat = (taxable * rate) / 100;
      $("#groupedVatAmount").text(fmt(finalVat) + " VND");
    } else {
      $("#vatGroupedSection").hide();
      $("#vatManualCheckDiv").show();
      $("#groupedVatRow").hide();
      $(".vat-sel, .vat-txt").parent().show();

      if (isManualVat) {
        $("#vatManualRow").show();
        $("#vatAutoRow").hide();
        finalVat = parseFloat($("#vatManualInput").val()) || 0;
      } else {
        $("#vatManualRow").hide();
        $("#vatAutoRow").show();
        finalVat = lines.reduce((sum, line) => {
          const lineDiscount = subtotal > 0 ? (discount * line.amount) / subtotal : 0;
          const lineTaxable = Math.max(line.amount - lineDiscount, 0);
          return sum + (lineTaxable * line.rate) / 100;
        }, 0);
      }
    }

    const grandTotal = taxable + finalVat;

    $("#sumSubtotal").text(fmt(subtotal) + " VND");
    $("#sumVatAuto").text(fmt(finalVat) + " VND");
    $("#sumTotal").text(fmt(grandTotal) + " VND");
  }

  function updateVatUI() {
  const mode = $('input[name="vat_mode"]:checked').val();

  if (mode === "grouped") {
    $(".vat-auto-col").hide();

    $("#vatGroupedSection").show();
    $("#groupedVatRow").show();

    $("#vatAutoRow, #vatManualRow").hide();
    $("#vatManualCheckDiv").hide();
  } else {
    $(".vat-auto-col").show();

    $("#vatGroupedSection").hide();
    $("#groupedVatRow").hide();

    $("#vatManualCheckDiv").show();

    if ($("#vatManualChk").is(":checked")) {
      $("#vatManualRow").show();
      $("#vatAutoRow").hide();
    } else {
      $("#vatManualRow").hide();
      $("#vatAutoRow").show();
    }
  }
}
  // --- Event Handlers ---

  function bindRow(row) {
    const $row = $(row);
    $row.find(".product-sel").select2({ theme: "select2", width: "100%" });

    $row.find(".product-sel").on("change", function () {
      const $opt = $(this).find("option:selected");
      const baseUnitId = $opt.data("base-unit-id");
      const baseUnitName = $opt.data("unit");

      $row.find(".unit-txt").val(baseUnitName || "");
      $row.find(".price-input").val($opt.data("price") || 0);
      $row.find(".vat-sel").val($opt.data("vat") || 0);
      $row.find(".factor-input").val(1);

      updateUnitOptions($row, $opt.val(), baseUnitName);
      fetchStock($opt.val(), $row.find(".stock-txt"));
      suggestBoxCount($row);
      calcTotals();
    });

    $row.find(".unit-sel").on("change", function () {
      const $opt = $(this).find("option:selected");
      const factor = $opt.data("factor") || 1;
      $row.find(".factor-input").val(factor);
      suggestBoxCount($row);
      calcTotals();
    });

    $row
      .find(".qty-input, .price-input, .vat-sel")
      .on("input change", function () {
        suggestBoxCount($row);
        calcTotals();
      });

    $row.find(".box-note-input").on("input", function () {
      const v = $(this).val().trim();
      if (v) {
        $(this).attr("data-manual", "1").attr("data-auto", "0");
      } else {
        $(this).attr("data-manual", "0").attr("data-auto", "0");
        suggestBoxCount($row);
      }
    });

    if (($row.find(".box-note-input").val() || "").trim()) {
      $row.find(".box-note-input").attr("data-manual", "1");
    }

    $row.find(".remove-row").on("click", function () {
      $row.remove();
      renumber();
      calcTotals();
      if ($("#itemsBody .item-row").length === 0) {
        $("#addRowBtn").click();
      }
    });
  }

  function renumber() {
    $("#itemsBody .item-row").each((i, el) => {
      $(el)
        .find(".row-num")
        .text(i + 1);
    });
  }

  // --- Initialization ---

  $("#addRowBtn").on("click", function () {
    const tpl = document.getElementById("rowTpl");
    const clone = tpl.content.cloneNode(true).querySelector("tr");
    $("#itemsBody").append(clone);
    bindRow($("#itemsBody .item-row:last")[0]);
    renumber();
    updateVatUI();
  });

  $(".vat-mode-radio").on("change", function () {
  updateVatUI();
  calcTotals();
});
  $("#vatManualChk").on("change", calcTotals);
  $("#warehouseSel").on("change", () => {
    $("#itemsBody .item-row").each(function () {
      const pid = $(this).find(".product-sel").val();
      fetchStock(pid, $(this).find(".stock-txt"));
    });
  });

  $("#discountInput, #vatManualInput, #vatRateGrouped").on(
    "input change",
    calcTotals,
  );

  // Khởi tạo các dòng có sẵn (khi Edit)
  $("#itemsBody .item-row").each(function () {
    bindRow(this);
    const $pSel = $(this).find(".product-sel");
    if ($pSel.val()) {
      updateUnitOptions(
        $(this),
        $pSel.val(),
        $pSel.find("option:selected").data("unit"),
      );
    }
    suggestBoxCount($(this));
  });

  if ($("#itemsBody .item-row").length === 0) $("#addRowBtn").click();

  updateVatUI();
  calcTotals();
});
