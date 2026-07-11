(function () {
  'use strict';

  var menu = [];
  var cart = [];
  var category = 'All';
  var timer;
  var recommendationVersion = 0;
  var activeOfferId = null;
  var activeOfferTarget = null;
  var activeOfferSalePrice = null;
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
      return '<article class="menu-card">' + menuImage(item) + '<h3>' + escapeText(item.name) + '</h3><p>' +
        escapeText(item.category) + '</p><footer><strong>' + money(item.price) +
        '</strong><button class="add" data-name="' + escapeText(item.name) + '">Add +</button></footer></article>';
    }).join('');
    grid.querySelectorAll('.add').forEach(function (button) {
      button.addEventListener('click', function () {
        var item = menu.find(function (row) { return row.name === button.dataset.name; });
        add(item);
      });
    });
    grid.querySelectorAll('img.menu-image').forEach(function (image) {
      image.addEventListener('error', function () {
        var fallback = document.createElement('div');
        fallback.className = 'menu-image menu-image-fallback';
        fallback.setAttribute('role', 'img');
        fallback.setAttribute('aria-label', 'No image available for ' + image.dataset.itemName);
        fallback.textContent = 'No image available';
        image.replaceWith(fallback);
      });
    });
  }

  function menuImage(item) {
    var image = typeof item.image === 'string' ? item.image.trim() : '';
    var itemName = escapeText(item.name);
    if (image) {
      return '<img class="menu-image" src="/static/images/' + encodeURIComponent(image) +
        '" alt="Photo of ' + itemName + '" data-item-name="' + itemName + '">';
    }
    return '<div class="menu-image menu-image-fallback" role="img" aria-label="No image available for ' +
      itemName + '">No image available</div>';
  }

  function clearActiveOffer() {
    activeOfferId = null;
    activeOfferTarget = null;
    activeOfferSalePrice = null;
  }

  function activeOfferAppliesTo(item) {
    return Boolean(
      item && activeOfferId && item.name === activeOfferTarget && item.quantity === 1 &&
      activeOfferSalePrice !== null && Number.isFinite(Number(activeOfferSalePrice)) &&
      Number(activeOfferSalePrice) >= 0
    );
  }

  function validateActiveOffer() {
    if (!activeOfferId) return;
    var target = cart.find(function (item) { return item.name === activeOfferTarget; });
    if (!activeOfferAppliesTo(target)) clearActiveOffer();
  }

  function effectiveItemPrice(item) {
    return activeOfferAppliesTo(item) ? Number(activeOfferSalePrice) : Number(item.price);
  }

  function add(item, skipRecommendation) {
    if (!item) return;
    var found = cart.find(function (row) { return row.name === item.name; });
    if (found) found.quantity++;
    else cart.push({ name: item.name, quantity: 1, price: item.price });
    validateActiveOffer();
    renderCart();
    if (!skipRecommendation) queueRecommendations();
  }

  function remove(name) {
    var found = cart.find(function (row) { return row.name === name; });
    if (!found) return;
    if (found.quantity > 1) found.quantity--;
    else cart = cart.filter(function (row) { return row.name !== name; });
    validateActiveOffer();
    renderCart();
    queueRecommendations();
  }

  function renderCart() {
    validateActiveOffer();
    if (!cart.length) {
      cartList.innerHTML = '<p class="recommendation-status">Your cart is empty.</p>';
      total.textContent = '0 VND';
      checkout.disabled = true;
      return;
    }
    cartList.innerHTML = cart.map(function (item) {
      return '<div class="cart-row"><span>' + escapeText(item.name) + ' × ' + item.quantity + '</span><span>' +
        money(effectiveItemPrice(item) * item.quantity) + ' <button data-remove="' + escapeText(item.name) +
        '" aria-label="Remove ' + escapeText(item.name) + '">×</button></span></div>';
    }).join('');
    cartList.querySelectorAll('[data-remove]').forEach(function (button) {
      button.addEventListener('click', function () { remove(button.dataset.remove); });
    });
    total.textContent = money(cart.reduce(function (sum, item) {
      return sum + effectiveItemPrice(item) * item.quantity;
    }, 0));
    checkout.disabled = false;
  }

  function queueRecommendations() {
    recommendationVersion++;
    clearTimeout(timer);
    if (activeOfferId) {
      recommendationStatus.textContent = 'Personal offer reserved. Change the offer item to refresh recommendations.';
      recommendations.innerHTML = '';
      return;
    }
    if (window.__CUSTOMER_APP_TEST__) return;
    timer = setTimeout(fetchRecommendations, 250);
  }

  function renderRecommendations(rows) {
    recommendationStatus.textContent = rows[0].cold_start
      ? 'Cold start: complete three orders to unlock personal offers.'
      : 'Based on your completed orders.';
    recommendations.innerHTML = rows.map(function (row) {
      var offer = '';
      if (row.promotion && row.promotion.type === 'personal') {
        offer = '<p class="offer">' + escapeText(row.promotion.display_text) + ' personal offer · ' +
          money(row.promotion.sale_price) + '</p><button class="add apply-offer" data-offer-id="' +
          escapeText(row.promotion.offer_id) + '" data-offer-target="' +
          escapeText(row.promotion.target_item) + '" data-offer-sale-price="' +
          escapeText(row.promotion.sale_price) + '">Add offer +</button>';
      } else if (row.promotion && row.promotion.type === 'global') {
        offer = '<p class="offer">' + escapeText(row.promotion.display_text || 'Active promotion') + ' · ' +
          money(row.price) + '</p>';
      }
      return '<article class="recommendation"><h3>' + escapeText(row.name) + '</h3><p>' +
        escapeText(row.copy) + '</p>' + offer + '<p class="reason">' +
        escapeText(row.personalization_reason) + '</p></article>';
    }).join('');
    recommendations.querySelectorAll('.apply-offer').forEach(function (button) {
      button.addEventListener('click', function () {
        applyPersonalOffer({
          offer_id: button.dataset.offerId,
          target_item: button.dataset.offerTarget,
          sale_price: button.dataset.offerSalePrice
        });
      });
    });
  }

  function applyPersonalOffer(offer) {
    if (!offer || !offer.offer_id || !offer.target_item || !Number.isFinite(Number(offer.sale_price))) return;
    var item = menu.find(function (row) { return row.name === offer.target_item; });
    if (!item) return;
    activeOfferId = offer.offer_id;
    activeOfferTarget = offer.target_item;
    activeOfferSalePrice = Number(offer.sale_price);
    recommendationVersion++;
    clearTimeout(timer);
    recommendations.innerHTML = '';
    recommendationStatus.textContent = 'Personal offer added to your cart.';
    add(item, true);
  }

  function checkoutPayload() {
    return {
      cart_items: cart.map(function (item) { return { name: item.name, quantity: item.quantity }; }),
      offer_id: activeOfferId
    };
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
        body: JSON.stringify(checkoutPayload())
      });
      var payload = await response.json();
      if (response.status === 401) {
        location.assign('/customer/login');
        return;
      }
      if (!response.ok) throw new Error(payload.detail || 'Unable to save order.');
      cart = [];
      clearActiveOffer();
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
  if (window.__CUSTOMER_APP_TEST__) {
    window.__customerAppTestHooks = {
      add: add,
      applyPersonalOffer: applyPersonalOffer,
      checkoutPayload: checkoutPayload,
      getState: function () {
        return {
          activeOfferId: activeOfferId,
          cartMarkup: cartList.innerHTML,
          menuMarkup: grid.innerHTML,
          recommendationStatus: recommendationStatus.textContent,
          total: total.textContent
        };
      },
      renderMenu: renderMenu,
      queueRecommendations: queueRecommendations,
      remove: remove,
      resetCart: function () {
        cart = [];
        clearActiveOffer();
        renderCart();
      },
      setMenu: function (items) { menu = items || []; }
    };
  } else {
    init();
  }
}());
