CREATE DATABASE IF NOT EXISTS stock_map
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE stock_map;

CREATE TABLE IF NOT EXISTS suppliers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(140) NOT NULL,
    cnpj VARCHAR(24),
    contact_name VARCHAR(120) NOT NULL,
    email VARCHAR(180) NOT NULL,
    phone VARCHAR(40),
    address VARCHAR(220),
    city VARCHAR(100),
    state VARCHAR(40),
    latitude DECIMAL(10, 7),
    longitude DECIMAL(10, 7),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_suppliers_email (email)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS retailers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(140) NOT NULL,
    cnpj VARCHAR(24),
    contact_name VARCHAR(120) NOT NULL,
    email VARCHAR(180) NOT NULL,
    phone VARCHAR(40),
    address VARCHAR(220),
    city VARCHAR(100),
    state VARCHAR(40),
    latitude DECIMAL(10, 7),
    longitude DECIMAL(10, 7),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_retailers_email (email)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS products (
    id INT AUTO_INCREMENT PRIMARY KEY,
    supplier_id INT NOT NULL,
    sku VARCHAR(60) NOT NULL,
    name VARCHAR(160) NOT NULL,
    category VARCHAR(100),
    unit_price DECIMAL(10, 2) NOT NULL DEFAULT 0,
    quantity INT NOT NULL DEFAULT 0,
    min_stock INT NOT NULL DEFAULT 5,
    lead_time_days INT NOT NULL DEFAULT 2,
    active TINYINT(1) NOT NULL DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_products_supplier
        FOREIGN KEY (supplier_id) REFERENCES suppliers(id)
        ON DELETE CASCADE,
    UNIQUE KEY uq_products_supplier_sku (supplier_id, sku),
    KEY idx_products_name (name),
    KEY idx_products_stock (quantity, min_stock)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS orders (
    id INT AUTO_INCREMENT PRIMARY KEY,
    retailer_id INT NOT NULL,
    supplier_id INT NOT NULL,
    status ENUM('pending', 'confirmed', 'dispatched', 'delivered', 'cancelled') NOT NULL DEFAULT 'pending',
    notes TEXT,
    total_amount DECIMAL(12, 2) NOT NULL DEFAULT 0,
    delivery_address VARCHAR(220),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_orders_retailer
        FOREIGN KEY (retailer_id) REFERENCES retailers(id),
    CONSTRAINT fk_orders_supplier
        FOREIGN KEY (supplier_id) REFERENCES suppliers(id),
    KEY idx_orders_status_created (status, created_at),
    KEY idx_orders_supplier (supplier_id),
    KEY idx_orders_retailer (retailer_id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS order_items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    order_id INT NOT NULL,
    product_id INT NOT NULL,
    quantity INT NOT NULL,
    unit_price DECIMAL(10, 2) NOT NULL,
    subtotal DECIMAL(12, 2) NOT NULL,
    CONSTRAINT fk_order_items_order
        FOREIGN KEY (order_id) REFERENCES orders(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_order_items_product
        FOREIGN KEY (product_id) REFERENCES products(id),
    KEY idx_order_items_product (product_id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS stock_movements (
    id INT AUTO_INCREMENT PRIMARY KEY,
    product_id INT NOT NULL,
    supplier_id INT NOT NULL,
    movement_type ENUM('entry', 'exit', 'adjustment') NOT NULL,
    quantity_change INT NOT NULL,
    reason VARCHAR(180),
    reference_type VARCHAR(40),
    reference_id INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_stock_movements_product
        FOREIGN KEY (product_id) REFERENCES products(id),
    CONSTRAINT fk_stock_movements_supplier
        FOREIGN KEY (supplier_id) REFERENCES suppliers(id),
    KEY idx_stock_movements_created (created_at)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS delivery_routes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    supplier_id INT NOT NULL,
    route_date DATE NOT NULL,
    status ENUM('planned', 'in_progress', 'completed', 'cancelled') NOT NULL DEFAULT 'planned',
    total_distance_km DECIMAL(10, 2) NOT NULL DEFAULT 0,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_delivery_routes_supplier
        FOREIGN KEY (supplier_id) REFERENCES suppliers(id),
    KEY idx_delivery_routes_date (route_date, status)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS route_stops (
    id INT AUTO_INCREMENT PRIMARY KEY,
    route_id INT NOT NULL,
    order_id INT NOT NULL,
    retailer_id INT NOT NULL,
    stop_order INT NOT NULL,
    distance_from_previous_km DECIMAL(10, 2),
    status ENUM('planned', 'completed', 'skipped') NOT NULL DEFAULT 'planned',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_route_stops_route
        FOREIGN KEY (route_id) REFERENCES delivery_routes(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_route_stops_order
        FOREIGN KEY (order_id) REFERENCES orders(id),
    CONSTRAINT fk_route_stops_retailer
        FOREIGN KEY (retailer_id) REFERENCES retailers(id),
    UNIQUE KEY uq_route_stop_order (route_id, stop_order)
) ENGINE=InnoDB;
