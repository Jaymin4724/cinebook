-- =========================================
-- 1. TRUNCATE TABLES (safe order)
-- =========================================
TRUNCATE TABLE 
    roles_permissions_map,
    bookings,
    screens,
    layouts,
    theatres,
    movies,
    user_details,
    users,
    permissions,
    roles
CASCADE;


-- =========================================
-- 2. INSERT ROLES
-- =========================================
INSERT INTO roles (role) VALUES 
('user'), 
('admin'), 
('theatre_admin');


-- =========================================
-- 3. INSERT PERMISSIONS
-- =========================================
INSERT INTO permissions (permission) VALUES 
('create-user'), ('read-users'),

('create-theatre'), ('read-theatres'), ('delete-theatre'),

('create-movie'), ('read-movies'), ('delete-movie'),

('create-layout'),

('create-screen'), ('read-my-theatres'), ('read-my-screens'), ('delete-screen'),

('create-show'), ('delete-show');


-- =========================================
-- 4. MAP PERMISSIONS
-- =========================================

-- THEATRE ADMIN
INSERT INTO roles_permissions_map (role_id, permission_id)
SELECT r.id, p.id 
FROM roles r, permissions p
WHERE r.role = 'theatre_admin'
AND p.permission IN (
    'create-layout',
    'create-screen',
    'read-my-theatres',
    'read-my-screens',
    'delete-screen',
    'create-show',
    'delete-show'
);


-- ADMIN → ALL
INSERT INTO roles_permissions_map (role_id, permission_id)
SELECT r.id, p.id 
FROM roles r, permissions p
WHERE r.role = 'admin';


-- USER → BASIC
INSERT INTO roles_permissions_map (role_id, permission_id)
SELECT r.id, p.id 
FROM roles r, permissions p
WHERE r.role = 'user'
AND p.permission IN (
    'read-movies'
);


-- =========================================
-- 5. INSERT USERS
-- =========================================
INSERT INTO users (email, is_active, role_id) VALUES 
(
    'jaymin.dave@armakuni.com',
    TRUE,
    (SELECT id FROM roles WHERE role = 'admin')
),
(
    'jaymin4724@gmail.com',
    TRUE,
    (SELECT id FROM roles WHERE role = 'theatre_admin')
);


-- =========================================
-- 6. INSERT USER DETAILS
-- =========================================
INSERT INTO user_details (user_id)
SELECT id FROM users;


-- =========================================
-- 7. VERIFICATION
-- =========================================

-- Role-wise permission count
SELECT r.role, COUNT(rpm.permission_id) as total_permissions
FROM roles r
LEFT JOIN roles_permissions_map rpm ON r.id = rpm.role_id
GROUP BY r.role;

-- User → permissions mapping
SELECT u.email, r.role, p.permission
FROM users u
JOIN roles r ON u.role_id = r.id
JOIN roles_permissions_map rpm ON r.id = rpm.role_id
JOIN permissions p ON p.id = rpm.permission_id
ORDER BY u.email, p.permission;

select * from movies;