
# CineBook - Online Movie Ticket Booking System

## 1. Introduction

Backend system for CineBook, an online movie ticket booking platform with role-based access and real-time seat handling.

---

## 2. Architecture

* Routes handle requests and responses
* Services contain business logic
* Repositories interact with database
* Redis used for caching and locking
* Elasticsearch used for search

---

## 3. Authentication Flow

### OTP Login

1. User enters email
2. OTP is generated and stored in Redis with expiry
3. OTP is sent via email
4. User submits OTP
5. OTP is validated and removed
6. Access and refresh tokens are generated and returned in the response body

### Google Login

1. User is redirected to Google
2. Authorization code is received
3. Code is exchanged for user data
4. User is created or logged in

### Token Refresh & Logout

1. Every token carries a unique ID (`jti`); revoked tokens are recorded in Redis until they would have expired anyway
2. `POST /auth/refresh`: validates the refresh token, rejects it if already revoked, issues a new access + refresh pair, and revokes the old refresh token
3. `POST /auth/logout`: revokes the current access token, and the refresh token too if one is supplied
4. Every authenticated request checks the access token against the revocation list, so a logged-out token stops working immediately

---

## 4. Role and Permission System

* User is assigned a role
* Role is mapped to permissions
* Permission is checked before accessing protected routes

---

## 5. Admin Flow

1. Create user with role after OTP validation
2. Create theatre
3. Fetch movie data using IMDB ID and store
4. View users, theatres, movies with pagination
5. Delete entities using soft delete

---

## 6. Theatre Admin Flow

### Layout Creation

1. Validate theatre ownership
2. Validate layout structure
3. Transform layout into structured format
4. Store layout

### Screen Creation

1. Validate theatre ownership
2. Validate layout belongs to theatre
3. Create screen

### Show Creation

1. Validate screen ownership
2. Validate movie exists and get duration
3. Validate show timing constraints
4. Check overlapping shows
5. Validate category pricing
6. Create show

---

## 7. User Flow

### Browse

1. Fetch movies by theatre
2. Fetch theatres by movie
3. Fetch shows for theatre and movie
4. Fetch show details with layout

### Seat Locking

1. Fetch layout from Redis or generate
2. Check seat availability
3. Lock seats in Redis using atomic operation
4. Set expiry for locks

### Booking

1. Validate locked seats belong to user
2. Calculate total price
3. Create booking in database
4. Update seat status in Redis
5. Remove locks

### Booking History & Cancellation

1. `GET /users/bookings`: paginated booking history for the current user, newest first
2. `GET /users/bookings/{id}`: single booking detail, including per-seat status
3. `POST /users/bookings/{id}/cancel`: cancel a booking, allowed only more than 6 hours before showtime and only once
4. Cancelling marks the booking and its seats as cancelled and immediately frees the seats in the cached layout

### Profile

1. `GET /users/me`: fetch the current user's profile (email, role, first/last name, mobile number)
2. `PATCH /users/me`: partially update first name, last name, and/or mobile number

### Account

1. Delete user using soft delete

---

## 8. Seat Layout System

1. Fetch base layout from database
2. Add pricing based on category
3. Mark booked seats
4. Store layout in Redis
5. Update layout dynamically with locked seats

---

## 9. Search System

1. Store movie and theatre data in Elasticsearch
2. Sync data on insert and update events
3. Perform prefix-based search
4. Return matched results with relevance score

---

## 10. Caching Strategy

* Redis used for OTP, layouts, and locks
* Layout fetched from cache if available
* Fallback to database if not present

---

## 11. Key Design Decisions

* Redis used for handling concurrency
* Seat locking before booking
* Validation separated from business logic
* Soft delete for data safety
* Layered architecture for scalability

---

## 12. Conclusion

System is designed to handle booking flow with focus on consistency, performance, and clean structure.
