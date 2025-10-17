DROP DATABASE IF EXISTS storefront;
CREATE DATABASE storefront
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;
USE storefront;

SET FOREIGN_KEY_CHECKS = 0;

/* ------------------------------------------------------------------- */
/* 1. Reference tables */
/* ------------------------------------------------------------------- */
CREATE TABLE Address (
  address_id     INT AUTO_INCREMENT PRIMARY KEY,
  street_address VARCHAR(255) NOT NULL,
  city           VARCHAR(100) NOT NULL,
  state          VARCHAR(50)  NOT NULL,
  postal_code    VARCHAR(20)  NOT NULL,
  country        VARCHAR(50)  DEFAULT 'PAL',
  created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE User (
  user_id    INT AUTO_INCREMENT PRIMARY KEY,
  email      VARCHAR(100) UNIQUE NOT NULL,
  password   VARCHAR(255)        NOT NULL,
  name       VARCHAR(100)        NOT NULL,
  role       ENUM('owner','manager','employee','customer') NOT NULL,
  city       VARCHAR(100),
  address_id INT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  last_login TIMESTAMP NULL,
  FOREIGN KEY (address_id) REFERENCES Address(address_id)
    ON DELETE SET NULL ON UPDATE CASCADE
);

/* ------------------------------------------------------------------- */
/* 2. Warehouses & initial Roles tables */
/* ------------------------------------------------------------------- */
CREATE TABLE Warehouse (
  warehouse_id INT AUTO_INCREMENT PRIMARY KEY,
  name         VARCHAR(100) NOT NULL,
  address_id   INT NOT NULL,
  capacity     INT NOT NULL,
  created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (address_id) REFERENCES Address(address_id)
    ON DELETE CASCADE ON UPDATE CASCADE
);


CREATE TABLE Manager (
  manager_id   INT AUTO_INCREMENT PRIMARY KEY,
  user_id      INT NOT NULL,
  warehouse_id INT,
  branch_id    INT NULL,                
  phone        VARCHAR(20),
  created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id)      REFERENCES User(user_id)
    ON DELETE CASCADE ON UPDATE CASCADE,
  FOREIGN KEY (warehouse_id) REFERENCES Warehouse(warehouse_id)
    ON DELETE SET NULL ON UPDATE CASCADE
);

/* 2B. Branch */
CREATE TABLE Branch (
  branch_id    INT AUTO_INCREMENT PRIMARY KEY,
  name         VARCHAR(100) NOT NULL,
  address_id   INT NOT NULL,
  warehouse_id INT,
  manager_id   INT,
  created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (address_id)   REFERENCES Address(address_id)
    ON DELETE CASCADE ON UPDATE CASCADE,
  FOREIGN KEY (warehouse_id) REFERENCES Warehouse(warehouse_id)
    ON DELETE SET NULL ON UPDATE CASCADE,
  FOREIGN KEY (manager_id)   REFERENCES Manager(manager_id)
    ON DELETE SET NULL ON UPDATE CASCADE
);


ALTER TABLE Manager
  ADD CONSTRAINT fk_manager_branch
  FOREIGN KEY (branch_id) REFERENCES Branch(branch_id)
    ON DELETE SET NULL ON UPDATE CASCADE;

/* ------------------------------------------------------------------- */
/* 3. Products                                                         */
/* ------------------------------------------------------------------- */
CREATE TABLE Product (
  product_id  INT AUTO_INCREMENT PRIMARY KEY,
  name        VARCHAR(100) NOT NULL,
  price       DECIMAL(10,2) NOT NULL,
  cost_price  DECIMAL(10,2) NOT NULL DEFAULT 0.00,
  category    VARCHAR(50),
  description TEXT,
  img_path    VARCHAR(255),
  created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

/* ------------------------------------------------------------------- */
/* 4. Employee tables                                                  */
/* ------------------------------------------------------------------- */
CREATE TABLE Employee (
  employee_id   INT AUTO_INCREMENT PRIMARY KEY,
  user_id       INT UNIQUE,
  warehouse_id  INT NULL,
  phone_number  VARCHAR(20),
  position      VARCHAR(50),
  salary        DECIMAL(10,2),
  hire_date     DATE,
  created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id)      REFERENCES User(user_id)
    ON DELETE CASCADE ON UPDATE CASCADE,
  FOREIGN KEY (warehouse_id) REFERENCES Warehouse(warehouse_id)
    ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE TABLE Employee_Branch (
  employee_id INT,
  branch_id   INT,
  start_date  DATE NOT NULL,
  end_date    DATE,
  PRIMARY KEY (employee_id, branch_id),
  FOREIGN KEY (employee_id) REFERENCES Employee(employee_id)
    ON DELETE CASCADE ON UPDATE CASCADE,
  FOREIGN KEY (branch_id)   REFERENCES Branch(branch_id)
    ON DELETE CASCADE ON UPDATE CASCADE
);

/* ------------------------------------------------------------------- */
/* 5. Customers & orders                                               */
/* ------------------------------------------------------------------- */
CREATE TABLE Customer (
  customer_id INT AUTO_INCREMENT PRIMARY KEY,
  user_id     INT UNIQUE,
  phone       VARCHAR(20),
  created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES User(user_id)
    ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE TABLE `Order` (
  order_id         INT AUTO_INCREMENT PRIMARY KEY,
  customer_id      INT,
  branch_id        INT,
  sale_date        DATETIME DEFAULT CURRENT_TIMESTAMP,
  total_amount     DECIMAL(10,2),
  profit_generated DECIMAL(10,2),
  status           VARCHAR(20) DEFAULT 'completed',
  processed_by     INT,
  FOREIGN KEY (customer_id) REFERENCES Customer(customer_id)
    ON DELETE SET NULL ON UPDATE CASCADE,
  FOREIGN KEY (branch_id)   REFERENCES Branch(branch_id)
    ON DELETE SET NULL ON UPDATE CASCADE,
  FOREIGN KEY (processed_by) REFERENCES User(user_id)
    ON DELETE SET NULL ON UPDATE CASCADE
);

CREATE TABLE Order_Details (
  order_detail_id INT AUTO_INCREMENT PRIMARY KEY,
  order_id        INT,
  product_id      INT,
  quantity_sold   INT           NOT NULL,
  unit_price      DECIMAL(10,2) NOT NULL,
  FOREIGN KEY (order_id)   REFERENCES `Order`(order_id)
    ON DELETE CASCADE ON UPDATE CASCADE,
  FOREIGN KEY (product_id) REFERENCES Product(product_id)
    ON DELETE CASCADE ON UPDATE CASCADE
);

/* ------------------------------------------------------------------- */
/* 6. Stock tables                                                     */
/* ------------------------------------------------------------------- */
CREATE TABLE Product_Warehouse (
  product_id        INT,
  warehouse_id      INT,
  quantity_in_stock INT NOT NULL DEFAULT 0,
  minimum_stock     INT NOT NULL DEFAULT 0,
  maximum_stock     INT NOT NULL DEFAULT 0,
  created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (product_id, warehouse_id),
  FOREIGN KEY (product_id)   REFERENCES Product(product_id)
    ON DELETE CASCADE ON UPDATE CASCADE,
  FOREIGN KEY (warehouse_id) REFERENCES Warehouse(warehouse_id)
    ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE TABLE Product_Branch (
  product_id        INT,
  branch_id         INT,
  quantity_in_stock INT NOT NULL DEFAULT 0,
  minimum_stock     INT NOT NULL DEFAULT 0,
  maximum_stock     INT NOT NULL DEFAULT 0,
  created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (product_id, branch_id),
  FOREIGN KEY (product_id) REFERENCES Product(product_id)
    ON DELETE CASCADE ON UPDATE CASCADE,
  FOREIGN KEY (branch_id)  REFERENCES Branch(branch_id)
    ON DELETE CASCADE ON UPDATE CASCADE
);
/*--Table for debuging and making sure everthing is good--*/
CREATE TABLE Inventory_Log (
  log_id           INT AUTO_INCREMENT PRIMARY KEY,
  product_id       INT,
  branch_id        INT,
  quantity_changed INT,
  changed_by       INT,
  change_type      VARCHAR(30),
  notes            TEXT,
  created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (product_id) REFERENCES Product(product_id)
    ON DELETE SET NULL ON UPDATE CASCADE,
  FOREIGN KEY (branch_id)  REFERENCES Branch(branch_id)
    ON DELETE SET NULL ON UPDATE CASCADE,
  FOREIGN KEY (changed_by) REFERENCES User(user_id)
    ON DELETE SET NULL ON UPDATE CASCADE
);
/*--Table for debuging and making sure everthing is good--*/
CREATE TABLE Stock_Alert (
  alert_id   INT AUTO_INCREMENT PRIMARY KEY,
  product_id INT,
  branch_id  INT,
  alert_type VARCHAR(30),
  message    TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (product_id) REFERENCES Product(product_id)
    ON DELETE CASCADE ON UPDATE CASCADE,
  FOREIGN KEY (branch_id)  REFERENCES Branch(branch_id)
    ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE TABLE Warehouse_Branch_Supply (
  warehouse_id INT,
  branch_id    INT,
  is_primary_supplier BOOLEAN DEFAULT TRUE,
  PRIMARY KEY (warehouse_id, branch_id),
  FOREIGN KEY (warehouse_id) REFERENCES Warehouse(warehouse_id)
    ON DELETE CASCADE ON UPDATE CASCADE,
  FOREIGN KEY (branch_id)    REFERENCES Branch(branch_id)
    ON DELETE CASCADE ON UPDATE CASCADE
);

/* ------------------------------------------------------------------- */
/* 7. Suppliers & purchasing                                           */
/* ------------------------------------------------------------------- */
CREATE TABLE Supplier (
  supplier_id  INT AUTO_INCREMENT PRIMARY KEY,
  name         VARCHAR(100) NOT NULL,
  email        VARCHAR(100),
  phone_number VARCHAR(20),
  address_id   INT,
  created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (address_id) REFERENCES Address(address_id)
    ON DELETE SET NULL ON UPDATE CASCADE
);

CREATE TABLE Purchase_Order (
  purchase_order_id      INT AUTO_INCREMENT PRIMARY KEY,
  warehouse_id           INT NOT NULL,
  supplier_id            INT NOT NULL,
  order_date             TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  expected_delivery_date TIMESTAMP,
  status                 VARCHAR(20) DEFAULT 'pending',
  created_at             TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (warehouse_id) REFERENCES Warehouse(warehouse_id)
    ON DELETE CASCADE ON UPDATE CASCADE,
  FOREIGN KEY (supplier_id)  REFERENCES Supplier(supplier_id)
    ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE TABLE Purchase_Order_Details (
  purchase_order_id INT,
  product_id        INT,
  quantity          INT NOT NULL,
  unit_price        DECIMAL(10,2) NOT NULL,
  created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (purchase_order_id, product_id),
  FOREIGN KEY (purchase_order_id) REFERENCES Purchase_Order(purchase_order_id)
    ON DELETE CASCADE ON UPDATE CASCADE,
  FOREIGN KEY (product_id)        REFERENCES Product(product_id)
    ON DELETE CASCADE ON UPDATE CASCADE
);

SET FOREIGN_KEY_CHECKS = 1;

/*======================================================================
					Random 	DATA 
======================================================================*/

/* Addresses */
INSERT INTO Address (address_id, street_address, city, state, postal_code, country, created_at) VALUES
  (1,'123 Main St','Los Angeles','CA','90001','USA',DEFAULT),
  (2,'456 Oak Ave','Miami','FL','33139','USA',DEFAULT),
  (3,'789 Storage Rd','Dallas','TX','75001','USA',DEFAULT),
  (4,'Al-Irsal Street','Ramallah','West Bank','00970','PAL',DEFAULT),
  (5,'Al-Rasheed St','Gaza City','Gaza Strip','00972','PAL',DEFAULT),
  (6,'Al-Shuhada St','Hebron','West Bank','00970','PAL',DEFAULT),
  (7,'Al-Nasr St','Nablus','West Bank','00970','PAL',DEFAULT),
  (8,'Manger Street','Bethlehem','West Bank','00970','PAL',DEFAULT),
  (9,'Al-Sultan St','Jericho','West Bank','00970','PAL',DEFAULT),
  (10,'Al-Amal St','Khan Yunis','Gaza Strip','00972','PAL',DEFAULT),
  (11,'Al-Nasser St','Rafah','Gaza Strip','00972','PAL',DEFAULT);
select*from warehouse_branch_supply;
INSERT INTO User (user_id, email, password, name, role, city, address_id, created_at, last_login) VALUES
  (1,'john@example.com','password123','John Doe','employee','Los Angeles',1,DEFAULT,CURRENT_TIMESTAMP),
  (2,'jane@example.com','password123','Jane Smith','customer','Miami',2,DEFAULT,CURRENT_TIMESTAMP),
  (3,'manager@example.com','1234','Test Manager','manager','Gaza City',5,DEFAULT,CURRENT_TIMESTAMP),
  (4,'owner@example.com','owner123','Store Owner','owner','Dallas',3,DEFAULT,CURRENT_TIMESTAMP),
  (5,'testcustomer@example.com','test123','Test Customer','customer','Ramallah',4,DEFAULT,CURRENT_TIMESTAMP),
  (6,'testemployee@example.com','test123','Test Employee','employee','Ramallah',4,DEFAULT,CURRENT_TIMESTAMP);
select*from `order`;
/* Warehouses */
INSERT INTO Warehouse (warehouse_id, name, address_id, capacity, created_at) VALUES
  (1,'Main Warehouse',3,1000,DEFAULT),
  (2,'Gaza City Warehouse',5,5000,DEFAULT),
  (3,'Ramallah Distribution Center',4,4000,DEFAULT);

/* Manager */
INSERT INTO Manager (manager_id, user_id, warehouse_id, branch_id, phone, created_at) VALUES
  (1,3,2,null,'+970590123456',DEFAULT);

/* Branches */
INSERT INTO Branch (branch_id, name, address_id, warehouse_id, manager_id, created_at) VALUES
  (1,'Downtown Branch',1,1,1,DEFAULT),
  (2,'Uptown Branch',2,1,1,DEFAULT),
  (3,'Ramallah Branch',4,3,1,DEFAULT);

/* Update Manager.branch_id now that branches exist */
UPDATE Manager SET branch_id = 1 WHERE manager_id = 1;

/* Employees */
INSERT INTO Employee (employee_id, user_id, warehouse_id, phone_number, position, salary, hire_date, created_at) VALUES
  (1,1,1,'+1234567890','Warehouse Lead',50000.00,'2023-01-01',DEFAULT),
  (2,6,3,'+970599000000','Sales Rep',25000.00,'2023-02-01',DEFAULT);

INSERT INTO Employee_Branch (employee_id, branch_id, start_date, end_date) VALUES
  (1,1,'2023-01-02',null),
  (2,3,'2023-02-15',null);


/* Customers */
INSERT INTO Customer (customer_id, user_id, phone, created_at) VALUES
  (1,2,'+9876543210',DEFAULT),
  (2,5,'+970590000001',DEFAULT);

/* Suppliers */
INSERT INTO Supplier (supplier_id, name, email, phone_number, address_id, created_at) VALUES
  (1,'Supplier A','salesA@nutri.com','+1122334455',1,DEFAULT),
  (2,'Supplier B','salesB@gear.com','+5544332211',2,DEFAULT);

/* Products */
INSERT INTO Product (product_id, name, price, cost_price, category, description, img_path, created_at) VALUES
  (1,'Optimum Whey Protein',44.99,30.00,'Category 1','Top-selling whey protein','whey_protein.jpg',DEFAULT),
  (2,'Pre-Workout Blast',29.99,20.00,'Category 1','Explosive pre-workout formula','preworkout.jpg',DEFAULT),
  (3,'BCAA Recovery Mix',19.99,13.00,'Category 1','Essential BCAAs','bcaa.jpg',DEFAULT),
  (4,'Multivitamin Complex',17.49,12.00,'Category 1','Daily multivitamin','multivitamin.jpg',DEFAULT),
  (5,'Pro-Lift Lifting Straps',14.99,8.00,'Category 2','Durable straps','lifting_straps.jpg',DEFAULT),
  (6,'Resistance Bands Set',24.99,15.00,'Category 2','5-band mobility set','resistance_bands.jpg',DEFAULT),
  (7,'Insulated Gym Shaker',9.99,5.00,'Category 2','Leakproof shaker','gym_shaker.jpg',DEFAULT),
  (8,'Deluxe Protein Bar - Chocolate',2.99,1.50,'Category 3','High-protein snack','protein_bar_chocolate.jpg',DEFAULT),
  (9,'Crunchy Protein Cookies',5.49,2.20,'Category 3','Protein cookies','protein_cookies.jpg',DEFAULT),
  (10,'DC Oats',3.99,1.60,'Category 3','Protein oatmeal','protein_oats.jpg',DEFAULT),
  (11,'Cellucor C4 Original',32.99,22.00,'Category 1','#1 US pre-workout','C4_Original.webp',DEFAULT),
  (12,'XTEND Original BCAA',26.99,18.00,'Category 1','7 g BCAA drink mix','XTEND_BCAA.webp',DEFAULT),
  (13,'Dymatize ISO-100',44.99,30.00,'Category 1','Fast whey isolate','iso100.webp',DEFAULT);



INSERT INTO Product_Warehouse
        (product_id, warehouse_id,
         quantity_in_stock, minimum_stock, maximum_stock)
SELECT  p.product_id,
        w.warehouse_id,
        CASE
            WHEN w.warehouse_id = 1 THEN 60
            WHEN w.warehouse_id = 2 THEN 100
            ELSE 80
        END,
        10, 500          
FROM    Product   p
CROSS JOIN Warehouse w;


INSERT INTO Product_Branch
        (product_id, branch_id,
         quantity_in_stock, minimum_stock, maximum_stock)
SELECT  p.product_id,
        b.branch_id,
        10, 5, 60
FROM    Product p
CROSS JOIN Branch b;



INSERT INTO `Order` (order_id, customer_id, branch_id, sale_date, total_amount, profit_generated, status, processed_by) VALUES
  (10,1,1,DEFAULT,54.98,(44.99-30.00)+(9.99-5.00),'completed',1),
  (2,2,3,DEFAULT,29.99,(29.99-20.00),'completed',1);


INSERT INTO Order_Details (order_detail_id, order_id, product_id, quantity_sold, unit_price) VALUES
  (1,10,1,1,44.99),  
  (2,10,7,1,9.99),
  (3,2,2,1,29.99);   


/* Purchase Orders */
INSERT INTO Purchase_Order (purchase_order_id, warehouse_id, supplier_id, order_date, expected_delivery_date, status, created_at) VALUES
  (1,1,1,DATE_SUB(CURRENT_DATE,INTERVAL 30 DAY),DATE_SUB(CURRENT_DATE,INTERVAL 23 DAY),'delivered',DEFAULT),
  (2,2,2,DATE_SUB(CURRENT_DATE,INTERVAL 7 DAY),DATE_ADD(CURRENT_DATE,INTERVAL 7 DAY),'pending',DEFAULT);

INSERT INTO Purchase_Order_Details (purchase_order_id, product_id, quantity, unit_price, created_at) VALUES
  (1,1,120,30.00,DEFAULT),
  (1,3,80,13.00,DEFAULT),
  (2,11,50,22.00,DEFAULT);

select*from `order`;
select*from warehouse_branch_supply;

INSERT IGNORE INTO Warehouse_Branch_Supply (warehouse_id, branch_id, is_primary_supplier) VALUES
(1, 1, TRUE),
(1, 2, TRUE),
(1, 3, TRUE);
