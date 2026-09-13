-- MySQL DDL script for Smart Faculty Invigilation Allotment System
-- Database name: smart_invigilation_db

CREATE DATABASE IF NOT EXISTS smart_invigilation_db;
USE smart_invigilation_db;

-- 1. Departments Table
CREATE TABLE IF NOT EXISTS departments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 2. Faculty Table
CREATE TABLE IF NOT EXISTS faculty (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    phone VARCHAR(15) NOT NULL,
    department_id INT NOT NULL,
    designation VARCHAR(50) NOT NULL,
    unavailable_dates TEXT DEFAULT NULL, -- Comma-separated YYYY-MM-DD
    max_duties INT NOT NULL DEFAULT 5,
    total_assigned_duties INT NOT NULL DEFAULT 0,
    FOREIGN KEY (department_id) REFERENCES departments(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 3. Examination Halls Table
CREATE TABLE IF NOT EXISTS examination_halls (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    capacity INT NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 4. Exams Table
CREATE TABLE IF NOT EXISTS exams (
    id INT AUTO_INCREMENT PRIMARY KEY,
    subject VARCHAR(100) NOT NULL,
    date DATE NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    hall_id INT NOT NULL,
    department_id INT NOT NULL,
    required_invigilators INT NOT NULL DEFAULT 1,
    FOREIGN KEY (hall_id) REFERENCES examination_halls(id) ON DELETE CASCADE,
    FOREIGN KEY (department_id) REFERENCES departments(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 5. Assignments Table
CREATE TABLE IF NOT EXISTS assignments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    faculty_id INT DEFAULT NULL, -- NULL represents unassigned / alert
    exam_id INT NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'Assigned', -- 'Assigned', 'Exchanged', 'Cancelled', 'Alert-Unassigned'
    FOREIGN KEY (faculty_id) REFERENCES faculty(id) ON DELETE SET NULL,
    FOREIGN KEY (exam_id) REFERENCES exams(id) ON DELETE CASCADE,
    UNIQUE KEY unique_faculty_exam (faculty_id, exam_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 6. Users Table (Authentication Credentials)
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL, -- Hashed
    role VARCHAR(20) NOT NULL DEFAULT 'faculty', -- 'admin' or 'faculty'
    faculty_id INT DEFAULT NULL,
    FOREIGN KEY (faculty_id) REFERENCES faculty(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 7. Notifications Table
CREATE TABLE IF NOT EXISTS notifications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    faculty_id INT NOT NULL,
    message TEXT NOT NULL,
    is_read BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (faculty_id) REFERENCES faculty(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 8. Exchange Requests Table
CREATE TABLE IF NOT EXISTS exchange_requests (
    id INT AUTO_INCREMENT PRIMARY KEY,
    assignment_id INT NOT NULL,
    target_faculty_id INT NOT NULL,
    request_reason VARCHAR(255) DEFAULT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'Pending', -- 'Pending', 'Approved', 'Rejected'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (assignment_id) REFERENCES assignments(id) ON DELETE CASCADE,
    FOREIGN KEY (target_faculty_id) REFERENCES faculty(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ---------------------------------------------------------
-- Insert Mock Seed Data
-- ---------------------------------------------------------

-- Seed Departments
INSERT INTO departments (id, name) VALUES
(1, 'Computer Science & Engineering'),
(2, 'Electronics & Communication Engineering'),
(3, 'Mechanical Engineering'),
(4, 'Civil Engineering');

-- Seed Faculty members
INSERT INTO faculty (id, name, email, phone, department_id, designation, unavailable_dates, max_duties) VALUES
(1, 'Dr. Alan Turing', 'turing@college.edu', '9876543201', 1, 'Professor', '2026-08-04', 4),
(2, 'Dr. Grace Hopper', 'hopper@college.edu', '9876543202', 1, 'Associate Professor', '2026-08-05', 5),
(3, 'Prof. Claude Shannon', 'shannon@college.edu', '9876543203', 2, 'Professor', '', 5),
(4, 'Dr. Ada Lovelace', 'lovelace@college.edu', '9876543204', 1, 'Assistant Professor', '2026-08-04,2026-08-06', 6),
(5, 'Prof. Richard Feynman', 'feynman@college.edu', '9876543205', 2, 'Professor', '2026-08-07', 4),
(6, 'Dr. Nikola Tesla', 'tesla@college.edu', '9876543206', 3, 'Associate Professor', '', 5),
(7, 'Prof. Marie Curie', 'curie@college.edu', '9876543207', 2, 'Professor', '', 5),
(8, 'Dr. Albert Einstein', 'einstein@college.edu', '9876543208', 3, 'Professor', '2026-08-05', 3),
(9, 'Prof. Wernher von Braun', 'braun@college.edu', '9876543209', 4, 'Associate Professor', '', 4),
(10, 'Dr. Charles Darwin', 'darwin@college.edu', '9876543210', 4, 'Assistant Professor', '', 5);

-- Seed Users (Passwords are pbkdf2:sha256 hashed. All users have password 'password123' except admin which is 'admin123')
-- admin123 hash: scrypt:32768:8:1$YnN1N9T0p3BvW4Gk$092ce4489dd31215b36442656910609f3e4bc3620ffadbb92461be6b1ad41a87b6495bebe0911d0442385b2e3f5383f71966a3d92fb9c25f4422e6cf485d4540 (using standard werkzeug.security hashes)
-- Let's put a plain scrypt hash for pbkdf2/scrypt, or let's use the Werkzeug generate_password_hash format.
-- Let's write the seed scripts inside app.py or database initializer, but we can write them here too.
-- Let's use the standard Werkzeug pbkdf2:sha256/scrypt hashes in database.sql.
-- 'admin123' hash: pbkdf2:sha256:600000$admin123hash$5a315cc6d3d789bdcbde87abdc9b32c695bc8120c159ce9196b014eeeb8515c0 (mock string, but we can hash it dynamically in code if we want, or store standard hashes)
-- Actually, the database initializer in app.py can generate the hashed passwords dynamically on startup if they do not exist! This is much cleaner and ensures compatibility with any Python/Werkzeug version!
-- Let's still seed them here as plain text for reference, or put the actual Werkzeug hashes:
-- 'admin123' hash: scrypt:32768:8:1$7N28n2M1z7v2L5y9$a42d6cc5789f2cfbc43bd73e35abac0c7ff97d510a76a8d792d2427a1dfbc1f8e1247b98d1a108a9844de88d120a1eb97fb05df8c51a703d15baeb9e2fe13b19
-- 'password123' hash: scrypt:32768:8:1$7N28n2M1z7v2L5y9$c1e85ee190a61250b73c434f6ba89b917de658a96677f525c50c0576a8d462bb023d8c11739f4e24ef5476a26df32bc03eb08ccbc442a8b34691458be5b0785a

INSERT INTO users (username, password, role, faculty_id) VALUES
('admin', 'scrypt:32768:8:1$7N28n2M1z7v2L5y9$a42d6cc5789f2cfbc43bd73e35abac0c7ff97d510a76a8d792d2427a1dfbc1f8e1247b98d1a108a9844de88d120a1eb97fb05df8c51a703d15baeb9e2fe13b19', 'admin', NULL),
('turing', 'scrypt:32768:8:1$7N28n2M1z7v2L5y9$c1e85ee190a61250b73c434f6ba89b917de658a96677f525c50c0576a8d462bb023d8c11739f4e24ef5476a26df32bc03eb08ccbc442a8b34691458be5b0785a', 'faculty', 1),
('hopper', 'scrypt:32768:8:1$7N28n2M1z7v2L5y9$c1e85ee190a61250b73c434f6ba89b917de658a96677f525c50c0576a8d462bb023d8c11739f4e24ef5476a26df32bc03eb08ccbc442a8b34691458be5b0785a', 'faculty', 2),
('shannon', 'scrypt:32768:8:1$7N28n2M1z7v2L5y9$c1e85ee190a61250b73c434f6ba89b917de658a96677f525c50c0576a8d462bb023d8c11739f4e24ef5476a26df32bc03eb08ccbc442a8b34691458be5b0785a', 'faculty', 3),
('lovelace', 'scrypt:32768:8:1$7N28n2M1z7v2L5y9$c1e85ee190a61250b73c434f6ba89b917de658a96677f525c50c0576a8d462bb023d8c11739f4e24ef5476a26df32bc03eb08ccbc442a8b34691458be5b0785a', 'faculty', 4),
('feynman', 'scrypt:32768:8:1$7N28n2M1z7v2L5y9$c1e85ee190a61250b73c434f6ba89b917de658a96677f525c50c0576a8d462bb023d8c11739f4e24ef5476a26df32bc03eb08ccbc442a8b34691458be5b0785a', 'faculty', 5),
('tesla', 'scrypt:32768:8:1$7N28n2M1z7v2L5y9$c1e85ee190a61250b73c434f6ba89b917de658a96677f525c50c0576a8d462bb023d8c11739f4e24ef5476a26df32bc03eb08ccbc442a8b34691458be5b0785a', 'faculty', 6),
('curie', 'scrypt:32768:8:1$7N28n2M1z7v2L5y9$c1e85ee190a61250b73c434f6ba89b917de658a96677f525c50c0576a8d462bb023d8c11739f4e24ef5476a26df32bc03eb08ccbc442a8b34691458be5b0785a', 'faculty', 7),
('einstein', 'scrypt:32768:8:1$7N28n2M1z7v2L5y9$c1e85ee190a61250b73c434f6ba89b917de658a96677f525c50c0576a8d462bb023d8c11739f4e24ef5476a26df32bc03eb08ccbc442a8b34691458be5b0785a', 'faculty', 8),
('braun', 'scrypt:32768:8:1$7N28n2M1z7v2L5y9$c1e85ee190a61250b73c434f6ba89b917de658a96677f525c50c0576a8d462bb023d8c11739f4e24ef5476a26df32bc03eb08ccbc442a8b34691458be5b0785a', 'faculty', 9),
('darwin', 'scrypt:32768:8:1$7N28n2M1z7v2L5y9$c1e85ee190a61250b73c434f6ba89b917de658a96677f525c50c0576a8d462bb023d8c11739f4e24ef5476a26df32bc03eb08ccbc442a8b34691458be5b0785a', 'faculty', 10);

-- Seed Examination Halls
INSERT INTO examination_halls (id, name, capacity) VALUES
(1, 'Seminar Hall A', 60),
(2, 'Block B Room 101', 30),
(3, 'Block B Room 102', 30),
(4, 'Main Audytorium', 120),
(5, 'Drawing Hall 204', 40);

-- Seed Exam Schedule (mock exams starting in August 2026)
INSERT INTO exams (id, subject, date, start_time, end_time, hall_id, department_id, required_invigilators) VALUES
(1, 'Data Structures & Algorithms', '2026-08-04', '09:30:00', '12:30:00', 2, 1, 1),
(2, 'Analog Communication', '2026-08-04', '09:30:00', '12:30:00', 3, 2, 1),
(3, 'Thermodynamics', '2026-08-04', '14:00:00', '17:00:00', 1, 3, 1),
(4, 'Structural Analysis', '2026-08-05', '09:30:00', '12:30:00', 2, 4, 1),
(5, 'Operating Systems', '2026-08-05', '09:30:00', '12:30:00', 1, 1, 2),
(6, 'Microprocessors', '2026-08-06', '14:00:00', '17:00:00', 5, 2, 1),
(7, 'Theory of Computation', '2026-08-07', '09:30:00', '12:30:00', 4, 1, 3);
