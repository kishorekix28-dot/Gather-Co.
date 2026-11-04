(function () {
  "use strict";
  const el = document.getElementById("chart-data");
  if (!el || typeof Chart === "undefined") return;
  const d = JSON.parse(el.textContent);
  Chart.defaults.font.family = "Inter, system-ui, sans-serif";
  Chart.defaults.color = "#64748b";
  Chart.defaults.plugins.legend.labels.usePointStyle = true;
  const grid = { color: "#eef2f7" };

  new Chart(document.getElementById("monthlyChart"), {
    type: "bar",
    data: {
      labels: d.months,
      datasets: [
        { label: "Stock in", data: d.stock_in, backgroundColor: "#6366f1", borderRadius: 6, maxBarThickness: 28 },
        { label: "Stock out", data: d.stock_out, backgroundColor: "#22d3ee", borderRadius: 6, maxBarThickness: 28 },
      ],
    },
    options: { maintainAspectRatio: false, scales: { x: { grid: { display: false } }, y: { grid, beginAtZero: true } },
      plugins: { legend: { position: "bottom" } } },
  });

  new Chart(document.getElementById("statusChart"), {
    type: "doughnut",
    data: { labels: ["In stock", "Low stock", "Out of stock"],
      datasets: [{ data: d.status, backgroundColor: ["#10b981", "#f59e0b", "#ef4444"], borderWidth: 0, hoverOffset: 6 }] },
    options: { maintainAspectRatio: false, cutout: "68%", plugins: { legend: { position: "bottom" } } },
  });

  new Chart(document.getElementById("categoryChart"), {
    type: "bar",
    data: { labels: d.categories,
      datasets: [{ label: "Value (USD)", data: d.category_values, backgroundColor: "#818cf8", borderRadius: 6, maxBarThickness: 22 }] },
    options: { indexAxis: "y", maintainAspectRatio: false, plugins: { legend: { display: false } },
      scales: { x: { grid, beginAtZero: true }, y: { grid: { display: false } } } },
  });
})();
