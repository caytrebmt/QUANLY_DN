/**
 * shop.js — OfficePro Frontend Engine
 * Vanilla JS, zero dependencies
 * Connects to Flask routes in shop.py
 */
'use strict';

/* ════════════════════════════════════════════════
   TOAST NOTIFICATIONS
════════════════════════════════════════════════ */
function showToast(msg, type = 'success', duration = 3200) {
  let container = document.getElementById('_toastContainer');
  if (!container) {
    container = document.createElement('div');
    container.id = '_toastContainer';
    container.style.cssText = 'position:fixed;bottom:22px;right:22px;z-index:9999;display:flex;flex-direction:column;gap:8px;pointer-events:none';
    document.body.appendChild(container);
  }

  const icons = {
    success: '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>',
    error:   '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>',
    info:    '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>',
  };
  const colors = { success: 'var(--green)', error: 'var(--red)', info: 'var(--blue,#2563eb)' };

  const toast = document.createElement('div');
  toast.style.cssText = `
    display:flex;align-items:center;gap:10px;
    background:var(--white,#fff);border:1px solid var(--line,#e4ddd3);
    border-radius:10px;padding:12px 16px;
    box-shadow:0 4px 24px rgba(26,22,18,.14);
    font-family:var(--font-sans,'DM Sans',sans-serif);font-size:13.5px;color:var(--ink,#1a1612);
    pointer-events:all;min-width:260px;max-width:360px;
    animation:_toastIn .22s cubic-bezier(.4,0,.2,1);
    border-left:3px solid ${colors[type] || colors.success};
  `;
  toast.innerHTML = `
    <span style="color:${colors[type]};flex-shrink:0">${icons[type] || icons.info}</span>
    <span style="flex:1;line-height:1.45">${msg}</span>
    <span style="cursor:pointer;color:var(--ink-4,#8a7f74);font-size:17px;line-height:1;flex-shrink:0" onclick="this.closest('[style]').remove()">×</span>
  `;

  if (!document.getElementById('_toastStyle')) {
    const s = document.createElement('style');
    s.id = '_toastStyle';
    s.textContent = `@keyframes _toastIn{from{transform:translateX(18px);opacity:0}to{transform:translateX(0);opacity:1}}@keyframes _toastOut{from{opacity:1;max-height:60px}to{opacity:0;max-height:0}}@keyframes spin{to{transform:rotate(360deg)}}`;
    document.head.appendChild(s);
  }

  container.appendChild(toast);
  setTimeout(() => {
    toast.style.animation = '_toastOut .25s ease forwards';
    toast.addEventListener('animationend', () => toast.remove(), { once: true });
  }, duration);
}


/* ════════════════════════════════════════════════
   CART BADGE
════════════════════════════════════════════════ */
function updateCartBadge(qty) {
  const badge = document.querySelector('.topnav__cart-badge');
  if (!badge) {
    // Create badge dynamically if not in DOM (empty cart state)
    const cartBtn = document.querySelector('a[href*="/cart"] .topnav__btn, a[href$="/cart"]');
    if (cartBtn && qty > 0) {
      const b = document.createElement('span');
      b.className = 'topnav__cart-badge';
      b.textContent = qty;
      cartBtn.style.position = 'relative';
      cartBtn.appendChild(b);
    }
    return;
  }
  if (qty > 0) {
    badge.textContent = qty;
    badge.style.display = 'flex';
    // Pulse animation
    badge.style.transform = 'scale(1.4)';
    setTimeout(() => badge.style.transform = '', 200);
  } else {
    badge.style.display = 'none';
  }
}


/* ════════════════════════════════════════════════
   ADD TO CART — AJAX
   POST /cart/add/<listing_id>
   Response: { ok, message, cart_qty, cart_url }
════════════════════════════════════════════════ */
function addToCart(event, listingId, productName) {
  if (event) event.stopPropagation();

  const btn = event?.currentTarget;
  const originalHtml = btn?.innerHTML;
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="animation:spin .8s linear infinite"><path d="M21 12a9 9 0 1 1-18 0"/></svg>';
  }

  fetch(`/cart/add/${listingId}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Requested-With': 'XMLHttpRequest',
    },
    body: JSON.stringify({ quantity: 1 }),
  })
  .then(r => r.json())
  .then(data => {
    if (data.ok) {
      showToast(`<strong>${(productName || 'Sản phẩm').substring(0, 40)}</strong> đã thêm vào giỏ hàng`);
      updateCartBadge(data.cart_qty);
    } else {
      showToast(data.message || 'Không thể thêm vào giỏ', 'error');
    }
  })
  .catch(() => showToast('Lỗi kết nối. Vui lòng thử lại.', 'error'))
  .finally(() => {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = originalHtml;
    }
  });
}


/* ════════════════════════════════════════════════
   LIVE SEARCH — catalog page
   Debounced form submit on /  with ?search=
════════════════════════════════════════════════ */
(function initLiveSearch() {
  const input  = document.getElementById('globalSearch');
  const form   = input?.closest('form');
  if (!input || !form) return;

  let timer;
  const DEBOUNCE_MS = 320;

  input.addEventListener('input', () => {
    clearTimeout(timer);
    timer = setTimeout(() => {
      // Only auto-submit on catalog page (action points to /)
      if (window.location.pathname === '/' || window.location.pathname === '/catalog') {
        form.submit();
      }
    }, DEBOUNCE_MS);
  });

  // Keyboard shortcut '/' → focus search
  document.addEventListener('keydown', e => {
    if (e.key === '/' && document.activeElement.tagName !== 'INPUT' && document.activeElement.tagName !== 'TEXTAREA') {
      e.preventDefault();
      input.focus();
      input.select();
    }
    if (e.key === 'Escape' && document.activeElement === input) {
      input.blur();
    }
  });
})();


/* ════════════════════════════════════════════════
   FLASH MESSAGE AUTO-DISMISS
════════════════════════════════════════════════ */
(function initFlashDismiss() {
  const DISMISS_AFTER = 5000;
  document.querySelectorAll('.flash-message').forEach(el => {
    setTimeout(() => {
      el.style.transition = 'opacity .3s, max-height .3s, padding .3s, margin .3s';
      el.style.opacity = '0';
      el.style.maxHeight = '0';
      el.style.padding = '0';
      el.style.margin = '0';
      el.style.overflow = 'hidden';
      setTimeout(() => el.remove(), 350);
    }, DISMISS_AFTER);
  });
})();


/* ════════════════════════════════════════════════
   PRODUCT CARD — hover quick-add scroll
════════════════════════════════════════════════ */
(function initCardHoverFix() {
  // Prevent quick-add button from triggering the card link
  document.querySelectorAll('.product-card__quick-add').forEach(btn => {
    btn.addEventListener('click', e => e.stopPropagation());
  });
})();


/* ════════════════════════════════════════════════
   PROMO CODE — inline feedback
   Submits checkout form for server-side validation
════════════════════════════════════════════════ */
(function initPromoInput() {
  const input = document.querySelector('input[name="promotion_code"]');
  if (!input) return;

  input.addEventListener('keydown', e => {
    if (e.key === 'Enter') {
      e.preventDefault();
      document.querySelector('.promo-field button')?.click();
    }
  });
  // Uppercase input
  input.addEventListener('input', () => {
    const pos = input.selectionStart;
    input.value = input.value.toUpperCase();
    input.setSelectionRange(pos, pos);
  });
})();


/* ════════════════════════════════════════════════
   VIEW MODE PERSISTENCE
════════════════════════════════════════════════ */
(function initViewPersist() {
  const savedView = localStorage.getItem('shopView');
  if (savedView === 'list') {
    const grid    = document.getElementById('productGrid');
    const gridBtn = document.getElementById('gridViewBtn');
    const listBtn = document.getElementById('listViewBtn');
    if (grid && gridBtn && listBtn) {
      grid.classList.add('list');
      listBtn.classList.add('active');
      gridBtn.classList.remove('active');
    }
  }
})();


/* ════════════════════════════════════════════════
   FORM VALIDATION HELPERS
════════════════════════════════════════════════ */
(function initFormValidation() {
  // Phone number format for VN
  document.querySelectorAll('input[type="tel"]').forEach(input => {
    input.addEventListener('blur', () => {
      const val = input.value.replace(/\s+/g, '');
      if (val && !/^(0[3-9]\d{8}|\+84[3-9]\d{8})$/.test(val)) {
        input.style.borderColor = 'var(--red)';
      } else {
        input.style.borderColor = '';
      }
    });
  });

  // Submit button loading state
  document.querySelectorAll('form:not(#cartForm)').forEach(form => {
    form.addEventListener('submit', () => {
      const submit = form.querySelector('button[type="submit"]');
      if (submit && !submit.dataset.noLoad) {
        setTimeout(() => {
          submit.disabled = true;
          const original = submit.innerHTML;
          submit.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="animation:spin .8s linear infinite"><path d="M21 12a9 9 0 1 1-18 0"/></svg> Đang xử lý...';
          // Restore after 8s as fallback
          setTimeout(() => {
            submit.disabled = false;
            submit.innerHTML = original;
          }, 8000);
        }, 50);
      }
    });
  });
})();


/* ════════════════════════════════════════════════
   CART QUANTITY — inline update (cart.html)
════════════════════════════════════════════════ */
window.adjustQty = function(fieldId, delta) {
  const input = document.getElementById(fieldId);
  if (!input) return;
  const newVal = Math.max(0, parseInt(input.value || 1) + delta);
  if (newVal === 0) {
    if (confirm('Xóa sản phẩm này khỏi giỏ hàng?')) {
      input.value = 0;
      document.getElementById('cartForm')?.submit();
    }
  } else {
    input.value = newVal;
    document.getElementById('cartForm')?.submit();
  }
};


/* ════════════════════════════════════════════════
   PRODUCT DETAIL — qty control
════════════════════════════════════════════════ */
window.changeQty = function(delta) {
  const display = document.getElementById('pdQty');
  if (!display) return;
  window._pdQty = Math.max(1, (window._pdQty || 1) + delta);
  display.textContent = window._pdQty;
};

window.addToCartDetail = function(listingId, name) {
  const btn = document.getElementById('pdAddBtn');
  const qty = window._pdQty || 1;
  const orig = btn?.innerHTML;
  if (btn) { btn.disabled = true; btn.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="animation:spin .8s linear infinite"><path d="M21 12a9 9 0 1 1-18 0"/></svg> Đang thêm...'; }

  fetch(`/cart/add/${listingId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
    body: JSON.stringify({ quantity: qty }),
  })
  .then(r => r.json())
  .then(data => {
    if (data.ok) {
      showToast(`Đã thêm <strong>${qty > 1 ? qty + '× ' : ''}${name.substring(0,40)}</strong> vào giỏ hàng`);
      updateCartBadge(data.cart_qty);
    } else {
      showToast(data.message || 'Không thể thêm', 'error');
    }
  })
  .catch(() => showToast('Lỗi kết nối', 'error'))
  .finally(() => { if (btn) { btn.disabled = false; btn.innerHTML = orig; } });
};


/* ════════════════════════════════════════════════
   ORDER ACTIONS — order_history, order_detail
════════════════════════════════════════════════ */
window.reorder = async function(orderId, btn) {
  const orig = btn.innerHTML;
  btn.disabled = true;
  btn.innerHTML = '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="animation:spin .8s linear infinite"><path d="M21 12a9 9 0 1 1-18 0"/></svg> Đang thêm...';
  try {
    const res  = await fetch(`/orders/${orderId}/reorder`, { method: 'POST', headers: { 'X-Requested-With': 'XMLHttpRequest' } });
    const data = await res.json();
    if (data.ok) {
      showToast(`Đã thêm <strong>${data.added}</strong> sản phẩm vào giỏ hàng`);
      updateCartBadge(data.cart_qty);
      btn.innerHTML = '✓ Đã thêm';
    } else {
      showToast(data.message || 'Lỗi xử lý', 'error');
      btn.disabled = false; btn.innerHTML = orig;
    }
  } catch {
    showToast('Lỗi kết nối', 'error');
    btn.disabled = false; btn.innerHTML = orig;
  }
};

window.cancelOrder = async function(orderId, btn) {
  if (!confirm('Bạn có chắc muốn hủy đơn hàng này không?')) return;
  const orig = btn.innerHTML;
  btn.disabled = true;
  btn.innerHTML = 'Đang hủy...';
  try {
    const res  = await fetch(`/orders/${orderId}/cancel`, { method: 'POST', headers: { 'X-Requested-With': 'XMLHttpRequest' } });
    const data = await res.json();
    if (data.ok) {
      showToast('Đã hủy đơn hàng thành công');
      setTimeout(() => location.reload(), 1200);
    } else {
      showToast(data.message || 'Không thể hủy', 'error');
      btn.disabled = false; btn.innerHTML = orig;
    }
  } catch {
    showToast('Lỗi kết nối', 'error');
    btn.disabled = false; btn.innerHTML = orig;
  }
};


/* ════════════════════════════════════════════════
   IMAGE LAZY LOAD — polyfill for older browsers
════════════════════════════════════════════════ */
(function initLazyImages() {
  if ('loading' in HTMLImageElement.prototype) return; // native support
  const imgs = document.querySelectorAll('img[loading="lazy"]');
  if (!('IntersectionObserver' in window)) {
    imgs.forEach(img => { img.src = img.dataset.src || img.src; });
    return;
  }
  const observer = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const img = entry.target;
        if (img.dataset.src) img.src = img.dataset.src;
        observer.unobserve(img);
      }
    });
  });
  imgs.forEach(img => observer.observe(img));
})();