(function () {
  if (typeof io === 'undefined') return;
  const socket = io();

  async function refreshOrdersTable() {
    const tbody = document.getElementById('orders-body');
    if (!tbody) return; // не на списке заказов — не дёргаем бек
    try {
      const params = new URLSearchParams(window.location.search);
      const res = await fetch(`/_partial/orders_table?${params.toString()}`, { cache: 'no-store' });
      if (!res.ok) return;
      tbody.innerHTML = await res.text();
    } catch (e) {
      console.error('refreshOrdersTable error', e);
    }
  }

  socket.on("order_update", () => {
    const delay = (window.__hasFlashToasts === true) ? 3800 : 0;
    setTimeout(refreshOrdersTable, delay);
  });
})();
