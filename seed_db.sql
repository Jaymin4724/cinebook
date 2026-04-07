-- table truncate 
TRUNCATE TABLE roles CASCADE
TRUNCATE TABLE users CASCADE
TRUNCATE TABLE permissions CASCADE
TRUNCATE TABLE roles_permissions_map CASCADE
TRUNCATE TABLE theatres CASCADE
TRUNCATE TABLE movies CASCADE
TRUNCATE TABLE screens CASCADE
TRUNCATE TABLE layouts CASCADE

-- insert roles 
INSERT INTO roles (role)
VALUES ('user'),('admin'),('theatre_admin')

select * from roles 

-- insert permissions 
INSERT INTO permissions (permission)
VALUES ('create-user'), ('create-theatre'), ('create-movie'), 
('read-users'), ('read-theatres'), ('read-movies'), ('create-layout'), ('create-screen')

select * from permissions 

-- insert roles_permissions_map
INSERT INTO roles_permissions_map (role_id,permission_id)
VALUES 
( 	
	(SELECT id FROM roles WHERE role = 'admin' LIMIT 1),
 	(SELECT id FROM permissions WHERE permission = 'read-users' LIMIT 1)
),
(
	(SELECT id FROM roles WHERE role = 'admin' LIMIT 1),
 	(SELECT id FROM permissions WHERE permission = 'read-theatres' LIMIT 1)
),
(
	(SELECT id FROM roles WHERE role = 'admin' LIMIT 1),
 	(SELECT id FROM permissions WHERE permission = 'read-movies' LIMIT 1)
),
( 	
	(SELECT id FROM roles WHERE role = 'admin' LIMIT 1),
 	(SELECT id FROM permissions WHERE permission = 'create-user' LIMIT 1)
),
(
	(SELECT id FROM roles WHERE role = 'admin' LIMIT 1),
 	(SELECT id FROM permissions WHERE permission = 'create-theatre' LIMIT 1)
),
(
	(SELECT id FROM roles WHERE role = 'admin' LIMIT 1),
 	(SELECT id FROM permissions WHERE permission = 'create-movie' LIMIT 1)
),
( 	
	(SELECT id FROM roles WHERE role = 'theatre_admin' LIMIT 1),
 	(SELECT id FROM permissions WHERE permission = 'create-layout' LIMIT 1)
),
( 	
	(SELECT id FROM roles WHERE role = 'theatre_admin' LIMIT 1),
 	(SELECT id FROM permissions WHERE permission = 'create-screen' LIMIT 1)
)
select * from roles_permissions_map

-- insert user(admin)
INSERT INTO users(email,is_active,role_id)
VALUES 
(
	'jaymin.dave@armakuni.com', TRUE, 
	( SELECT id FROM roles WHERE role = 'admin' LIMIT 1)
),
(
	'jaymin4724@gmail.com', TRUE, 
	( SELECT id FROM roles WHERE role = 'theatre_admin' LIMIT 1)
)

select * from users; 

-- insert empty user-details(of created user)
INSERT INTO user_details(user_id) 
VALUES
((SELECT id FROM users WHERE email = 'jaymin.dave@armakuni.com')),
((SELECT id FROM users WHERE email = 'jaymin4724@gmail.com'))

select * from user_details

select * from theatres
select * from movies
select * from layouts
select * from screens
