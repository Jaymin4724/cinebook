-- 1. Table Truncate (Keeping your existing order)
TRUNCATE TABLE roles, users, permissions, roles_permissions_map, 
               theatres, movies, screens, layouts, bookings, 
               user_details CASCADE;

-- 2. Insert Roles
INSERT INTO roles (role) VALUES ('user'), ('admin'), ('theatre_admin');
select * from roles 

-- 3. Insert ALL Permissions (from your FastAPI code)
INSERT INTO permissions (permission) VALUES 
('create-user'), ('read-users'), 
('create-theatre'), ('read-theatres'), ('delete-theatre'),
('create-movie'), ('read-movies'), ('delete-movie'),
('create-layout'), 
('create-screen'), ('delete-screen'),
('create-show'), ('delete-show');
select * from permissions 

-- 4. Insert roles_permissions_map
-- Mapping THEATRE_ADMIN permissions
INSERT INTO roles_permissions_map (role_id, permission_id)
SELECT r.id, p.id 
FROM roles r, permissions p
WHERE r.role = 'theatre_admin' 
AND p.permission IN (
    'create-layout', 
    'create-screen', 'delete-screen', 
    'create-show', 'delete-show'
);
SELECT u.email, r.role, p.permission
FROM users u
JOIN roles r ON u.role_id = r.id
JOIN roles_permissions_map rpm ON r.id = rpm.role_id
JOIN permissions p ON p.id = rpm.permission_id
ORDER BY u.email, p.permission;

-- Mapping ADMIN permissions (Admin gets EVERYTHING)
INSERT INTO roles_permissions_map (role_id, permission_id)
SELECT r.id, p.id 
FROM roles r, permissions p
WHERE r.role = 'admin';

SELECT rpm.role_id, r.role, rpm.permission_id, p.permission 
FROM roles_permissions_map rpm 
JOIN roles r ON r.id = rpm.role_id
JOIN permissions p ON p.id = rpm.permission_id

-- 5. Insert Users
INSERT INTO users (email, is_active, role_id) VALUES 
('jaymin.dave@armakuni.com', TRUE, (SELECT id FROM roles WHERE role = 'admin')),
('jaymin4724@gmail.com', TRUE, (SELECT id FROM roles WHERE role = 'theatre_admin'));

-- 6. Insert User Details
INSERT INTO user_details (user_id) 
SELECT id FROM users;

-- Verification Queries
SELECT r.role, COUNT(rpm.permission_id) as total_permissions
FROM roles r
LEFT JOIN roles_permissions_map rpm ON r.id = rpm.role_id
GROUP BY r.role;