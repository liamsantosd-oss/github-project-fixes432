/* Offline interactions for archived catalog captures. No Roblox API or network calls. */
(function () {
  'use strict';

  function ready(callback) {
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', callback, { once: true });
    else callback();
  }

  ready(function () {
    var root = document.querySelector('#main-view');
    if (!root) return;
    var cards = Array.prototype.slice.call(root.querySelectorAll('.catalog-item-container'));
    if (!cards.length) return;

    var form = document.querySelector('form[action*="/catalog"]');
    var input = form && (form.querySelector('#avatar-shop-keyword-input') || form.querySelector('input[name="searchField"]') || form.querySelector('input[type="search"], input[name="keyword"], input'));
    if (!input) input = document.querySelector('[data-testid="navigation-search-input-field"]');

    var filterButtons = Array.prototype.slice.call(document.querySelectorAll('.filter-select'));
    var priceButton = filterButtons.find(function (button) { return /price/i.test(button.textContent); });
    var sortButton = filterButtons.find(function (button) { return /sort by/i.test(button.textContent); });
    var allCards = cards.map(function (card, index) {
      var name = card.querySelector('.item-card-name');
      var creator = card.querySelector('.creator-name');
      var price = card.querySelector('.text-robux-tile');
      var link = card.querySelector('a[href*="/catalog/"]');
      return {
        element: card,
        index: index,
        name: (name ? name.textContent : '').trim(),
        creator: (creator ? creator.textContent : '').trim(),
        price: price ? Number((price.textContent || '').replace(/[^0-9.]/g, '')) : NaN,
        href: link ? link.getAttribute('href') : ''
      };
    });

    var options = document.createElement('section');
    options.className = 'offline-catalog-controls';
    options.setAttribute('aria-label', 'Offline catalog controls');
    options.innerHTML = '<label class="offline-catalog-label">Search saved items <input class="offline-catalog-search" type="search" placeholder="Name or creator" autocomplete="off"></label>' +
      '<label class="offline-catalog-label">Sort <select class="offline-catalog-sort"><option value="captured">Captured order</option><option value="name">Name A–Z</option><option value="price-low">Price: low to high</option><option value="price-high">Price: high to low</option></select></label>' +
      '<p class="offline-catalog-status" role="status" aria-live="polite"></p>';
    root.insertBefore(options, root.firstChild);

    var search = options.querySelector('.offline-catalog-search');
    var sort = options.querySelector('.offline-catalog-sort');
    var status = options.querySelector('.offline-catalog-status');

    var stylesheet = document.createElement('link');
    stylesheet.rel = 'stylesheet';
    stylesheet.href = '/assets/local-catalog.css';
    document.head.appendChild(stylesheet);

    // Make captured item links stay inside the archive; saved item detail pages
    // are not part of this snapshot, so explain that limitation on the current page.
    allCards.forEach(function (item) {
      item.element.querySelectorAll('a[href*="roblox.com/catalog/"]').forEach(function (anchor) {
        anchor.setAttribute('href', '#offline-item');
        anchor.setAttribute('data-offline-item-name', item.name || 'Saved catalog item');
      });
      var thumbnail = item.element.querySelector('.thumbnail-2d-container.shimmer');
      if (thumbnail) {
        item.element.classList.add('offline-unavailable');
        thumbnail.setAttribute('aria-label', 'Image not included in this offline capture');
      }
    });

    function apply() {
      var query = (search.value || '').trim().toLowerCase();
      var matching = allCards.filter(function (item) {
        return !query || (item.name + ' ' + item.creator).toLowerCase().indexOf(query) !== -1;
      });
      var mode = sort.value;
      matching.sort(function (a, b) {
        if (mode === 'name') return a.name.localeCompare(b.name);
        if (mode === 'price-low') return (isNaN(a.price) ? Infinity : a.price) - (isNaN(b.price) ? Infinity : b.price);
        if (mode === 'price-high') return (isNaN(b.price) ? -Infinity : b.price) - (isNaN(a.price) ? -Infinity : a.price);
        return a.index - b.index;
      });
      allCards.forEach(function (item) { item.element.classList.toggle('offline-hidden', matching.indexOf(item) === -1); });
      var list = root.querySelector('.organic-items-wrapper');
      if (list) matching.forEach(function (item) { list.appendChild(item.element); });
      status.textContent = matching.length + ' of ' + allCards.length + ' saved items shown. Search and sorting use this captured list only; live marketplace filters and new results are unavailable offline.';
    }

    search.addEventListener('input', apply);
    sort.addEventListener('change', apply);
    if (form) form.addEventListener('submit', function (event) { event.preventDefault(); search.value = input ? input.value : search.value; apply(); });
    if (input) input.addEventListener('input', function () { search.value = input.value; apply(); });

    document.addEventListener('click', function (event) {
      var anchor = event.target && event.target.closest ? event.target.closest('a[data-offline-item-name]') : null;
      if (!anchor) return;
      event.preventDefault();
      window.alert('“' + anchor.getAttribute('data-offline-item-name') + '” is a saved marketplace listing. Its item detail page was not included in this offline archive.');
    });

    // Captured Roblox dropdowns depend on blocked backend APIs. Disable them
    // explicitly rather than leaving controls that look live but do nothing.
    filterButtons.forEach(function (button) {
      button.disabled = true;
      button.setAttribute('aria-disabled', 'true');
      button.setAttribute('title', 'Live marketplace filters are unavailable in the offline archive');
      button.style.opacity = '0.65';
      button.style.cursor = 'not-allowed';
    });
    apply();
  });
}());
