-- QuiverQuant paper trading schema
CREATE TABLE IF NOT EXISTS qq_email_ingests (
    id INT AUTO_INCREMENT PRIMARY KEY,
    gmail_id VARCHAR(255) UNIQUE,
    thread_id VARCHAR(255),
    subject VARCHAR(255),
    sender VARCHAR(255),
    received_at DATETIME,
    snippet TEXT,
    html MEDIUMTEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS qq_strategies (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) UNIQUE,
    capital_usd DECIMAL(18,2) DEFAULT 0,
    price_fill ENUM('next_open','close') DEFAULT 'next_open',
    allow_fractional TINYINT(1) DEFAULT 1,
    rounding_mode ENUM('floor','round','ceil') DEFAULT 'floor',
    target_sum_tolerance_pct DECIMAL(6,4) DEFAULT 0.0100,
    active TINYINT(1) DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS qq_rebalances (
    id INT AUTO_INCREMENT PRIMARY KEY,
    strategy_id INT NOT NULL,
    rebalance_date DATE NOT NULL,
    status ENUM('pending','processed','skipped') DEFAULT 'pending',
    note TEXT,
    email_ingest_id INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(strategy_id, rebalance_date),
    FOREIGN KEY (strategy_id) REFERENCES qq_strategies(id),
    FOREIGN KEY (email_ingest_id) REFERENCES qq_email_ingests(id)
);

CREATE TABLE IF NOT EXISTS qq_allocations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    rebalance_id INT NOT NULL,
    ticker VARCHAR(16) NOT NULL,
    target_weight DECIMAL(10,6) NOT NULL,
    current_weight DECIMAL(10,6),
    transaction ENUM('Open Trade','Rebalance','Close Trade'),
    rebalance_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (rebalance_id) REFERENCES qq_rebalances(id)
);

CREATE TABLE IF NOT EXISTS price_daily (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ticker VARCHAR(16) NOT NULL,
    price_date DATE NOT NULL,
    open DECIMAL(18,4),
    close DECIMAL(18,4),
    UNIQUE(ticker, price_date)
);

CREATE TABLE IF NOT EXISTS qq_trades (
    id INT AUTO_INCREMENT PRIMARY KEY,
    strategy_id INT NOT NULL,
    ticker VARCHAR(16) NOT NULL,
    trade_date DATE NOT NULL,
    action ENUM('BUY','SELL') NOT NULL,
    quantity DECIMAL(20,8) NOT NULL,
    price DECIMAL(18,4) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS qq_positions_daily (
    id INT AUTO_INCREMENT PRIMARY KEY,
    strategy_id INT NOT NULL,
    ticker VARCHAR(16) NOT NULL,
    position_date DATE NOT NULL,
    quantity DECIMAL(20,8) NOT NULL,
    price DECIMAL(18,4) NOT NULL,
    UNIQUE(strategy_id, ticker, position_date)
);

CREATE TABLE IF NOT EXISTS qq_nav_daily (
    id INT AUTO_INCREMENT PRIMARY KEY,
    strategy_id INT NOT NULL,
    nav_date DATE NOT NULL,
    nav DECIMAL(18,4) NOT NULL,
    cash DECIMAL(18,4) NOT NULL,
    UNIQUE(strategy_id, nav_date)
);
