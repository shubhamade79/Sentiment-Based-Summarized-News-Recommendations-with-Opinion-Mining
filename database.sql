CREATE DATABASE IF NOT EXISTS `login` DEFAULT CHARACTER SET utf8 COLLATE utf8_general_ci;
USE `login`;

CREATE TABLE IF NOT EXISTS `accounts` (
	`id` int(11) NOT NULL AUTO_INCREMENT,
	`username` varchar(50) NOT NULL,
	`password` varchar(255) NOT NULL,
	`email` varchar(100) NOT NULL,
	PRIMARY KEY (`id`)
);

ALTER TABLE accounts ADD preferences TEXT;

CREATE TABLE articles (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `title` VARCHAR(255),
    `link` TEXT,
    `full_text` TEXT,
    `summary` TEXT,
    `question` TEXT,
    `image_url` TEXT,
    `category` VARCHAR(255)
);

ALTER TABLE articles ADD COLUMN sentiment VARCHAR(10);
ALTER TABLE articles ADD COLUMN timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

TRUNCATE TABLE login.articles;
select * from login.articles;

