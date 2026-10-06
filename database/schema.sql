-- ============================================================
-- RetailTwin AI — Database Schema
-- Database: RetailTwin_AI
-- MySQL 8.x
-- ============================================================

-- Create and select database
CREATE DATABASE IF NOT EXISTS RetailTwin_AI
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE RetailTwin_AI;

-- ============================================================
-- TABLE: USER
-- ============================================================
CREATE TABLE IF NOT EXISTS USER (
    user_id       INT           NOT NULL AUTO_INCREMENT,
    name          VARCHAR(100)  NOT NULL,
    email         VARCHAR(100)  NOT NULL,
    password_hash VARCHAR(255)  NOT NULL,
    phone         VARCHAR(15),
    role          ENUM('ADMIN', 'STORE_MANAGER') NOT NULL DEFAULT 'STORE_MANAGER',
    created_at    DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id),
    UNIQUE KEY uq_user_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- TABLE: STORE
-- ============================================================
CREATE TABLE IF NOT EXISTS STORE (
    store_id      INT          NOT NULL AUTO_INCREMENT,
    store_name    VARCHAR(100) NOT NULL,
    location      VARCHAR(150),
    manager_name  VARCHAR(100),
    contact       VARCHAR(15),
    created_at    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (store_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- TABLE: CATEGORY
-- ============================================================
CREATE TABLE IF NOT EXISTS CATEGORY (
    category_id   INT          NOT NULL AUTO_INCREMENT,
    category_name VARCHAR(100) NOT NULL,
    description   TEXT,
    created_date  DATE         NOT NULL DEFAULT (CURRENT_DATE),
    PRIMARY KEY (category_id),
    UNIQUE KEY uq_category_name (category_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- TABLE: PRODUCT
-- ============================================================
CREATE TABLE IF NOT EXISTS PRODUCT (
    product_id    INT            NOT NULL AUTO_INCREMENT,
    product_name  VARCHAR(100)   NOT NULL,
    category_id   INT            NOT NULL,
    cost_price    DECIMAL(10,2)  NOT NULL,
    selling_price DECIMAL(10,2)  NOT NULL,
    lead_time     INT            NOT NULL DEFAULT 1 COMMENT 'Days to restock',
    expiry_days   INT            NOT NULL DEFAULT 365 COMMENT 'Shelf life in days',
    created_at    DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (product_id),
    CONSTRAINT fk_product_category
        FOREIGN KEY (category_id) REFERENCES CATEGORY(category_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- TABLE: INVENTORY
-- ============================================================
CREATE TABLE IF NOT EXISTS INVENTORY (
    inventory_id  INT      NOT NULL AUTO_INCREMENT,
    product_id    INT      NOT NULL,
    store_id      INT      NOT NULL,
    current_stock INT      NOT NULL DEFAULT 0,
    minimum_stock INT      NOT NULL DEFAULT 0,
    maximum_stock INT      NOT NULL DEFAULT 1000,
    reorder_level INT      NOT NULL DEFAULT 10,
    last_updated  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (inventory_id),
    UNIQUE KEY uq_inventory_product_store (product_id, store_id),
    CONSTRAINT fk_inventory_product
        FOREIGN KEY (product_id) REFERENCES PRODUCT(product_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    CONSTRAINT fk_inventory_store
        FOREIGN KEY (store_id) REFERENCES STORE(store_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- TABLE: SALES
-- Cascade delete is intentionally NOT used — preserve history
-- ============================================================
CREATE TABLE IF NOT EXISTS SALES (
    sale_id        INT            NOT NULL AUTO_INCREMENT,
    product_id     INT            NOT NULL,
    store_id       INT            NOT NULL,
    sale_date      DATE           NOT NULL,
    quantity_sold  INT            NOT NULL,
    cost_price     DECIMAL(10,2)  NOT NULL,
    selling_price  DECIMAL(10,2)  NOT NULL,
    discount       DECIMAL(5,2)   NOT NULL DEFAULT 0.00,
    revenue        DECIMAL(12,2)  NOT NULL,
    created_at     DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (sale_id),
    CONSTRAINT fk_sales_product
        FOREIGN KEY (product_id) REFERENCES PRODUCT(product_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    CONSTRAINT fk_sales_store
        FOREIGN KEY (store_id) REFERENCES STORE(store_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    INDEX idx_sales_date (sale_date),
    INDEX idx_sales_product_store (product_id, store_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- TABLE: DEMAND_FORECAST
-- ============================================================
CREATE TABLE IF NOT EXISTS DEMAND_FORECAST (
    forecast_id      INT            NOT NULL AUTO_INCREMENT,
    product_id       INT            NOT NULL,
    store_id         INT            NOT NULL,
    forecast_date    DATE           NOT NULL,
    predicted_demand DECIMAL(10,2)  NOT NULL,
    confidence_score DECIMAL(5,2)   NOT NULL DEFAULT 0.00
                         COMMENT 'Model quality score: max(0, R2*100)',
    model_name       VARCHAR(100)   NOT NULL DEFAULT 'RandomForestRegressor',
    created_at       DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (forecast_id),
    CONSTRAINT fk_forecast_product
        FOREIGN KEY (product_id) REFERENCES PRODUCT(product_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    CONSTRAINT fk_forecast_store
        FOREIGN KEY (store_id) REFERENCES STORE(store_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    INDEX idx_forecast_date (forecast_date),
    INDEX idx_forecast_product_store (product_id, store_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- TABLE: PRICING_STRATEGY (optional module)
-- ============================================================
CREATE TABLE IF NOT EXISTS PRICING_STRATEGY (
    pricing_id          INT            NOT NULL AUTO_INCREMENT,
    product_id          INT            NOT NULL,
    original_price      DECIMAL(10,2)  NOT NULL,
    suggested_price     DECIMAL(10,2)  NOT NULL,
    discount_percentage DECIMAL(5,2)   NOT NULL DEFAULT 0.00,
    effective_date      DATE           NOT NULL,
    created_at          DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (pricing_id),
    CONSTRAINT fk_pricing_product
        FOREIGN KEY (product_id) REFERENCES PRODUCT(product_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- TABLE: DIGITAL_TWIN_SIMULATION
-- ============================================================
CREATE TABLE IF NOT EXISTS DIGITAL_TWIN_SIMULATION (
    simulation_id    INT            NOT NULL AUTO_INCREMENT,
    store_id         INT            NOT NULL,
    product_id       INT            NOT NULL,
    scenario_name    VARCHAR(100)   NOT NULL,
    simulation_date  DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    starting_stock   INT            NOT NULL,
    simulated_stock  INT            NOT NULL,
    expected_sales   DECIMAL(10,2)  NOT NULL DEFAULT 0.00,
    expected_revenue DECIMAL(12,2)  NOT NULL DEFAULT 0.00,
    expected_profit  DECIMAL(12,2)  NOT NULL DEFAULT 0.00,
    expected_loss    DECIMAL(12,2)  NOT NULL DEFAULT 0.00,
    expected_stockout INT           NOT NULL DEFAULT 0,
    expected_overstock INT          NOT NULL DEFAULT 0,
    recommendation   TEXT,
    PRIMARY KEY (simulation_id),
    CONSTRAINT fk_simulation_store
        FOREIGN KEY (store_id) REFERENCES STORE(store_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    CONSTRAINT fk_simulation_product
        FOREIGN KEY (product_id) REFERENCES PRODUCT(product_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    INDEX idx_simulation_date (simulation_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- TABLE: CUSTOMER_FLOW (optional/secondary module)
-- ============================================================
CREATE TABLE IF NOT EXISTS CUSTOMER_FLOW (
    flow_id         INT           NOT NULL AUTO_INCREMENT,
    store_id        INT           NOT NULL,
    date            DATE          NOT NULL,
    customer_count  INT           NOT NULL DEFAULT 0,
    peak_hour       VARCHAR(20),
    avg_dwell_time  DECIMAL(6,2)  NOT NULL DEFAULT 0.00
                        COMMENT 'Average time spent in store (minutes)',
    PRIMARY KEY (flow_id),
    CONSTRAINT fk_flow_store
        FOREIGN KEY (store_id) REFERENCES STORE(store_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    UNIQUE KEY uq_flow_store_date (store_id, date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
