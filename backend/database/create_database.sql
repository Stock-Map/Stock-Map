CREATE DATABASE IF NOT EXISTS stock_map
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE stock_map;

-- ---------------------------------------------------------------------------
-- Tabelas. Espelham os models SQLAlchemy em backend/models/.
-- O db.create_all() tambem cria estas tabelas; este bloco existe para que o
-- script rode sozinho pelo cliente mysql.
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS fornecedores (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(140) NOT NULL,
    cnpj VARCHAR(24),
    nome_contato VARCHAR(120) NOT NULL,
    email VARCHAR(180) NOT NULL,
    telefone VARCHAR(40),
    endereco VARCHAR(220),
    cidade VARCHAR(100),
    estado VARCHAR(40),
    latitude DECIMAL(10, 7),
    longitude DECIMAL(10, 7),
    criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_fornecedores_email (email)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS lojistas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(140) NOT NULL,
    cnpj VARCHAR(24),
    nome_contato VARCHAR(120) NOT NULL,
    email VARCHAR(180) NOT NULL,
    telefone VARCHAR(40),
    endereco VARCHAR(220),
    cidade VARCHAR(100),
    estado VARCHAR(40),
    latitude DECIMAL(10, 7),
    longitude DECIMAL(10, 7),
    criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_lojistas_email (email)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS produtos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    fornecedor_id INT NOT NULL,
    sku VARCHAR(60) NOT NULL,
    nome VARCHAR(160) NOT NULL,
    categoria VARCHAR(100),
    preco_unitario DECIMAL(10, 2) NOT NULL DEFAULT 0,
    quantidade INT NOT NULL DEFAULT 0,
    estoque_minimo INT NOT NULL DEFAULT 5,
    prazo_entrega_dias INT NOT NULL DEFAULT 2,
    ativo TINYINT(1) NOT NULL DEFAULT 1,
    criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_produtos_fornecedor
        FOREIGN KEY (fornecedor_id) REFERENCES fornecedores(id),
    UNIQUE KEY uq_produtos_fornecedor_sku (fornecedor_id, sku),
    KEY idx_produtos_nome (nome),
    KEY idx_produtos_estoque (quantidade, estoque_minimo)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS pedidos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    lojista_id INT NOT NULL,
    fornecedor_id INT NOT NULL,
    status ENUM('pendente', 'confirmado', 'despachado', 'entregue', 'cancelado')
        NOT NULL DEFAULT 'pendente',
    observacoes TEXT,
    valor_total DECIMAL(12, 2) NOT NULL DEFAULT 0,
    endereco_entrega VARCHAR(220),
    criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_pedidos_lojista FOREIGN KEY (lojista_id) REFERENCES lojistas(id),
    CONSTRAINT fk_pedidos_fornecedor FOREIGN KEY (fornecedor_id) REFERENCES fornecedores(id),
    KEY idx_pedidos_status_criado (status, criado_em),
    KEY idx_pedidos_lojista (lojista_id),
    KEY idx_pedidos_fornecedor (fornecedor_id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS itens_pedido (
    id INT AUTO_INCREMENT PRIMARY KEY,
    pedido_id INT NOT NULL,
    produto_id INT NOT NULL,
    quantidade INT NOT NULL,
    preco_unitario DECIMAL(10, 2) NOT NULL,
    subtotal DECIMAL(12, 2) NOT NULL,
    CONSTRAINT fk_itens_pedido_pedido
        FOREIGN KEY (pedido_id) REFERENCES pedidos(id) ON DELETE CASCADE,
    CONSTRAINT fk_itens_pedido_produto
        FOREIGN KEY (produto_id) REFERENCES produtos(id),
    KEY idx_itens_pedido_produto (produto_id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS movimentacoes_estoque (
    id INT AUTO_INCREMENT PRIMARY KEY,
    produto_id INT NOT NULL,
    fornecedor_id INT NOT NULL,
    tipo_movimentacao ENUM('entrada', 'saida', 'ajuste') NOT NULL,
    variacao_quantidade INT NOT NULL,
    motivo VARCHAR(180),
    referencia_tipo VARCHAR(40),
    referencia_id INT,
    criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_movimentacoes_produto
        FOREIGN KEY (produto_id) REFERENCES produtos(id),
    CONSTRAINT fk_movimentacoes_fornecedor
        FOREIGN KEY (fornecedor_id) REFERENCES fornecedores(id),
    KEY idx_movimentacoes_criado (criado_em),
    KEY idx_movimentacoes_produto (produto_id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS rotas_entrega (
    id INT AUTO_INCREMENT PRIMARY KEY,
    fornecedor_id INT NOT NULL,
    data_rota DATE NOT NULL,
    status ENUM('planejada', 'em_andamento', 'concluida', 'cancelada')
        NOT NULL DEFAULT 'planejada',
    distancia_total_km DECIMAL(10, 2) NOT NULL DEFAULT 0,
    observacoes TEXT,
    criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_rotas_fornecedor
        FOREIGN KEY (fornecedor_id) REFERENCES fornecedores(id),
    KEY idx_rotas_data (data_rota, status)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS paradas_rota (
    id INT AUTO_INCREMENT PRIMARY KEY,
    rota_id INT NOT NULL,
    pedido_id INT NOT NULL,
    lojista_id INT NOT NULL,
    ordem_parada INT NOT NULL,
    distancia_anterior_km DECIMAL(10, 2),
    status ENUM('planejada', 'concluida', 'ignorada') NOT NULL DEFAULT 'planejada',
    criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_paradas_rota
        FOREIGN KEY (rota_id) REFERENCES rotas_entrega(id) ON DELETE CASCADE,
    CONSTRAINT fk_paradas_pedido FOREIGN KEY (pedido_id) REFERENCES pedidos(id),
    CONSTRAINT fk_paradas_lojista FOREIGN KEY (lojista_id) REFERENCES lojistas(id),
    UNIQUE KEY uq_paradas_rota_ordem (rota_id, ordem_parada)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------------
-- Dados de exemplo. INSERT IGNORE mantem o script reexecutavel.
-- ---------------------------------------------------------------------------

INSERT IGNORE INTO fornecedores
    (id, nome, cnpj, nome_contato, email, telefone, endereco, cidade, estado, latitude, longitude)
VALUES
    (1, 'Distribuidora Minas Norte', '12.345.678/0001-90', 'Carla Menezes',
     'contato@minasnorte.com.br', '(31) 3222-1010',
     'Av. Cristiano Machado, 1500', 'Belo Horizonte', 'MG', -19.8570000, -43.9350000),
    (2, 'Atacado Sul Suprimentos', '98.765.432/0001-10', 'Rogerio Alves',
     'vendas@sulsuprimentos.com.br', '(31) 3444-2020',
     'Rua Sao Paulo, 320', 'Contagem', 'MG', -19.9320000, -44.0540000);

INSERT IGNORE INTO lojistas
    (id, nome, cnpj, nome_contato, email, telefone, endereco, cidade, estado, latitude, longitude)
VALUES
    (1, 'Mercado Bom Preco', '11.222.333/0001-44', 'Juliana Rocha',
     'compras@bompreco.com.br', '(31) 3555-3030',
     'Rua da Bahia, 900', 'Belo Horizonte', 'MG', -19.9230000, -43.9380000),
    (2, 'Emporio Vila Nova', '55.666.777/0001-88', 'Marcos Diniz',
     'marcos@emporiovilanova.com.br', '(31) 3666-4040',
     'Av. Amazonas, 210', 'Betim', 'MG', -19.9680000, -44.1980000);

INSERT IGNORE INTO produtos
    (id, fornecedor_id, sku, nome, categoria, preco_unitario, quantidade, estoque_minimo, prazo_entrega_dias, ativo)
VALUES
    (1, 1, 'ARZ-5KG', 'Arroz tipo 1 - 5kg', 'Alimentos', 28.90, 120, 20, 2, 1),
    (2, 1, 'FJO-1KG', 'Feijao carioca - 1kg', 'Alimentos', 9.75, 8, 15, 2, 1),
    (3, 2, 'DTG-500', 'Detergente neutro 500ml', 'Limpeza', 3.40, 0, 10, 3, 1);

-- ---------------------------------------------------------------------------
-- Procedures. Todo acesso que vai alem do CRUD basico passa por aqui e e
-- chamado exclusivamente pela camada Repository.
-- ---------------------------------------------------------------------------

DROP PROCEDURE IF EXISTS sp_produtos_com_status;
DROP PROCEDURE IF EXISTS sp_alertas_estoque_baixo;
DROP PROCEDURE IF EXISTS sp_relatorio_resumo;
DROP PROCEDURE IF EXISTS sp_relatorio_top_produtos;
DROP PROCEDURE IF EXISTS sp_relatorio_desempenho_fornecedores;
DROP PROCEDURE IF EXISTS sp_pedidos_filtrados;
DROP PROCEDURE IF EXISTS sp_pedido_detalhe;
DROP PROCEDURE IF EXISTS sp_pedido_itens;
DROP PROCEDURE IF EXISTS sp_pedidos_para_roteirizar;
DROP PROCEDURE IF EXISTS sp_rotas_listar;
DROP PROCEDURE IF EXISTS sp_rota_paradas;
DROP PROCEDURE IF EXISTS sp_historico_movimentacoes;

DELIMITER //

CREATE PROCEDURE sp_produtos_com_status(
    IN p_fornecedor_id INT,
    IN p_busca VARCHAR(160)
)
BEGIN
    SELECT p.id, p.fornecedor_id, p.sku, p.nome, p.categoria, p.preco_unitario,
           p.quantidade, p.estoque_minimo, p.prazo_entrega_dias, p.ativo,
           p.criado_em, p.atualizado_em,
           f.nome AS fornecedor_nome,
           CASE
               WHEN p.quantidade <= 0 THEN 'indisponivel'
               WHEN p.quantidade <= p.estoque_minimo THEN 'baixo'
               ELSE 'disponivel'
           END AS status_estoque
      FROM produtos p
      INNER JOIN fornecedores f ON f.id = p.fornecedor_id
     WHERE p.ativo = 1
       AND (p_fornecedor_id IS NULL OR p.fornecedor_id = p_fornecedor_id)
       AND (p_busca IS NULL OR p_busca = ''
            OR p.nome LIKE CONCAT('%', p_busca, '%')
            OR p.sku LIKE CONCAT('%', p_busca, '%')
            OR p.categoria LIKE CONCAT('%', p_busca, '%'))
     ORDER BY p.nome;
END //

CREATE PROCEDURE sp_alertas_estoque_baixo()
BEGIN
    SELECT p.id AS produto_id, p.sku, p.nome AS produto_nome, p.quantidade,
           p.estoque_minimo, p.preco_unitario,
           f.id AS fornecedor_id, f.nome AS fornecedor_nome,
           CASE WHEN p.quantidade <= 0 THEN 'indisponivel' ELSE 'baixo' END AS severidade
      FROM produtos p
      INNER JOIN fornecedores f ON f.id = p.fornecedor_id
     WHERE p.ativo = 1
       AND p.quantidade <= p.estoque_minimo
     ORDER BY CASE WHEN p.quantidade <= 0 THEN 0 ELSE 1 END,
              p.quantidade ASC,
              p.nome ASC;
END //

CREATE PROCEDURE sp_relatorio_resumo(
    IN p_data_inicio DATE,
    IN p_data_fim DATE
)
BEGIN
    SELECT
        (SELECT COUNT(*) FROM fornecedores) AS fornecedores,
        (SELECT COUNT(*) FROM lojistas) AS lojistas,
        (SELECT COUNT(*) FROM produtos WHERE ativo = 1) AS produtos,
        (SELECT COALESCE(SUM(quantidade), 0) FROM produtos WHERE ativo = 1) AS unidades_estoque,
        (SELECT COUNT(*) FROM produtos WHERE ativo = 1 AND quantidade <= 0) AS produtos_indisponiveis,
        (SELECT COUNT(*) FROM produtos
          WHERE ativo = 1 AND quantidade > 0 AND quantidade <= estoque_minimo) AS produtos_estoque_baixo,
        (SELECT COUNT(*) FROM pedidos
          WHERE status IN ('pendente', 'confirmado', 'despachado')) AS pedidos_abertos,
        (SELECT COUNT(*) FROM pedidos
          WHERE DATE(criado_em) BETWEEN p_data_inicio AND p_data_fim) AS pedidos_periodo,
        (SELECT COALESCE(SUM(valor_total), 0) FROM pedidos
          WHERE DATE(criado_em) BETWEEN p_data_inicio AND p_data_fim
            AND status <> 'cancelado') AS faturamento_periodo;
END //

CREATE PROCEDURE sp_relatorio_top_produtos(
    IN p_data_inicio DATE,
    IN p_data_fim DATE
)
BEGIN
    SELECT p.id AS produto_id, p.nome, f.nome AS fornecedor_nome,
           SUM(ip.quantidade) AS demanda,
           SUM(ip.subtotal) AS total
      FROM itens_pedido ip
      INNER JOIN pedidos pe ON pe.id = ip.pedido_id
      INNER JOIN produtos p ON p.id = ip.produto_id
      INNER JOIN fornecedores f ON f.id = p.fornecedor_id
     WHERE pe.status <> 'cancelado'
       AND DATE(pe.criado_em) BETWEEN p_data_inicio AND p_data_fim
     GROUP BY p.id, p.nome, f.nome
     ORDER BY demanda DESC
     LIMIT 5;
END //

CREATE PROCEDURE sp_relatorio_desempenho_fornecedores(
    IN p_data_inicio DATE,
    IN p_data_fim DATE
)
BEGIN
    SELECT f.id AS fornecedor_id, f.nome,
           COUNT(pe.id) AS total_pedidos,
           COALESCE(SUM(CASE WHEN pe.status <> 'cancelado' THEN pe.valor_total ELSE 0 END), 0) AS total
      FROM fornecedores f
      LEFT JOIN pedidos pe
             ON pe.fornecedor_id = f.id
            AND DATE(pe.criado_em) BETWEEN p_data_inicio AND p_data_fim
     GROUP BY f.id, f.nome
     ORDER BY total DESC, total_pedidos DESC
     LIMIT 5;
END //

CREATE PROCEDURE sp_pedidos_filtrados(
    IN p_status VARCHAR(20),
    IN p_lojista_id INT,
    IN p_data_inicio DATE,
    IN p_data_fim DATE
)
BEGIN
    SELECT pe.id, pe.lojista_id, pe.fornecedor_id, pe.status, pe.observacoes,
           pe.valor_total, pe.endereco_entrega, pe.criado_em, pe.atualizado_em,
           l.nome AS lojista_nome, f.nome AS fornecedor_nome,
           COUNT(ip.id) AS total_itens
      FROM pedidos pe
      INNER JOIN lojistas l ON l.id = pe.lojista_id
      INNER JOIN fornecedores f ON f.id = pe.fornecedor_id
      LEFT JOIN itens_pedido ip ON ip.pedido_id = pe.id
     WHERE (p_status IS NULL OR p_status = '' OR pe.status = p_status)
       AND (p_lojista_id IS NULL OR pe.lojista_id = p_lojista_id)
       AND (p_data_inicio IS NULL OR DATE(pe.criado_em) >= p_data_inicio)
       AND (p_data_fim IS NULL OR DATE(pe.criado_em) <= p_data_fim)
     GROUP BY pe.id, pe.lojista_id, pe.fornecedor_id, pe.status, pe.observacoes,
              pe.valor_total, pe.endereco_entrega, pe.criado_em, pe.atualizado_em,
              l.nome, f.nome
     ORDER BY pe.criado_em DESC;
END //

CREATE PROCEDURE sp_pedido_detalhe(
    IN p_pedido_id INT
)
BEGIN
    SELECT pe.id, pe.lojista_id, pe.fornecedor_id, pe.status, pe.observacoes,
           pe.valor_total, pe.endereco_entrega, pe.criado_em, pe.atualizado_em,
           l.nome AS lojista_nome, f.nome AS fornecedor_nome
      FROM pedidos pe
      INNER JOIN lojistas l ON l.id = pe.lojista_id
      INNER JOIN fornecedores f ON f.id = pe.fornecedor_id
     WHERE pe.id = p_pedido_id;
END //

CREATE PROCEDURE sp_pedido_itens(
    IN p_pedido_id INT
)
BEGIN
    SELECT ip.id, ip.pedido_id, ip.produto_id, ip.quantidade,
           ip.preco_unitario, ip.subtotal,
           p.nome AS produto_nome, p.sku
      FROM itens_pedido ip
      INNER JOIN produtos p ON p.id = ip.produto_id
     WHERE ip.pedido_id = p_pedido_id
     ORDER BY ip.id;
END //

CREATE PROCEDURE sp_pedidos_para_roteirizar(
    IN p_fornecedor_id INT
)
BEGIN
    SELECT pe.id AS pedido_id, pe.endereco_entrega, pe.valor_total,
           l.id AS lojista_id, l.nome AS lojista_nome, l.cidade,
           l.latitude, l.longitude
      FROM pedidos pe
      INNER JOIN lojistas l ON l.id = pe.lojista_id
     WHERE pe.fornecedor_id = p_fornecedor_id
       AND pe.status IN ('confirmado', 'despachado')
     ORDER BY pe.criado_em ASC;
END //

CREATE PROCEDURE sp_rotas_listar()
BEGIN
    SELECT r.id, r.fornecedor_id, r.data_rota, r.status, r.distancia_total_km,
           r.observacoes, r.criado_em,
           f.nome AS fornecedor_nome,
           COUNT(pr.id) AS total_paradas
      FROM rotas_entrega r
      INNER JOIN fornecedores f ON f.id = r.fornecedor_id
      LEFT JOIN paradas_rota pr ON pr.rota_id = r.id
     GROUP BY r.id, r.fornecedor_id, r.data_rota, r.status, r.distancia_total_km,
              r.observacoes, r.criado_em, f.nome
     ORDER BY r.criado_em DESC;
END //

CREATE PROCEDURE sp_rota_paradas(
    IN p_rota_id INT
)
BEGIN
    SELECT pr.id, pr.rota_id, pr.pedido_id, pr.lojista_id, pr.ordem_parada,
           pr.distancia_anterior_km, pr.status,
           l.nome AS lojista_nome, l.endereco, l.cidade, l.estado
      FROM paradas_rota pr
      INNER JOIN lojistas l ON l.id = pr.lojista_id
     WHERE pr.rota_id = p_rota_id
     ORDER BY pr.ordem_parada;
END //

CREATE PROCEDURE sp_historico_movimentacoes(
    IN p_produto_id INT,
    IN p_fornecedor_id INT,
    IN p_data_inicio DATE,
    IN p_data_fim DATE
)
BEGIN
    SELECT m.id, m.produto_id, m.fornecedor_id, m.tipo_movimentacao,
           m.variacao_quantidade, m.motivo, m.referencia_tipo, m.referencia_id,
           m.criado_em,
           p.nome AS produto_nome, p.sku,
           f.nome AS fornecedor_nome
      FROM movimentacoes_estoque m
      INNER JOIN produtos p ON p.id = m.produto_id
      INNER JOIN fornecedores f ON f.id = m.fornecedor_id
     WHERE (p_produto_id IS NULL OR m.produto_id = p_produto_id)
       AND (p_fornecedor_id IS NULL OR m.fornecedor_id = p_fornecedor_id)
       AND (p_data_inicio IS NULL OR DATE(m.criado_em) >= p_data_inicio)
       AND (p_data_fim IS NULL OR DATE(m.criado_em) <= p_data_fim)
     ORDER BY m.criado_em DESC, m.id DESC;
END //

DELIMITER ;
