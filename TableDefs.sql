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
    email VARCHAR(100) NOT NULL UNIQUE, 
    PRIMARY KEY (userName)
);

CREATE TABLE PersonPhone (
    userName VARCHAR(50) NOT NULL,
    phone VARCHAR(20) NOT NULL UNIQUE,
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

-- Role combination constraints 
-- 1. Staff CANNOT be a volunteer, conflict of interest in order supervision and delivery
-- 2. Staff CANNOT Be client, Creates conflict of interest if staff can create orders for themselves
-- 3. Staff CANNOT Be donor, to maintain transparency in donation process and item valuation and acceptance
-- 4. Volunteer CANNOT be a client or donor, conflict of interest in service delivery
-- 5. Client CAN be a donor as it promotes community involvement 

DELIMITER //

CREATE TRIGGER check_role_combinations
BEFORE INSERT ON Act
FOR EACH ROW
BEGIN
    DECLARE user_roles VARCHAR(100);
    
    -- Get existing roles for the user
    SELECT GROUP_CONCAT(roleID) INTO user_roles
    FROM Act
    WHERE userName = NEW.userName;
    
    -- Check staff combinations
    IF NEW.roleID = 'staff' AND 
       (user_roles LIKE '%volunteer%' OR 
        user_roles LIKE '%client%' OR 
        user_roles LIKE '%donor%')
    THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Staff members maintain operational oversight and cannot hold other roles to prevent conflicts of interest';
    END IF;
    
    -- Check if user already has staff role
    IF user_roles LIKE '%staff%' AND 
       (NEW.roleID = 'volunteer' OR 
        NEW.roleID = 'client' OR 
        NEW.roleID = 'donor')
    THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Staff members cannot take on additional roles to maintain organizational integrity';
    END IF;

    -- Check volunteer combinations
    IF NEW.roleID = 'volunteer' AND 
       (user_roles LIKE '%client%' OR 
        user_roles LIKE '%donor%')
    THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'A volunteer cannot be a client or donor as it creates a conflict of interest in service delivery and donation handling';
    END IF;
    
    -- Check if user has volunteer role when trying to be client or donor
    IF (NEW.roleID = 'client' OR NEW.roleID = 'donor') AND 
       user_roles LIKE '%volunteer%'
    THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'A volunteer cannot take on client or donor roles to maintain impartial service delivery';
    END IF;
END //

DELIMITER ;

-- Role Data
INSERT INTO Role (roleID, rDescription) VALUES 
('staff', 'Staff members who manage operations'),
('volunteer', 'Volunteers who help with deliveries'),
('client', 'Refugees and asylum seekers'),
('donor', 'People who donate items');

-- Person Data
INSERT INTO Person (userName, password, fname, lname, email) VALUES
('john_s', '618dea9700a79af1486435029ea0894b:a1d2b52c366b25b1d16d0b9b9a50d9f91cc3b6a9de816fddd1f86169330b4391', 'John', 'Smith', 'john.s@welcome.com'),
('mary_j', '8cd7ba337e5379f01aa4978b3b13cf7c:67ff73c6d1180295ad96cbc10ebe739de425818ca984773b39bb2fd1a7be04df', 'Mary', 'Johnson', 'mary.j@welcome.com'),
('david_w', 'df8864815a010ced2aab122b6563a22d:7af96354d61fba62b9ec8c42c6adc26f1f5d579171274a1cf02d101bcd47db30', 'David', 'Wilson', 'david.w@gmail.com'),
('sarah_b', '1f958013b919de23821738cad1d41d34:0986236a87cad3952e0c1a4c4c5cfe6fc7562cc082cc6dc3c158662ba212e457', 'Sarah', 'Brown', 'sarah.b@yahoo.com'),
('michael_d', '652f6f2bc29ba1bc6859547706f64fe5:dfd19375d4a09eaf6530ace16b8610f84670e8c0312183b0a762713bc8a2c6bb', 'Michael', 'Davis', 'michael.d@welcome.com'),
('lisa_m', 'a2067bcb33e998c0a1d5c79e6dfd42a4:a41efbfe9251c1f48409bc5df49ebe30167f8c446afeeff1f425dd99f7d63f10', 'Lisa', 'Miller', 'lisa.m@gmail.com'),
('james_h', '35918013ebdb64285ff9b025151f4a57:2a6bbd633e0ca3f0f0a32d36b7b3012dcfb2ce6dbf090c37200b8fa0a28bf109', 'James', 'Harris', 'james.h@yahoo.com'),
('emma_p', '74051403d86947bd80028a907a880127:c46b6214a7f3e1a7d2e19567906a311969aa11a36442e7de381efef7c39b37a8', 'Emma', 'Parker', 'emma.p@gmail.com'),
('peter_r', '1c62702f8dd884374f3a2b60bd1e6e37:c6ae752cd0a64c88ea125d1dd163a1bcf8f1ca06416c4bbb115cdc1a159b59ab', 'Peter', 'Roberts', 'peter.r@welcome.com'),
('susan_t', '5ccdbc00a82938b93a34eabe76215c86:4e7c045182a94ed98732addbe45817aebffce11887de9405451331807bd64b7d', 'Susan', 'Thompson', 'susan.t@welcome.com');

-- PersonPhone Data
INSERT INTO PersonPhone (userName, phone) VALUES
('john_s', '+15551234567'),
('john_s', '+15551234568'),
('mary_j', '+15552345678'),
('david_w', '+15553456789'),
('david_w', '+15553456790'),
('david_w', '+15553456791'),
('sarah_b', '+15554567890'),
('michael_d', '+15555678901'),
('michael_d', '+15555678902'),
('lisa_m', '+15556789012'),
('james_h', '+15557890123'),
('emma_p', '+15558901234'),
('emma_p', '+15558901235'),
('peter_r', '+15559012345'),
('susan_t', '+15550123456'),
('susan_t', '+15550123457');

-- Act Data (Role assignments with multiple roles where appropriate)
INSERT INTO Act (userName, roleID) VALUES
('john_s', 'staff'),
('mary_j', 'volunteer'),
('david_w', 'client'),
('sarah_b', 'donor'),
('michael_d', 'staff'),
('lisa_m', 'client'),
('james_h', 'volunteer'),
('emma_p', 'donor'),
('peter_r', 'volunteer'),
('susan_t', 'client'),
('sarah_b', 'client'),
('emma_p', 'client');

-- Category Data
INSERT INTO Category (mainCategory, subCategory, catNotes) VALUES
('Furniture', 'Beds', 'Bedroom furniture'),
('Furniture', 'Tables', 'All types of tables'),
('Furniture', 'Chairs', 'Seating furniture'),
('Furniture', 'Storage', 'Storage related furniture'),
('Electronics', 'TVs', 'Television sets'),
('Electronics', 'Appliances', 'Home appliances'),
('Kitchenware', 'Utensils', 'Cooking utensils'),
('Kitchenware', 'Cookware', 'Pots and pans'),
('Textiles', 'Bedding', 'Bed sheets and covers'),
('Textiles', 'Curtains', 'Window treatments'),
('Decor', 'Wall Art', 'Decorative items');

-- Location Data
INSERT INTO Location (roomNum, shelfNum, shelf, shelfDescription) VALUES
(1, 1, 'A1', 'Main storage front'),
(1, 2, 'A2', 'Main storage back'),
(2, 1, 'B1', 'Electronics section'),
(2, 2, 'B2', 'Furniture section 1'),
(2, 3, 'B3', 'Furniture section 2'),
(3, 1, 'C1', 'Kitchen items'),
(3, 2, 'C2', 'Textiles'),
(4, 1, 'D1', 'Temporary storage'),
(4, 2, 'D2', 'Sorting area'),
(4, 3, 'D3', 'Ready for delivery');

-- Item Data
INSERT INTO Item (iDescription, color, isNew, hasPieces, material, mainCategory, subCategory) VALUES
('Queen Bed Frame', 'Brown', FALSE, TRUE, 'Wood', 'Furniture', 'Beds'),
('Dining Table', 'Oak', FALSE, TRUE, 'Wood', 'Furniture', 'Tables'),
('Office Chair', 'Black', TRUE, TRUE, 'Leather', 'Furniture', 'Chairs'),
('Smart TV 55"', 'Black', TRUE, FALSE, 'Plastic', 'Electronics', 'TVs'),
('Microwave Oven', 'Silver', TRUE, FALSE, 'Metal', 'Electronics', 'Appliances'),
('Cooking Set', 'Silver', TRUE, TRUE, 'Stainless Steel', 'Kitchenware', 'Cookware'),
('Cutlery Set', 'Silver', TRUE, TRUE, 'Stainless Steel', 'Kitchenware', 'Utensils'),
('Queen Bedding', 'Blue', TRUE, FALSE, 'Cotton', 'Textiles', 'Bedding'),
('Curtain Set', 'Beige', TRUE, TRUE, 'Polyester', 'Textiles', 'Curtains'),
('Wall Painting', 'Multicolor', FALSE, FALSE, 'Canvas', 'Decor', 'Wall Art'),
('Coffee Table', 'Walnut', FALSE, TRUE, 'Wood', 'Furniture', 'Tables'),
('Desk Chair', 'Grey', TRUE, TRUE, 'Mesh', 'Furniture', 'Chairs'),
('Kitchen Cabinet', 'White', FALSE, TRUE, 'Wood', 'Furniture', 'Storage'),
('Study Desk', 'Black', FALSE, TRUE, 'Wood', 'Furniture', 'Tables'),
('Bookshelf', 'White', FALSE, TRUE, 'Wood', 'Furniture', 'Storage');

-- Piece Data
INSERT INTO Piece (ItemID, pieceNum, pDescription, length, width, height, roomNum, shelfNum, pNotes) VALUES
(1, 1, 'Headboard', 60, 3, 40, 2, 2, 'Good condition'),
(1, 2, 'Footboard', 60, 3, 30, 2, 2, 'Minor scratches'),
(1, 3, 'Side Rails', 80, 2, 8, 2, 2, 'Complete set'),
(2, 1, 'Table Top', 72, 36, 2, 2, 2, 'Excellent condition'),
(2, 2, 'Table Legs', 4, 4, 29, 2, 2, 'All hardware included'),
(3, 1, 'Seat Base', 20, 20, 5, 2, 3, 'New condition'),
(3, 2, 'Back Rest', 20, 5, 30, 2, 3, 'Perfect state'),
(3, 3, 'Armrests', 12, 3, 2, 2, 3, 'Adjustable'),
-- Items with single piece
(4, 1, 'Main Unit', 48, 30, 4, 2, 1, 'Smart TV complete unit'),
(5, 1, 'Microwave Body', 20, 15, 12, 2, 1, 'Full unit with turntable'),
(6, 1, 'Large Pot', 12, 12, 8, 3, 1, 'Like new'),
(6, 2, 'Medium Pot', 10, 10, 6, 3, 1, 'Like new'),
(6, 3, 'Small Pot', 8, 8, 5, 3, 1, 'Like new'),
(7, 1, 'Forks Set', 8, 2, 1, 3, 1, 'New in box'),
(7, 2, 'Spoons Set', 8, 2, 1, 3, 1, 'New in box'),
(7, 3, 'Knives Set', 8, 2, 1, 3, 1, 'New in box'),
(8, 1, 'Complete Set', 90, 90, 2, 3, 2, 'Queen size bedding set'),
(9, 1, 'Left Panel', 72, 2, 48, 3, 2, 'Main curtain piece'),
(9, 2, 'Right Panel', 72, 2, 48, 3, 2, 'Matching panel'),
(9, 3, 'Tie Backs', 24, 2, 1, 3, 2, 'Complete set'),
(10, 1, 'Complete Painting', 36, 2, 24, 4, 1, 'Framed artwork'),
(11, 1, 'Table Top', 40, 20, 2, 2, 2, 'Good condition'),
(11, 2, 'Legs', 2, 2, 18, 2, 2, 'Complete hardware'),
(11, 3, 'Support Bar', 38, 2, 2, 2, 2, 'Center support'),
(12, 1, 'Base', 20, 20, 5, 2, 3, 'Excellent'),
(12, 2, 'Wheels', 2, 2, 2, 2, 3, 'New condition'),
(12, 3, 'Armrests', 12, 3, 2, 2, 3, 'Adjustable'),
(13, 1, 'Cabinet Body', 30, 20, 40, 2, 2, 'Good condition'),
(13, 2, 'Doors', 15, 1, 38, 2, 2, 'With handles'),
(13, 3, 'Shelves', 28, 18, 1, 2, 2, 'Three pieces'),
(13, 4, 'Hardware', 1, 1, 1, 2, 2, 'Complete set'),
(14, 1, 'Desktop', 48, 24, 2, 2, 2, 'Sturdy'),
(14, 2, 'Legs', 2, 2, 29, 2, 2, 'Complete set'),
(14, 3, 'Cable Management', 46, 2, 1, 2, 2, 'Plastic cover'),
(14, 4, 'Hardware Set', 1, 1, 1, 2, 2, 'All screws included'),
(15, 1, 'Main Frame', 36, 12, 72, 2, 2, 'Solid wood'),
(15, 2, 'Shelves', 34, 11, 1, 2, 2, 'All 5 pieces'),
(15, 3, 'Back Panel', 36, 1, 72, 2, 2, 'Stabilizer'),
(15, 4, 'Hardware Kit', 1, 1, 1, 2, 2, 'Assembly parts');
-- DonatedBy Data
INSERT INTO DonatedBy (ItemID, userName, donateDate) VALUES
(1, 'sarah_b', '2024-11-15'),
(2, 'emma_p', '2024-11-20'),
(3, 'sarah_b', '2024-11-25'),
(4, 'emma_p', '2024-11-30'),
(5, 'sarah_b', '2024-12-01'),
(6, 'emma_p', '2024-12-02'),
(7, 'sarah_b', '2024-12-03'),
(8, 'emma_p', '2024-12-04'),
(9, 'sarah_b', '2024-12-05'),
(10, 'emma_p', '2024-12-06'),
(11, 'sarah_b', '2024-12-07'),
(12, 'emma_p', '2024-12-07'),
(13, 'sarah_b', '2024-12-08'),
(14, 'emma_p', '2024-12-08'),
(15, 'sarah_b', '2024-12-08');

-- Ordered Data
INSERT INTO Ordered (orderDate, orderNotes, supervisor, client) VALUES
('2024-11-15', 'First floor delivery', 'john_s', 'david_w'),
('2024-11-20', 'Afternoon only', 'michael_d', 'lisa_m'),
('2024-11-25', 'Weekend preferred', 'john_s', 'susan_t'),
('2024-11-30', 'Call before delivery', 'michael_d', 'david_w'),
('2024-12-01', 'Morning delivery', 'john_s', 'lisa_m'),
('2024-12-02', 'Fragile items', 'michael_d', 'susan_t'),
('2024-12-03', 'Assembly needed', 'john_s', 'david_w'),
('2024-12-04', 'After 2 PM', 'michael_d', 'lisa_m'),
('2024-12-05', 'Ground floor', 'john_s', 'susan_t'),
('2024-12-06', 'Special handling', 'michael_d', 'david_w'),
('2024-12-07', 'Multiple items', 'john_s', 'lisa_m'),
('2024-12-07', 'Urgent delivery', 'michael_d', 'susan_t'),
('2024-12-07', 'Standard delivery', 'john_s', 'david_w'),
('2024-12-08', 'With installation', 'michael_d', 'lisa_m'),
('2024-12-08', 'Careful handling', 'john_s', 'susan_t'),
('2024-12-08', 'Multiple pieces', 'michael_d', 'david_w'),
('2024-12-08', 'Heavy items', 'john_s', 'lisa_m'),
('2024-12-08', 'Basic delivery', 'michael_d', 'susan_t'),
('2024-12-08', 'Express delivery', 'john_s', 'david_w'),
('2024-12-08', 'Standard handling', 'michael_d', 'lisa_m');

-- ItemIn Data
INSERT INTO ItemIn (ItemID, orderID, found) VALUES
(1, 1, TRUE),
(2, 1, TRUE),
(3, 2, TRUE),
(4, 3, TRUE),
(5, 4, TRUE),
(6, 5, TRUE),
(7, 6, TRUE),
(8, 7, FALSE),
(9, 8, TRUE),
(10, 9, TRUE),
(11, 10, TRUE),
(12, 11, TRUE),
(13, 12, FALSE),
(14, 13, TRUE),
(15, 14, TRUE),
(1, 15, TRUE),
(2, 16, FALSE),
(3, 17, TRUE),
(4, 18, TRUE),
(5, 19, TRUE),
(6, 20, FALSE);

-- Delivered Data
INSERT INTO Delivered (userName, orderID, status, date) VALUES
('mary_j', 1, 'Delivered', '2024-11-16'),
('james_h', 1, 'Delivered', '2024-11-16'),
('peter_r', 2, 'Delivered', '2024-11-21'),
('mary_j', 3, 'Delivered', '2024-11-26'),
('james_h', 4, 'Delivered', '2024-12-01'),
('peter_r', 5, 'Delivered', '2024-12-02'),
('mary_j', 6, 'Delivered', '2024-12-03'),
('james_h', 7, 'InProgress', '2024-12-04'),
('peter_r', 8, 'InProgress', '2024-12-05'),
('mary_j', 9, 'InProgress', '2024-12-06'),
('james_h', 10, 'Pending', '2024-12-07'),
('peter_r', 11, 'Pending', '2024-12-07'),
('mary_j', 12, 'Pending', '2024-12-07'),
('james_h', 13, 'Pending', '2024-12-08'),
('peter_r', 14, 'Pending', '2024-12-08'),
('mary_j', 15, 'Pending', '2024-12-08'),
('james_h', 16, 'Pending', '2024-12-08'),
('peter_r', 17, 'Pending', '2024-12-08'),
('mary_j', 18, 'Pending', '2024-12-08'),
('james_h', 19, 'Pending', '2024-12-08'),
('peter_r', 20, 'Pending', '2024-12-08');

commit work;