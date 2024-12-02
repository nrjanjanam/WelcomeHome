DROP DATABASE welcomehome;

CREATE DATABASE welcomehome;

USE welcomehome;

CREATE TABLE Category (
    mainCategory VARCHAR(50) NOT NULL,
    subCategory VARCHAR(50) NOT NULL,
    catNotes TEXT,
    PRIMARY KEY (mainCategory, subCategory)
);

CREATE TABLE Item (
    ItemID INT NOT NULL AUTO_INCREMENT,
    iDescription TEXT,
    photo BLOB, -- BLOB is better here, but for simplicity, we change it to VARCHAR; For p3 implementation, we recommend you to implement as blob
    color VARCHAR(20),
    isNew BOOLEAN DEFAULT TRUE,
    hasPieces BOOLEAN,
    material VARCHAR(50),
    mainCategory VARCHAR(50) NOT NULL,
    subCategory VARCHAR(50) NOT NULL,
    PRIMARY KEY (ItemID),
    FOREIGN KEY (mainCategory, subCategory) REFERENCES Category(mainCategory, subCategory)
);


CREATE TABLE Person (
    userName VARCHAR(50) NOT NULL,
    password VARCHAR(400) NOT NULL,
    fname VARCHAR(50) NOT NULL,
    lname VARCHAR(50) NOT NULL,
    email VARCHAR(100) NOT NULL,
    PRIMARY KEY (userName)
);

CREATE TABLE PersonPhone (
    userName VARCHAR(50) NOT NULL,
    phone VARCHAR(20) NOT NULL,
    PRIMARY KEY (userName, phone),
    FOREIGN KEY (userName) REFERENCES Person(userName)
);

CREATE TABLE DonatedBy (
    ItemID INT NOT NULL,
    userName VARCHAR(50) NOT NULL,
    donateDate DATE NOT NULL,
    PRIMARY KEY (ItemID, userName),
    FOREIGN KEY (ItemID) REFERENCES Item(ItemID),
    FOREIGN KEY (userName) REFERENCES Person(userName)
);

CREATE TABLE Role (
    roleID VARCHAR(20) NOT NULL,
    rDescription VARCHAR(100),
    PRIMARY KEY (roleID)
);

CREATE TABLE Act (
    userName VARCHAR(50) NOT NULL,
    roleID VARCHAR(20) NOT NULL,
    PRIMARY KEY (userName, roleID),
    FOREIGN KEY (userName) REFERENCES Person(userName),
    FOREIGN KEY (roleID) REFERENCES Role(roleID)
);

CREATE TABLE Location (
    roomNum INT NOT NULL,
    shelfNum INT NOT NULL, -- not a point for deduction
    shelf VARCHAR(20),
    shelfDescription VARCHAR(200),
    PRIMARY KEY (roomNum, shelfNum)
);



CREATE TABLE Piece (
    ItemID INT NOT NULL,
    pieceNum INT NOT NULL,
    pDescription VARCHAR(200),
    length INT NOT NULL, -- for simplicity
    width INT NOT NULL,
    height INT NOT NULL,
    roomNum INT NOT NULL,
    shelfNum INT NOT NULL, 
    pNotes TEXT,
    PRIMARY KEY (ItemID, pieceNum),
    FOREIGN KEY (ItemID) REFERENCES Item(ItemID),
    FOREIGN KEY (roomNum, shelfNum) REFERENCES Location(roomNum, shelfNum)
);

CREATE TABLE Ordered (
    orderID INT NOT NULL AUTO_INCREMENT,
    orderDate DATE NOT NULL,
    orderNotes VARCHAR(200),
    supervisor VARCHAR(50) NOT NULL,
    client VARCHAR(50) NOT NULL,
    PRIMARY KEY (orderID),
    FOREIGN KEY (supervisor) REFERENCES Person(userName),
    FOREIGN KEY (client) REFERENCES Person(userName)
);

CREATE TABLE ItemIn (
    ItemID INT NOT NULL,
    orderID INT NOT NULL,
    found BOOLEAN DEFAULT FALSE,
    PRIMARY KEY (ItemID, orderID),
    FOREIGN KEY (ItemID) REFERENCES Item(ItemID),
    FOREIGN KEY (orderID) REFERENCES Ordered(orderID)
);


CREATE TABLE Delivered (
    userName VARCHAR(50) NOT NULL,
    orderID INT NOT NULL,
    status VARCHAR(20) NOT NULL,
    date DATE NOT NULL,
    PRIMARY KEY (userName, orderID),
    FOREIGN KEY (userName) REFERENCES Person(userName),
    FOREIGN KEY (orderID) REFERENCES Ordered(orderID)
);

-- Role Data
INSERT INTO Role (roleID, rDescription) VALUES
('staff', 'Staff members who manage operations'),
('volunteer', 'Volunteers who help with deliveries'),
('client', 'Refugees and asylum seekers'),
('donor', 'People who donate items');

-- Person Data
-- Password is same as username
INSERT INTO `` (`userName`,`password`,`fname`,`lname`,`email`) VALUES ('david_donor','885f629202ccdd28dc8f27a0acb87da6:00115ba11846af381ab603871f69f867c70dbdc529f23a856e498a7e181fb35f','David','Brown','david@email.com');
INSERT INTO `` (`userName`,`password`,`fname`,`lname`,`email`) VALUES ('john_staff','812328ea9d94ac8993356f88606a45ad:9de15d8150e7f0554f471e92692cd153cdd74e90ebd15725cd9ab71363fa5038','John','Anderson','john@welcomehome.org');
INSERT INTO `` (`userName`,`password`,`fname`,`lname`,`email`) VALUES ('mary_vol','45fae0ae42b2d839d8b1ee938b5df0d9:e22a4ac354df67262278d5fb1bad849ddb310e71806ec3bd72d57f72c6466e02','Mary','Wilson','mary@email.com');
INSERT INTO `` (`userName`,`password`,`fname`,`lname`,`email`) VALUES ('sara_client','997d7fa3a3b51eb00e876c48c1d247ba:97a22cfe7d5312970a9aa15c8a0f68a7ad90d33a0f14c75578c76083d7290fdf','Sara','Miller','sara@email.com');


-- Category Data
INSERT INTO Category (mainCategory, subCategory, catNotes) VALUES 
('Furniture', 'Chairs', 'Various types of chairs'),
('Furniture', 'Tables', 'Dining and coffee tables'),
('Furniture', 'Beds', 'Beds and mattresses'),
('Housewares', 'Kitchenware', 'Kitchen utensils and cookware'),
('Electronics', 'Appliances', 'Small household appliances');

-- Location Data
INSERT INTO Location (roomNum, shelfNum, shelf, shelfDescription) VALUES
(1, 1, 'A1', 'Front room, first shelf'),
(1, 2, 'A2', 'Front room, second shelf'),
(2, 1, 'B1', 'Storage room, first shelf'),
(2, 2, 'B2', 'Storage room, second shelf');

-- Item Data
INSERT INTO Item (iDescription, photo, color, isNew, hasPieces, material, mainCategory, subCategory) VALUES
('Dining Chair', 'chair1.jpg', 'Brown', FALSE, FALSE, 'Wood', 'Furniture', 'Chairs'),
('Coffee Table', 'table1.jpg', 'Black', FALSE, TRUE, 'Wood', 'Furniture', 'Tables'),
('Microwave', 'micro1.jpg', 'White', TRUE, FALSE, 'Metal', 'Electronics', 'Appliances');

INSERT INTO Piece (ItemID, pieceNum, pDescription, length, width, height, roomNum, shelfNum, pNotes) VALUES
(1, 1, 'Chair Base', 20, 20, 30, 1, 1, 'Good condition'),
(2, 1, 'Table Top', 40, 60, 5, 1, 2, 'Minor scratches'),
(2, 2, 'Table Legs', 5, 5, 25, 1, 2, 'Complete set');

-- DOnated By Data
INSERT INTO DonatedBy (ItemID, userName, donateDate) VALUES
(1, 'david_donor', '2024-01-15'),
(2, 'david_donor', '2024-01-15'),
(3, 'david_donor', '2024-01-16');

-- Ordered Data
INSERT INTO Ordered (orderDate, orderNotes, supervisor, client) VALUES
('2024-01-20', 'First floor delivery', 'john_staff', 'sara_client'),
('2024-01-21', 'Fragile items included', 'john_staff', 'sara_client');

-- Item In Data
INSERT INTO ItemIn (ItemID, orderID, found) VALUES
(1, 1, TRUE),
(2, 1, TRUE),
(3, 2, FALSE);

-- Delivered Data
INSERT INTO Delivered (userName, orderID, status, date) VALUES
('mary_vol', 1, 'Delivered', '2024-01-22'),
('mary_vol', 2, 'InProgress', '2024-01-23');

commit work;
