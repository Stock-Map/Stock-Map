const API_URL =
  location.port === "5500" || location.protocol === "file:"
    ? "http://127.0.0.1:5000"
    : "";

const state = {
  fornecedores: [],
  lojistas: [],
  produtos: [],
  pedidos: [],
  alertas: [],
  relatorio: null,
  rotas: [],
  movimentacoes: [],
  itensPedido: [],
  filtrosPedidos: {},
  filtrosMovimentacoes: {},
  periodoRelatorio: {},
};

const titles = {
  painel: "Painel",
  fornecedores: "Fornecedores",
  lojistas: "Lojistas",
  produtos: "Produtos",
  pedidos: "Pedidos",
  alertas: "Alertas",
  relatorios: "Relatorios",
  rotas: "Rotas",
  movimentacoes: "Movimentacoes",
};

const money = new Intl.NumberFormat("pt-BR", {
  style: "currency",
  currency: "BRL",
});

const number = new Intl.NumberFormat("pt-BR");

function qs(selector) {
  return document.querySelector(selector);
}

function qsa(selector) {
  return [...document.querySelectorAll(selector)];
}

function showToast(message) {
  const toast = qs("#toast");
  toast.textContent = message;
  toast.classList.add("show");
  window.clearTimeout(showToast.timer);
  showToast.timer = window.setTimeout(() => toast.classList.remove("show"), 3600);
}

async function api(path, options = {}) {
  const response = await fetch(`${API_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  if (response.status === 204) {
    return null;
  }

  const corpo = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(corpo.erro || "Falha na requisicao.");
  }

  return corpo;
}

function formData(form) {
  return Object.fromEntries(new FormData(form).entries());
}

function apenasPreenchidos(dados) {
  return Object.fromEntries(
    Object.entries(dados).filter(([, valor]) => valor !== ""),
  );
}

function setSelectOptions(select, items, placeholder) {
  const currentValue = select.value;
  select.innerHTML = `<option value="">${placeholder}</option>`;
  items.forEach((item) => {
    const option = document.createElement("option");
    option.value = item.id;
    option.textContent = item.nome;
    select.appendChild(option);
  });
  if (items.some((item) => String(item.id) === String(currentValue))) {
    select.value = currentValue;
  }
}

function statusLabel(status) {
  const rotulos = {
    pendente: "Pendente",
    confirmado: "Confirmado",
    despachado: "Em entrega",
    entregue: "Entregue",
    cancelado: "Cancelado",
  };
  return rotulos[status] || status;
}

function stockLabel(status) {
  const rotulos = {
    disponivel: "Disponivel",
    baixo: "Baixo",
    indisponivel: "Indisponivel",
  };
  return rotulos[status] || status;
}

function empty(message) {
  return `<p class="empty-state">${message}</p>`;
}

function renderMetrics() {
  const resumo = state.relatorio?.resumo || {};
  const metrics = [
    ["Fornecedores", resumo.fornecedores || 0],
    ["Lojistas", resumo.lojistas || 0],
    ["Produtos ativos", resumo.produtos || 0],
    ["Unidades em estoque", number.format(resumo.unidades_estoque || 0)],
    ["Pedidos abertos", resumo.pedidos_abertos || 0],
    ["Pedidos no periodo", resumo.pedidos_periodo || 0],
    ["Estoque baixo", resumo.produtos_estoque_baixo || 0],
    ["Faturamento no periodo", money.format(resumo.faturamento_periodo || 0)],
  ];
  qs("#grade-metricas").innerHTML = metrics
    .map(([label, value]) => `<article class="metric-card"><span>${label}</span><strong>${value}</strong></article>`)
    .join("");
}

function renderAlerts() {
  const markup = state.alertas.length
    ? state.alertas
        .map(
          (alerta) => `
            <article class="alert-card ${alerta.severidade}">
              <h3>${alerta.produto_nome}</h3>
              <p>${alerta.fornecedor_nome} | Estoque ${alerta.quantidade} | Minimo ${alerta.estoque_minimo}</p>
            </article>
          `,
        )
        .join("")
    : empty("Nenhum alerta ativo.");
  qs("#lista-alertas").innerHTML = markup;
  qs("#painel-alertas").innerHTML = markup;
  qs("#contador-alertas").textContent = `${state.alertas.length} alertas`;
  qs("#contador-alertas-tela").textContent = state.alertas.length;
}

function renderEntities() {
  qs("#contador-fornecedores").textContent = state.fornecedores.length;
  qs("#contador-lojistas").textContent = state.lojistas.length;

  qs("#lista-fornecedores").innerHTML = state.fornecedores.length
    ? state.fornecedores
        .map(
          (fornecedor) => `
            <article class="entity-card">
              <h3>${fornecedor.nome}</h3>
              <p>${fornecedor.nome_contato} | ${fornecedor.email}</p>
              <p>${fornecedor.cidade || "Cidade nao informada"} ${fornecedor.estado || ""}</p>
            </article>
          `,
        )
        .join("")
    : empty("Nenhum fornecedor cadastrado.");

  qs("#lista-lojistas").innerHTML = state.lojistas.length
    ? state.lojistas
        .map(
          (lojista) => `
            <article class="entity-card">
              <h3>${lojista.nome}</h3>
              <p>${lojista.nome_contato} | ${lojista.email}</p>
              <p>${lojista.cidade || "Cidade nao informada"} ${lojista.estado || ""}</p>
            </article>
          `,
        )
        .join("")
    : empty("Nenhum lojista cadastrado.");
}

function renderSelects() {
  setSelectOptions(qs("#produto-fornecedor"), state.fornecedores, "Selecione");
  setSelectOptions(qs("#pedido-lojista"), state.lojistas, "Selecione");
  setSelectOptions(qs("#pedido-fornecedor"), state.fornecedores, "Selecione");
  setSelectOptions(qs("#rota-fornecedor"), state.fornecedores, "Selecione");
  setSelectOptions(qs("#filtro-pedido-lojista"), state.lojistas, "Todos os lojistas");
  setSelectOptions(qs("#filtro-movimentacao-produto"), state.produtos, "Todos os produtos");
  setSelectOptions(
    qs("#filtro-movimentacao-fornecedor"),
    state.fornecedores,
    "Todos os fornecedores",
  );
  renderOrderProductOptions();
}

function filteredProducts() {
  const busca = qs("#busca-produto").value.trim().toLowerCase();
  if (!busca) return state.produtos;
  return state.produtos.filter((produto) =>
    [produto.nome, produto.sku, produto.categoria, produto.fornecedor_nome]
      .filter(Boolean)
      .some((valor) => valor.toLowerCase().includes(busca)),
  );
}

function renderProducts() {
  const rows = filteredProducts()
    .map(
      (produto) => `
        <tr>
          <td><strong>${produto.nome}</strong><br><span class="muted">${produto.categoria || "Sem categoria"}</span></td>
          <td>${produto.fornecedor_nome}</td>
          <td>${produto.sku}</td>
          <td>
            <span class="stock-status stock-${produto.status_estoque}">${stockLabel(produto.status_estoque)}</span>
            <br><span class="muted">${produto.quantidade} un. | min. ${produto.estoque_minimo}</span>
          </td>
          <td>${money.format(produto.preco_unitario || 0)}</td>
          <td>
            <button class="btn btn-secondary" type="button" data-stock="${produto.id}" data-current="${produto.quantidade}">Ajustar</button>
          </td>
        </tr>
      `,
    )
    .join("");
  qs("#tabela-produtos").innerHTML = rows || `<tr><td colspan="6">${empty("Nenhum produto encontrado.")}</td></tr>`;
}

function renderOrderProductOptions() {
  const fornecedorId = qs("#pedido-fornecedor").value;
  const produtos = state.produtos.filter(
    (produto) => !fornecedorId || String(produto.fornecedor_id) === String(fornecedorId),
  );
  const select = qs("#pedido-produto");
  const currentValue = select.value;
  select.innerHTML = '<option value="">Selecione</option>';
  produtos.forEach((produto) => {
    const option = document.createElement("option");
    option.value = produto.id;
    option.textContent = `${produto.nome} | ${produto.quantidade} un. | ${money.format(produto.preco_unitario || 0)}`;
    select.appendChild(option);
  });
  if (produtos.some((produto) => String(produto.id) === String(currentValue))) {
    select.value = currentValue;
  }
}

function renderOrderDraft() {
  qs("#itens-pedido").innerHTML = state.itensPedido.length
    ? state.itensPedido
        .map(
          (item, index) => `
            <div class="draft-item">
              <span>${item.produto_nome} | qtd. ${item.quantidade}</span>
              <button class="btn btn-danger" type="button" data-remove-item="${index}">Remover</button>
            </div>
          `,
        )
        .join("")
    : empty("Nenhum item adicionado.");
}

function renderOrders() {
  qs("#contador-pedidos").textContent = state.pedidos.length;
  const rows = state.pedidos
    .map(
      (pedido) => `
        <tr>
          <td>#${pedido.id}</td>
          <td>${pedido.lojista_nome}</td>
          <td>${pedido.fornecedor_nome}</td>
          <td>${pedido.total_itens}</td>
          <td><span class="status status-${pedido.status}">${statusLabel(pedido.status)}</span></td>
          <td>${money.format(pedido.valor_total || 0)}</td>
          <td>
            <select data-order-status="${pedido.id}" aria-label="Alterar status do pedido ${pedido.id}">
              ${["confirmado", "despachado", "entregue", "cancelado"]
                .map((status) => `<option value="${status}" ${status === pedido.status ? "selected" : ""}>${statusLabel(status)}</option>`)
                .join("")}
            </select>
          </td>
        </tr>
      `,
    )
    .join("");
  qs("#tabela-pedidos").innerHTML = rows || `<tr><td colspan="7">${empty("Nenhum pedido registrado.")}</td></tr>`;
  qs("#pedidos-recentes").innerHTML =
    state.pedidos
      .slice(0, 6)
      .map(
        (pedido) => `
          <tr>
            <td>#${pedido.id}</td>
            <td>${pedido.lojista_nome}</td>
            <td>${pedido.fornecedor_nome}</td>
            <td><span class="status status-${pedido.status}">${statusLabel(pedido.status)}</span></td>
            <td>${money.format(pedido.valor_total || 0)}</td>
          </tr>
        `,
      )
      .join("") || `<tr><td colspan="5">${empty("Nenhum pedido registrado.")}</td></tr>`;
}

function renderMovimentacoes() {
  const corpo = qs("#tabela-movimentacoes");
  qs("#contador-movimentacoes").textContent = state.movimentacoes.length;

  if (!state.movimentacoes.length) {
    corpo.innerHTML = `<tr><td colspan="6">${empty("Nenhuma movimentacao no periodo.")}</td></tr>`;
    return;
  }

  corpo.innerHTML = state.movimentacoes
    .map((movimentacao) => {
      const variacao = movimentacao.variacao_quantidade;
      const sinal = variacao > 0 ? `+${variacao}` : `${variacao}`;
      return `
        <tr>
          <td>${new Date(movimentacao.criado_em).toLocaleString("pt-BR")}</td>
          <td>${movimentacao.produto_nome}<br><span class="muted">${movimentacao.sku}</span></td>
          <td>${movimentacao.fornecedor_nome}</td>
          <td><span class="status status-${movimentacao.tipo_movimentacao}">${movimentacao.tipo_movimentacao}</span></td>
          <td>${sinal}</td>
          <td>${movimentacao.motivo || "-"}</td>
        </tr>
      `;
    })
    .join("");
}

const chartColors = {
  accent: "#0369a1",
  blue: "#1d4ed8",
  success: "#047857",
  warning: "#b45309",
  danger: "#b91c1c",
  slate: "#64748b",
  violet: "#7c3aed",
};

const chartInstances = {};

function renderChart(canvasId, config) {
  if (typeof Chart === "undefined") return;
  const canvas = qs(`#${canvasId}`);
  if (!canvas) return;
  if (chartInstances[canvasId]) {
    chartInstances[canvasId].destroy();
  }
  chartInstances[canvasId] = new Chart(canvas, config);
}

function renderOrderStatusChart() {
  const ordem = ["confirmado", "despachado", "entregue", "pendente", "cancelado"];
  const palette = {
    confirmado: chartColors.blue,
    despachado: chartColors.accent,
    entregue: chartColors.success,
    pendente: chartColors.warning,
    cancelado: chartColors.danger,
  };
  const counts = {};
  state.pedidos.forEach((pedido) => {
    counts[pedido.status] = (counts[pedido.status] || 0) + 1;
  });
  const present = ordem.filter((status) => counts[status]);
  renderChart("grafico-status-pedidos", {
    type: "doughnut",
    data: {
      labels: present.map((status) => statusLabel(status)),
      datasets: [
        {
          data: present.map((status) => counts[status]),
          backgroundColor: present.map((status) => palette[status]),
          borderWidth: 0,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: "62%",
      plugins: { legend: { position: "bottom" } },
    },
  });
}

function renderStockStatusChart() {
  const buckets = { disponivel: 0, baixo: 0, indisponivel: 0 };
  state.produtos.forEach((produto) => {
    if (buckets[produto.status_estoque] !== undefined) buckets[produto.status_estoque] += 1;
  });
  renderChart("grafico-status-estoque", {
    type: "doughnut",
    data: {
      labels: [stockLabel("disponivel"), stockLabel("baixo"), stockLabel("indisponivel")],
      datasets: [
        {
          data: [buckets.disponivel, buckets.baixo, buckets.indisponivel],
          backgroundColor: [chartColors.success, chartColors.warning, chartColors.danger],
          borderWidth: 0,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: "62%",
      plugins: { legend: { position: "bottom" } },
    },
  });
}

function renderTopProductsChart() {
  const rows = state.relatorio?.top_produtos || [];
  renderChart("grafico-top-produtos", {
    type: "bar",
    data: {
      labels: rows.map((row) => row.nome),
      datasets: [
        {
          label: "Demanda (un.)",
          data: rows.map((row) => Number(row.demanda || 0)),
          backgroundColor: chartColors.accent,
          borderRadius: 6,
        },
      ],
    },
    options: {
      indexAxis: "y",
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: { x: { beginAtZero: true, ticks: { precision: 0 } } },
    },
  });
}

function renderSupplierRevenueChart() {
  const rows = state.relatorio?.desempenho_fornecedores || [];
  renderChart("grafico-faturamento-fornecedor", {
    type: "bar",
    data: {
      labels: rows.map((row) => row.nome),
      datasets: [
        {
          label: "Faturamento",
          data: rows.map((row) => Number(row.total || 0)),
          backgroundColor: chartColors.violet,
          borderRadius: 6,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: { label: (ctx) => money.format(ctx.parsed.y || 0) },
        },
      },
      scales: {
        y: {
          beginAtZero: true,
          ticks: { callback: (value) => money.format(value) },
        },
      },
    },
  });
}

function renderCharts() {
  renderOrderStatusChart();
  renderStockStatusChart();
  renderTopProductsChart();
  renderSupplierRevenueChart();
}

function renderBars(container, rows, labelKey, valueKey, formatValue = (value) => value) {
  const max = Math.max(...rows.map((row) => Number(row[valueKey] || 0)), 1);
  container.innerHTML = rows.length
    ? rows
        .map((row) => {
          const value = Number(row[valueKey] || 0);
          const width = Math.max(4, Math.round((value / max) * 100));
          return `
            <div class="bar-row">
              <header><span>${row[labelKey]}</span><span>${formatValue(value)}</span></header>
              <div class="bar-track"><div class="bar-fill" style="width: ${width}%"></div></div>
            </div>
          `;
        })
        .join("")
    : empty("Sem dados para exibir.");
}

function renderReports() {
  const periodo = state.relatorio?.periodo;
  if (periodo) {
    qs("#periodo-relatorio").textContent =
      `${periodo.data_inicio} ate ${periodo.data_fim}`;
  }
  renderBars(qs("#top-produtos"), state.relatorio?.top_produtos || [], "nome", "demanda", (value) => `${value} un.`);
  renderBars(qs("#desempenho-fornecedores"), state.relatorio?.desempenho_fornecedores || [], "nome", "total", (value) => money.format(value));
}

function renderRoutes() {
  qs("#contador-rotas").textContent = state.rotas.length;
  qs("#lista-rotas").innerHTML = state.rotas.length
    ? state.rotas
        .map(
          (rota) => `
            <article class="route-card">
              <h3>Rota #${rota.id} | ${rota.fornecedor_nome}</h3>
              <p>${rota.total_paradas} paradas | ${rota.distancia_total_km || 0} km | ${rota.status}</p>
              <ol class="route-stops">
                ${(rota.paradas || [])
                  .map(
                    (parada) => `
                      <li>
                        Pedido #${parada.pedido_id} - ${parada.lojista_nome}
                        <span class="muted">${parada.cidade || ""} ${parada.distancia_anterior_km ? `| ${parada.distancia_anterior_km} km` : ""}</span>
                      </li>
                    `,
                  )
                  .join("")}
              </ol>
            </article>
          `,
        )
        .join("")
    : empty("Nenhuma rota planejada.");
}

function renderAll() {
  renderMetrics();
  renderAlerts();
  renderEntities();
  renderSelects();
  renderProducts();
  renderOrders();
  renderOrderDraft();
  renderReports();
  renderRoutes();
  renderMovimentacoes();
  renderCharts();
}

async function loadAll(silent = false) {
  try {
    const parametrosPedidos = new URLSearchParams(state.filtrosPedidos).toString();
    const parametrosMovimentacoes = new URLSearchParams(state.filtrosMovimentacoes).toString();
    const parametrosRelatorio = new URLSearchParams(state.periodoRelatorio).toString();

    const [
      fornecedores,
      lojistas,
      produtos,
      pedidos,
      alertas,
      relatorio,
      rotas,
      movimentacoes,
    ] = await Promise.all([
      api("/fornecedores"),
      api("/lojistas"),
      api("/produtos"),
      api(`/pedidos${parametrosPedidos ? `?${parametrosPedidos}` : ""}`),
      api("/alertas"),
      api(`/relatorios${parametrosRelatorio ? `?${parametrosRelatorio}` : ""}`),
      api("/rotas"),
      api(`/movimentacoes${parametrosMovimentacoes ? `?${parametrosMovimentacoes}` : ""}`),
    ]);

    Object.assign(state, {
      fornecedores,
      lojistas,
      produtos,
      pedidos,
      alertas,
      relatorio,
      rotas,
      movimentacoes,
    });

    renderAll();
    if (!silent) showToast("Dados atualizados.");
  } catch (erro) {
    showToast(erro.message);
  }
}

async function submitJson(form, path, mensagemSucesso, afterSubmit) {
  const button = form.querySelector('button[type="submit"]');
  button.disabled = true;
  try {
    await api(path, {
      method: "POST",
      body: JSON.stringify(formData(form)),
    });
    form.reset();
    showToast(mensagemSucesso);
    await afterSubmit?.();
    await loadAll(true);
  } catch (erro) {
    showToast(erro.message);
  } finally {
    button.disabled = false;
  }
}

function bindNavigation() {
  qsa(".nav-link").forEach((button) => {
    button.addEventListener("click", () => {
      qsa(".nav-link").forEach((item) => item.classList.remove("active"));
      qsa(".view").forEach((view) => view.classList.remove("active"));
      button.classList.add("active");
      qs(`#${button.dataset.view}`).classList.add("active");
      qs("#titulo-tela").textContent = titles[button.dataset.view];
    });
  });
}

function bindForms() {
  qs("#form-fornecedor").addEventListener("submit", (event) => {
    event.preventDefault();
    submitJson(event.currentTarget, "/fornecedores", "Fornecedor cadastrado.");
  });

  qs("#form-lojista").addEventListener("submit", (event) => {
    event.preventDefault();
    submitJson(event.currentTarget, "/lojistas", "Lojista cadastrado.");
  });

  qs("#form-produto").addEventListener("submit", (event) => {
    event.preventDefault();
    submitJson(event.currentTarget, "/produtos", "Produto cadastrado.");
  });

  qs("#form-rota").addEventListener("submit", (event) => {
    event.preventDefault();
    submitJson(event.currentTarget, "/rotas", "Rota gerada.");
  });

  qs("#form-pedido").addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!state.itensPedido.length) {
      showToast("Adicione ao menos um item ao pedido.");
      return;
    }
    const form = event.currentTarget;
    const dados = formData(form);
    dados.itens = state.itensPedido.map(({ produto_id, quantidade }) => ({
      produto_id,
      quantidade,
    }));
    const button = form.querySelector('button[type="submit"]');
    button.disabled = true;
    try {
      await api("/pedidos", {
        method: "POST",
        body: JSON.stringify(dados),
      });
      state.itensPedido = [];
      form.reset();
      renderOrderDraft();
      showToast("Pedido registrado.");
      await loadAll(true);
    } catch (erro) {
      showToast(erro.message);
    } finally {
      button.disabled = false;
    }
  });
}

function bindOrderBuilder() {
  qs("#pedido-fornecedor").addEventListener("change", () => {
    state.itensPedido = [];
    renderOrderProductOptions();
    renderOrderDraft();
  });

  qs("#adicionar-item-pedido").addEventListener("click", () => {
    const produtoId = qs("#pedido-produto").value;
    const quantidade = Number(qs("#pedido-quantidade").value || 0);
    const produto = state.produtos.find((item) => String(item.id) === String(produtoId));
    if (!produto || quantidade < 1) {
      showToast("Selecione um produto e uma quantidade valida.");
      return;
    }
    state.itensPedido.push({
      produto_id: produto.id,
      produto_nome: produto.nome,
      quantidade,
    });
    renderOrderDraft();
  });

  qs("#itens-pedido").addEventListener("click", (event) => {
    const button = event.target.closest("[data-remove-item]");
    if (!button) return;
    state.itensPedido.splice(Number(button.dataset.removeItem), 1);
    renderOrderDraft();
  });
}

function bindTableActions() {
  document.body.addEventListener("click", async (event) => {
    const stockButton = event.target.closest("[data-stock]");
    if (!stockButton) return;
    const valor = window.prompt("Nova quantidade em estoque:", stockButton.dataset.current);
    if (valor === null) return;
    try {
      await api(`/produtos/${stockButton.dataset.stock}/estoque`, {
        method: "PATCH",
        body: JSON.stringify({ quantidade: Number(valor), motivo: "Ajuste pelo painel" }),
      });
      showToast("Estoque atualizado.");
      await loadAll(true);
    } catch (erro) {
      showToast(erro.message);
    }
  });

  document.body.addEventListener("change", async (event) => {
    const select = event.target.closest("[data-order-status]");
    if (!select) return;
    try {
      await api(`/pedidos/${select.dataset.orderStatus}/status`, {
        method: "PATCH",
        body: JSON.stringify({ status: select.value }),
      });
      showToast("Pedido atualizado.");
      await loadAll(true);
    } catch (erro) {
      showToast(erro.message);
      await loadAll(true);
    }
  });
}

function bindFiltrosPedidos() {
  const form = qs("#filtros-pedidos");

  form.addEventListener("submit", async (evento) => {
    evento.preventDefault();
    state.filtrosPedidos = apenasPreenchidos(formData(form));
    await loadAll(true);
  });

  qs("#limpar-filtros-pedidos").addEventListener("click", async () => {
    form.reset();
    state.filtrosPedidos = {};
    await loadAll(true);
  });
}

function bindFiltrosMovimentacoes() {
  const form = qs("#filtros-movimentacoes");

  form.addEventListener("submit", async (evento) => {
    evento.preventDefault();
    state.filtrosMovimentacoes = apenasPreenchidos(formData(form));
    await loadAll(true);
  });

  qs("#limpar-filtros-movimentacoes").addEventListener("click", async () => {
    form.reset();
    state.filtrosMovimentacoes = {};
    await loadAll(true);
  });
}

function bindFiltroRelatorio() {
  const form = qs("#filtros-relatorio");

  form.addEventListener("submit", async (evento) => {
    evento.preventDefault();
    state.periodoRelatorio = apenasPreenchidos(formData(form));
    await loadAll(true);
  });
}

function bindFilters() {
  qs("#busca-produto").addEventListener("input", renderProducts);
  qs("#botao-atualizar").addEventListener("click", () => loadAll());
}

document.addEventListener("DOMContentLoaded", () => {
  bindNavigation();
  bindForms();
  bindOrderBuilder();
  bindTableActions();
  bindFilters();
  bindFiltrosPedidos();
  bindFiltrosMovimentacoes();
  bindFiltroRelatorio();
  loadAll();
  window.setInterval(() => loadAll(true), 15000);
});
