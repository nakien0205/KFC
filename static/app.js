/**
 * KFC Kiosk Interactive App
 * Handles: menu rendering, cart state, API recommendation integration, category filtering
 */

(function () {
  'use strict';

  // ── State ──
  const cart = []; // [{name, price, quantity}]
  let menuItems = []; // [{name, category, price}]
  let activeCategory = null; // null = show all
  let recommendDebounceTimer = null;
  const DEBOUNCE_MS = 300;

  // ── DOM refs ──
  const menuContainer = document.getElementById('menu-items-container');
  const cartList = document.getElementById('cart-items-list');
  const cartSubtotal = document.getElementById('cart-subtotal');
  const cartTotal = document.getElementById('cart-total');
  const checkoutBtn = document.getElementById('checkout-btn-action');
  const recPanel = document.getElementById('recommendation-bento-panel');
  const categoryNav = document.querySelector('.category-nav');

  // ── Helpers ──

  function formatVND(price) {
    try {
      const val = Math.round(Number(price));
      return val.toLocaleString('vi-VN').replace(/,/g, '.') + 'đ';
    } catch {
      return price + 'đ';
    }
  }

  function getCartItemNames() {
    return Array.from(new Set(cart.map(function (c) { return c.name; })));
  }

  function cartTotal_() {
    return cart.reduce(function (sum, c) { return sum + c.price * c.quantity; }, 0);
  }

  // ── Menu Rendering ──

  function createMenuCard(item) {
    var card = document.createElement('div');
    card.className = 'double-bezel menu-card card-enter';
    card.setAttribute('data-category', item.category);

    var emoji = '🍗';
    var cat = (item.category || '').toLowerCase();
    if (cat === 'burgers') emoji = '🍔';
    else if (cat === 'sides') emoji = '🍟';
    else if (cat === 'desserts') emoji = '🍦';
    else if (cat === 'drinks') emoji = '🥤';

    card.innerHTML =
      '<div class="card-inner">' +
        '<div class="card-image-placeholder">' + emoji + '</div>' +
        '<h3 class="card-item-title">' + escapeHTML(item.name) + '</h3>' +
        '<div class="card-footer">' +
          '<span class="price-text">' + formatVND(item.price) + '</span>' +
          '<button class="btn-pill add-to-cart-btn" data-name="' + escapeHTML(item.name) + '" data-price="' + item.price + '">' +
            'Thêm <span class="icon-circle">+</span>' +
          '</button>' +
        '</div>' +
      '</div>';

    var btn = card.querySelector('.add-to-cart-btn');
    btn.addEventListener('click', function (e) {
      e.stopPropagation();
      addToCart(item.name, item.price);
    });

    return card;
  }

  function escapeHTML(str) {
    var div = document.createElement('div');
    div.appendChild(document.createTextNode(str));
    return div.innerHTML;
  }

  function renderMenu(filter) {
    menuContainer.innerHTML = '';
    var items = filter
      ? menuItems.filter(function (m) { return m.category === filter; })
      : menuItems;

    items.forEach(function (item, i) {
      var card = createMenuCard(item);
      // Stagger entry animation
      card.style.animationDelay = (i * 40) + 'ms';
      menuContainer.appendChild(card);
    });
  }

  async function fetchMenu() {
    try {
      var res = await fetch('/api/menu');
      if (!res.ok) throw new Error('Menu fetch failed');
      menuItems = await res.json();
      renderMenu(activeCategory);
    } catch (err) {
      menuContainer.innerHTML =
        '<div class="recommendation-empty">Không thể tải thực đơn. Vui lòng thử lại.</div>';
    }
  }

  // ── Cart Management ──

  function addToCart(name, price) {
    var existing = cart.find(function (c) { return c.name === name; });
    if (existing) {
      existing.quantity++;
    } else {
      cart.push({ name: name, price: price, quantity: 1 });
    }
    renderCart();
    debounceFetchRecommendations();
  }

  function removeFromCart(name) {
    var idx = cart.findIndex(function (c) { return c.name === name; });
    if (idx === -1) return;
    if (cart[idx].quantity > 1) {
      cart[idx].quantity--;
    } else {
      cart.splice(idx, 1);
    }
    renderCart();
    debounceFetchRecommendations();
  }

  function renderCart() {
    cartList.innerHTML = '';

    if (cart.length === 0) {
      cartList.innerHTML =
        '<div class="empty-cart-message">Giỏ hàng của bạn đang trống. Chọn món ăn ưa thích để bắt đầu!</div>';
      cartSubtotal.textContent = '0đ';
      cartTotal.textContent = '0đ';
      checkoutBtn.classList.add('disabled');
      return;
    }

    cart.forEach(function (item) {
      var row = document.createElement('div');
      row.className = 'cart-item-row card-enter';

      row.innerHTML =
        '<div class="cart-item-info">' +
          '<span class="cart-item-name">' + escapeHTML(item.name) + '</span>' +
          '<span class="cart-item-qty badge">' + item.quantity + '</span>' +
        '</div>' +
        '<div class="cart-item-actions">' +
          '<span class="price-mono cart-item-price">' + formatVND(item.price * item.quantity) + '</span>' +
          '<button class="cart-remove-btn" data-name="' + escapeHTML(item.name) + '" aria-label="Xóa">×</button>' +
        '</div>';

      var removeBtn = row.querySelector('.cart-remove-btn');
      removeBtn.addEventListener('click', function () {
        removeFromCart(item.name);
      });

      cartList.appendChild(row);
    });

    var total = cartTotal_();
    cartSubtotal.textContent = formatVND(total);
    cartTotal.textContent = formatVND(total);
    checkoutBtn.classList.remove('disabled');
  }

  // ── Recommendation API Integration ──

  function debounceFetchRecommendations() {
    clearTimeout(recommendDebounceTimer);
    recommendDebounceTimer = setTimeout(fetchRecommendations, DEBOUNCE_MS);
  }

  async function fetchRecommendations() {
    var names = getCartItemNames();

    if (names.length === 0) {
      recPanel.innerHTML =
        '<div class="recommendation-empty">Thêm món vào giỏ hàng để nhận gợi ý!</div>';
      return;
    }

    // Show loading
    recPanel.innerHTML =
      '<div class="loading-indicator"><div class="loading-pulse"></div><span>Đang tải gợi ý...</span></div>';

    try {
      var res = await fetch('/api/recommend', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          cart_items: names,
          timestamp: new Date().toISOString()
        })
      });

      if (!res.ok) throw new Error('Recommendation fetch failed');
      var recs = await res.json();
      renderRecommendations(recs);
    } catch (err) {
      recPanel.innerHTML =
        '<div class="recommendation-empty">Không thể tải gợi ý. Vui lòng thử lại.</div>';
    }
  }

  function renderRecommendations(recs) {
    recPanel.innerHTML = '';

    if (!recs || recs.length === 0) {
      recPanel.innerHTML =
        '<div class="recommendation-empty">Chưa có gợi ý phù hợp.</div>';
      return;
    }

    recs.forEach(function (rec, i) {
      var tile = document.createElement('div');
      tile.style.animationDelay = (i * 60) + 'ms';

      var scorePercent = Math.round((rec.score || 0) * 100);
      var badgeText = scorePercent >= 70 ? 'BÁN CHẠY' : 'GỢI Ý';

      var emoji = '🍗';
      var itemObj = menuItems.find(function(m) { return m.name === rec.name; });
      var cat = itemObj ? (itemObj.category || '').toLowerCase() : '';
      if (cat === 'burgers') emoji = '🍔';
      else if (cat === 'sides') emoji = '🍟';
      else if (cat === 'desserts') emoji = '🍦';
      else if (cat === 'drinks') emoji = '🥤';

      if (i === 0) {
        tile.className = 'double-bezel bento-tile col-span-2 card-enter';
        tile.innerHTML =
          '<div class="card-inner tile-hero-layout">' +
            '<div class="tile-hero-main">' +
              '<div class="tile-header">' +
                '<span class="badge badge-hero">⭐ ĐỀ XUẤT LỚN</span>' +
                '<span class="price-mono">' + formatVND(rec.price) + '</span>' +
              '</div>' +
              '<h3 class="tile-item-title">' + escapeHTML(rec.name) + '</h3>' +
              '<p class="tile-copy">' + escapeHTML(rec.copy || '') + '</p>' +
            '</div>' +
            '<div class="tile-hero-aside">' +
              '<div class="tile-image-placeholder">' + emoji + '</div>' +
            '</div>' +
            '<div class="tile-footer">' +
              '<span class="tile-rationale">' + escapeHTML(rec.rationale || '') + '</span>' +
              '<button class="add-to-cart-btn-mini" data-name="' + escapeHTML(rec.name) + '" data-price="' + rec.price + '">' +
                'Thêm <span class="icon-circle">+</span>' +
              '</button>' +
            '</div>' +
          '</div>';
      } else {
        tile.className = 'double-bezel bento-tile card-enter';
        tile.innerHTML =
          '<div class="card-inner">' +
            '<div class="tile-header">' +
              '<span class="badge">' + badgeText + '</span>' +
              '<span class="price-mono">' + formatVND(rec.price) + '</span>' +
            '</div>' +
            '<h3 class="tile-item-title">' + escapeHTML(rec.name) + '</h3>' +
            '<p class="tile-copy">' + escapeHTML(rec.copy || '') + '</p>' +
            '<div class="tile-footer">' +
              '<span class="tile-rationale">' + escapeHTML(rec.rationale || '') + '</span>' +
              '<button class="add-to-cart-btn-mini" data-name="' + escapeHTML(rec.name) + '" data-price="' + rec.price + '">' +
                'Thêm <span class="icon-circle">+</span>' +
              '</button>' +
            '</div>' +
          '</div>';
      }

      var addBtn = tile.querySelector('.add-to-cart-btn-mini');
      addBtn.addEventListener('click', function (e) {
        e.stopPropagation();
        addToCart(rec.name, rec.price);
      });

      recPanel.appendChild(tile);
    });
  }

  // ── Category Filtering ──

  function setupCategoryFiltering() {
    if (!categoryNav) return;

    // Add "All" category as first item if not present
    var allLink = categoryNav.querySelector('[data-category="all"]');
    if (!allLink) {
      var first = document.createElement('a');
      first.href = '#';
      first.className = 'category-item active';
      first.setAttribute('data-category', 'all');
      first.innerHTML = '<span class="category-text">Tất cả</span>';
      categoryNav.insertBefore(first, categoryNav.firstChild);

      // Remove active from others
      categoryNav.querySelectorAll('.category-item').forEach(function (el) {
        if (el !== first) el.classList.remove('active');
      });
    }

    categoryNav.addEventListener('click', function (e) {
      var link = e.target.closest('.category-item');
      if (!link) return;
      e.preventDefault();

      categoryNav.querySelectorAll('.category-item').forEach(function (el) {
        el.classList.remove('active');
      });
      link.classList.add('active');

      var cat = link.getAttribute('data-category');
      activeCategory = (cat === 'all') ? null : cat;
      renderMenu(activeCategory);
    });
  }

  // ── Backtest Simulator ──

  const backtestModal = document.getElementById('backtest-modal');
  const runBacktestBtn = document.getElementById('run-backtest-btn');
  const closeBacktestBtn = document.getElementById('close-backtest-btn');
  const backtestResultsBody = document.getElementById('backtest-results-body');

  if (runBacktestBtn) {
    runBacktestBtn.addEventListener('click', function (e) {
      e.preventDefault();
      openBacktestModal();
    });
  }

  if (closeBacktestBtn) {
    closeBacktestBtn.addEventListener('click', function () {
      closeBacktestModal();
    });
  }

  if (backtestModal) {
    backtestModal.addEventListener('click', function (e) {
      if (e.target === backtestModal) {
        closeBacktestModal();
      }
    });
  }

  function openBacktestModal() {
    backtestModal.classList.add('active');
    triggerBacktest();
  }

  function closeBacktestModal() {
    backtestModal.classList.remove('active');
  }

  async function triggerBacktest() {
    backtestResultsBody.innerHTML =
      '<div class="loading-indicator"><div class="loading-pulse"></div><span>Đang chạy mô phỏng trên 1.000+ đơn hàng...</span></div>';

    try {
      var res = await fetch('/api/backtest', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });

      if (!res.ok) throw new Error('Backtest failed');
      var results = await res.json();
      renderBacktestResults(results);
    } catch (err) {
      backtestResultsBody.innerHTML =
        '<div class="recommendation-empty">Không thể chạy thử nghiệm. Vui lòng kiểm tra lại backend.</div>';
    }
  }

  function renderBacktestResults(results) {
    var baselineAovStr = formatVND(results.baseline_aov);
    var hybridAovStr = formatVND(results.hybrid_aov);
    var upliftStr = '+' + formatVND(results.absolute_change);
    var percentageUpliftStr = '+' + results.percentage_uplift.toFixed(2) + '%';

    backtestResultsBody.innerHTML =
      '<div class="backtest-grid">' +
        '<div class="backtest-uplift-banner">' +
          '<span class="backtest-uplift-label">Doanh thu trung bình tăng trưởng (AOV Uplift)</span>' +
          '<span class="backtest-uplift-value">' + percentageUpliftStr + '</span>' +
        '</div>' +
        '<div class="backtest-metric-card">' +
          '<span class="backtest-metric-label">Baseline AOV (Pepsi)</span>' +
          '<span class="backtest-metric-value">' + baselineAovStr + '</span>' +
        '</div>' +
        '<div class="backtest-metric-card">' +
          '<span class="backtest-metric-label">Hybrid Recommender AOV</span>' +
          '<span class="backtest-metric-value highlight">' + hybridAovStr + '</span>' +
        '</div>' +
        '<div class="backtest-metric-card" style="grid-column: span 2; text-align: center;">' +
          '<span class="backtest-metric-label">Giá trị tăng thêm trên mỗi đơn hàng</span>' +
          '<span class="backtest-metric-value" style="color: #2e7d32;">' + upliftStr + '</span>' +
        '</div>' +
      '</div>';
  }

  // ── Init ──

  document.addEventListener('DOMContentLoaded', function () {
    setupCategoryFiltering();
    fetchMenu();
    renderCart();
  });
})();
