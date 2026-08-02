window.ERPPrint = {
  modalInstance: null,

  openPreview: function (html) {
    var modalEl = document.getElementById("voucherPrintModal");
    var body = document.getElementById("print-modal-body");
    if (!modalEl || !body) return;
    body.innerHTML = html;
    if (!this.modalInstance) {
      this.modalInstance = new bootstrap.Modal(modalEl);
    }
    this.modalInstance.show();
  },

  closePreview: function () {
    if (this.modalInstance) {
      this.modalInstance.hide();
    }
  },

  print: function () {
    var printArea = document.getElementById("print-area");
    var modalBody = document.getElementById("print-modal-body");
    if (!printArea || !modalBody) return;
    printArea.innerHTML = modalBody.innerHTML;
    this.closePreview();
    window.print();
  },
};

document.addEventListener("DOMContentLoaded", function () {
  var btn = document.getElementById("btnPrintFromModal");
  if (btn) {
    btn.addEventListener("click", function () {
      window.ERPPrint.print();
    });
  }

  document.body.addEventListener("click", function (e) {
    var trigger = e.target.closest(".btn-erp-print");
    if (!trigger) return;
    var url = trigger.getAttribute("data-print-url");
    if (!url) return;
    e.preventDefault();
    var modalBody = document.getElementById("print-modal-body");
    var modal = document.getElementById("voucherPrintModal");
    if (!modalBody || !modal) return;
    modalBody.innerHTML = '<p class="text-center text-muted">Đang tải nội dung...</p>';
    window.ERPPrint.openPreview(modalBody.innerHTML);
    fetch(url, { headers: { "X-CSRFToken": document.querySelector('meta[name="csrf-token"]')?.content || "" } })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data.ok && data.html) {
          modalBody.innerHTML = data.html;
        } else {
          modalBody.innerHTML = '<p class="text-center text-danger">Không thể tải nội dung phiếu in.</p>';
        }
      })
      .catch(function () {
        modalBody.innerHTML = '<p class="text-center text-danger">Lỗi kết nối máy chủ.</p>';
      });
  });
});
