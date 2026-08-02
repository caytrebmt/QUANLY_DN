$(function () {
  const unitConvMap = window.unitConvMap || {};
  const fmt = (v) => new Intl.NumberFormat("vi-VN").format(Math.round(v || 0));

  function updateUnitOptions($row, productId, baseUnitName) {
    const $unitSel = $row.find(".unit-sel");
    const currentVal = $unitSel.val();
    $unitSel.find('option[value=""]').text(`${baseUnitName || "-- ĐVT --"} (Gốc)`);
    $unitSel.find("option").attr("data-factor", 1);
    Object.entries(unitConvMap[String(productId)] || {}).forEach(([unitId, factor]) => {
      $unitSel.find(`option[value="${unitId}"]`).attr("data-factor", factor);
    });
    $unitSel.val(currentVal);
  }

  function calcRow(row) {
    const $row = $(row);
    const qty = parseFloat($row.find(".qty-input").val()) || 0;
    const price = parseFloat($row.find(".price-input").val()) || 0;
    const vatRate = parseFloat($row.find(".vat-sel").val()) || 0;
    const amount = qty * price;
    const mode = $('input[name="vat_mode"]:checked').val();
    const vatAmount = mode === "per_item" ? (amount * vatRate) / 100 : 0;
    const total = amount + vatAmount;
    $row.find(".amount-txt").val(fmt(amount));
    $row.find(".vat-txt").val(fmt(vatAmount));
    $row.find(".total-txt").val(fmt(total));
    return { amount, rate: vatRate };
  }

  function calcTotals() {
    let subtotal = 0;
    const lines = [];
    const mode = $('input[name="vat_mode"]:checked').val();
    $("#itemsBody .item-row").each(function () {
      const row = calcRow(this);
      subtotal += row.amount;
      lines.push(row);
    });

    const discount = Math.min(Math.max(parseFloat($("#discountInput").val()) || 0, 0), subtotal);
    const taxable = Math.max(subtotal - discount, 0);
    let vat = 0;
    if (mode === "grouped") {
      $(".vat-auto-col").hide();
      $("#vatGroupedSection").show();
      const rate = parseFloat($("#vatRateGrouped").val()) || 0;
      vat = (taxable * rate) / 100;
    } else {
      $(".vat-auto-col").show();
      $("#vatGroupedSection").hide();
      vat = lines.reduce((sum, line) => {
        const lineDiscount = subtotal > 0 ? (discount * line.amount) / subtotal : 0;
        return sum + (Math.max(line.amount - lineDiscount, 0) * line.rate) / 100;
      }, 0);
    }

    $("#sumSubtotal").text(fmt(subtotal) + " VND");
    $("#sumVat").text(fmt(vat) + " VND");
    $("#sumTotal").text(fmt(taxable + vat) + " VND");
  }

  function bindRow(row) {
    const $row = $(row);
    $row.find(".product-sel").select2({ theme: "bootstrap-5", width: "100%" });
    $row.find(".product-sel").on("change", function () {
      const $opt = $(this).find("option:selected");
      const baseUnitName = $opt.data("unit") || "";
      $row.find(".unit-txt").val(baseUnitName);
      $row.find(".price-input").val($opt.data("price") || 0);
      $row.find(".vat-sel").val($opt.data("vat") || 0);
      $row.find(".factor-input").val(1);
      updateUnitOptions($row, $opt.val(), baseUnitName);
      calcTotals();
    });
    $row.find(".unit-sel").on("change", function () {
      const factor = $(this).find("option:selected").data("factor") || 1;
      $row.find(".factor-input").val(factor);
      calcTotals();
    });
    $row.find(".qty-input, .price-input, .vat-sel").on("input change", calcTotals);
    $row.find(".remove-row").on("click", function () {
      $row.remove();
      renumber();
      calcTotals();
      if ($("#itemsBody .item-row").length === 0) $("#addRowBtn").click();
    });
  }

  function renumber() {
    $("#itemsBody .item-row").each((i, el) => $(el).find(".row-num").text(i + 1));
  }

  $("#customerSel").select2({
    theme: "bootstrap-5",
    placeholder: "-- Báo giá chung / người nhận tự do --",
    allowClear: true,
    width: "100%",
  });
  $("#customerSel").on("change", function () {
    const opt = $(this).find("option:selected");
    if (!opt.val()) return;
    if (!$("#recipientName").val()) $("#recipientName").val(opt.data("name") || "");
    if (!$("#recipientAddress").val()) $("#recipientAddress").val(opt.data("address") || "");
    if (!$("#recipientPhone").val()) $("#recipientPhone").val(opt.data("phone") || "");
    if (!$("#recipientEmail").val()) $("#recipientEmail").val(opt.data("email") || "");
  });

  $("#addRowBtn").on("click", function () {
    const clone = document.getElementById("rowTpl").content.cloneNode(true).querySelector("tr");
    $("#itemsBody").append(clone);
    bindRow($("#itemsBody .item-row:last")[0]);
    renumber();
    calcTotals();
  });

  $(".vat-mode-radio, #discountInput, #vatRateGrouped").on("input change", calcTotals);

  $("#itemsBody .item-row").each(function () {
    bindRow(this);
    const $pSel = $(this).find(".product-sel");
    if ($pSel.val()) updateUnitOptions($(this), $pSel.val(), $pSel.find("option:selected").data("unit"));
  });
  if ($("#itemsBody .item-row").length === 0) $("#addRowBtn").click();
  calcTotals();
});
