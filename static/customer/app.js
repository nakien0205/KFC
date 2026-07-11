(function () {
  'use strict';

  var menu = [];
  var cart = [];
  var category = 'All';
  var timer;
  var recommendationVersion = 0;
  var activeOfferId = null;
  var activeOfferTarget = null;
  var grid = document.getElementById('menu-grid');
  var tabs = document.getElementById('category-tabs');
  var cartList = document.getElementById('cart-list');
  var total = document.getElementById('cart-total');
  var checkout = document.getElementById('checkout-button');
  var status = document.getElementById('checkout-status');
  var recommendationStatus = document.getElementById('recommendation-status');
  var recommendations = document.getElementById('recommendations');

  function money(value) {
    return Math.round(Number(value) || 0).toLocaleString('en-US').replace(/,/g, '.') + ' VND';
  }

  function escapeText(value) {
    var node = document.createElement('span');
    node.textContent = value;
    return node.innerHTML;
  }

  function names() {
    return cart.map(function (item) { return item.name; });
  }

  function renderTabs() {
    var categories = ['All'].concat(Array.from(new Set(menu.map(function (item) { return item.category; }))));
    tabs.innerHTML = categories.map(function (name) {
      return '<button class="tab ' + (name === category ? 'active' : '') + '" data-category="' +
        escapeText(name) + '">' + escapeText(name) + '</button>';
    }).join('');
    tabs.querySelectorAll('button').forEach(function (button) {
      button.addEventListener('click', function () {
        category = button.dataset.category;
        renderTabs();
        renderMenu();
      });
    });
  }

  function renderMenu() {
    var visible = category === 'All' ? menu : menu.filter(function (item) { return item.category === category; });
    grid.innerHTML = visible.map(function (item) {
      return '<article class="menu-card"><h3>' + escapeText(item.name) + '</h3><p>' +
        escapeText(item.category) + '</p><footer><strong>' + money(item.price) +
        '</strong><button class="add" data-name="' + escapeText(item.name) + '">Add +</button></footer></article>';
    }).join('');
    grid.querySelectorAll('.add').forEach(function (button) {
      button.addEventListener('click', function () {
        var item = menu.find(function (row) { return row.name === button.dataset.name; });
        add(item);
      });
    });
  }

  function add(item) {
    if (!item) return;
    var found = cart.find(function (row) { return row.name === item.name; });
    if (found) found.quantity++;
    else cart.push({ name: item.name, quantity: 1, price: item.price });
    renderCart();
    queueRecommendations();
  }

  function remove(name) {
    var found = cart.find(function (row) { return row.name === name; });
    if (!found) return;
    if (found.quantity > 1) found.quantity--;
    else cart = cart.filter(function (row) { return row.name !== name; });
    if (name === activeOfferTarget) {
      activeOfferId = null;
      activeOfferTarget = null;
    }
    renderCart();
    queueRecommendations();
  }

  function renderCart() {
    if (!cart.length) {
      cartList.innerHTML = '<p class="recommendation-status">Your cart is empty.</p>';
      total.textContent = '0 VND';
      checkout.disabled = true;
      return;
    }
    cartList.innerHTML = cart.map(function (item) {
      return '<div class="cart-row"><span>' + escapeText(item.name) + ' × ' + item.quantity + '</span><span>' +
        money(item.price * item.quantity) + ' <button data-remove="' + escapeText(item.name) +
        '" aria-label="Remove ' + escapeText(item.name) + '">×</button></span></div>';
    }).join('');
    cartList.querySelectorAll('[data-remove]').forEach(function (button) {
      button.addEventListener('click', function () { remove(button.dataset.remove); });
    });
    total.textContent = money(cart.reduce(function (sum, item) { return sum + item.price * item.quantity; }, 0));
    checkout.disabled = false;
  }

  function queueRecommendations() {
    recommendationVersion++;
    clearTimeout(timer);
    timer = setTimeout(fetchRecommendations, 250);
  }

  function renderRecommendations(rows) {
    recommendationStatus.textContent = rows[0].cold_start
      ? 'Cold start: complete three orders to unlock personal offers.'
      : 'Based on your completed orders.';
    recommendations.innerHTML = rows.map(function (row) {
      var offer = '';
      if (row.promotion) {
        offer = '<p class="offer">' + escapeText(row.promotion.display_text) + ' personal offer · ' +
          money(row.price) + '</p><button class="add apply-offer" data-offer-id="' +
          escapeText(row.promotion.offer_id) + '" data-offer-target="' +
          escapeText(row.promotion.target_item) + '">Add offer +</button>';
      }
      return '<article class="recommendation"><h3>' + escapeText(row.name) + '</h3><p>' +
        escapeText(row.copy) + '</p>' + offer + '<p class="reason">' +
        escapeText(row.personalization_reason) + '</p></article>';
    }).join('');
    recommendations.querySelectorAll('.apply-offer').forEach(function (button) {
      button.addEventListener('click', function () {
        var item = menu.find(function (row) { return row.name === button.dataset.offerTarget; });
        if (!item) return;
        activeOfferId = button.dataset.offerId;
        activeOfferTarget = button.dataset.offerTarget;
        add(item);
      });
    });
  }

  async function fetchRecommendations() {
    var version = recommendationVersion;
    if (!cart.length) {
      recommendationStatus.textContent = 'Add items to your cart to see picks.';
      recommendations.innerHTML = '';
      return;
    }
    recommendationStatus.textContent = 'Finding your best matches…';
    recommendations.innerHTML = '';
    try {
      var response = await fetch('/api/customer/recommend', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ cart_items: names(), timestamp: new Date().toISOString() })
      });
      if (version !== recommendationVersion) return;
      if (response.status === 401) {
        location.assign('/customer/login');
        return;
      }
      if (!response.ok) throw new Error('Recommendations are unavailable.');
      var rows = await response.json();
      if (version !== recommendationVersion) return;
      if (!rows.length) {
        recommendationStatus.textContent = 'No suitable recommendations found.';
        return;
      }
      renderRecommendations(rows);
    } catch (err) {
      if (version !== recommendationVersion) return;
      recommendationStatus.textContent = 'Recommendations are unavailable. Please try again.';
    }
  }

  async function checkoutOrder() {
    status.textContent = '';
    checkout.disabled = true;
    try {
      var response = await fetch('/api/customer/checkout', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          cart_items: cart.map(function (item) { return { name: item.name, quantity: item.quantity }; }),
          offer_id: activeOfferId
        })
      });
      var payload = await response.json();
      if (response.status === 401) {
        location.assign('/customer/login');
        return;
      }
      if (!response.ok) throw new Error(payload.detail || 'Unable to save order.');
      cart = [];
      activeOfferId = null;
      activeOfferTarget = null;
      status.style.color = '#1f6b38';
      status.textContent = 'Order saved. Your next recommendations will use it.';
      renderCart();
      queueRecommendations();
    } catch (err) {
      status.style.color = '#ad0020';
      status.textContent = err.message || 'Unable to save order.';
      checkout.disabled = false;
    }
  }

  async function init() {
    try {
      var session = await fetch('/api/customer/session');
      if (!session.ok) {
        location.assign('/customer/login');
        return;
      }
      var profile = await session.json();
      document.getElementById('customer-email').textContent = profile.customer.email;
      var response = await fetch('/api/menu');
      if (!response.ok) throw new Error('Menu unavailable');
      menu = await response.json();
      renderTabs();
      renderMenu();
      renderCart();
    } catch (err) {
      grid.innerHTML = '<p>Unable to load the menu. Please try again.</p>';
    }
  }

  document.getElementById('logout-button').addEventListener('click', async function () {
    await fetch('/api/customer/logout', { method: 'POST' });
    location.assign('/customer');
  });
  checkout.addEventListener('click', checkoutOrder);
  init();
}());
