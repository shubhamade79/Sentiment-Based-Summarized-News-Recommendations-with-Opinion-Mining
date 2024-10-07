# Sentiment-Based-Summarized-News-Recommendations-with-Opinion-Mining


## Installation and Setup

To get started , follow these steps to set up your environment and install the necessary dependencies.

### Prerequisites
- Python (version 3.7 or later)
- pip (Python package manager)
- Access to a command-line interface
- Setup Database
  
1. Set up the MySQ database:

    Open a MySQL Workbench client and run the following commands to create the database and table:

    ```sql
    CREATE DATABASE IF NOT EXISTS `login` DEFAULT CHARACTER SET utf8 COLLATE utf8_general_ci;
    USE `login`;

    CREATE TABLE IF NOT EXISTS `accounts` (
        `id` int(11) NOT NULL AUTO_INCREMENT,
        `username` varchar(50) NOT NULL,
        `password` varchar(255) NOT NULL,
        `email` varchar(100) NOT NULL,
        PRIMARY KEY (`id`)
    );

    ALTER TABLE `accounts` ADD `preferences` TEXT;
    ```

2. Configure the database connection in `app.py`:

   Open `app.py` and ensure the MySQL configurations are set correctly:

    ```python
    app.config['MYSQL_HOST'] = 'localhost'
    app.config['MYSQL_USER'] = 'root'
    app.config['MYSQL_PASSWORD'] = 'your_password'
    app.config['MYSQL_DB'] = 'login'
    ```


### Step 1: Clone the Repository
First, clone the repository to your local machine:
```bash
git clone https://github.com/shubhamade79/Sentiment-Based-Summarized-News-Recommendations-with-Opinion-Mining.git
cd Sentiment-Based-Summarized-News-Recommendations-with-Opinion-Mining
```
### Step 2: Create a Virtual Environment
It's recommended to create a virtual environment to manage dependencies:
```bash
python -m venv venv
source venv/bin/activate  # For Unix or MacOS
venv\Scripts\activate  # For Windows
```

### Step 3: Install Dependencies
Install all the required libraries using pip:
```bash
pip install -r requirements.txt
```
If Doesn't Execute or Not Install Properly Then Install Manually
```bash
pip install flask requests beautifulsoup4 flask-mysqldb mysqlclient transformers torch
```
### Step 4: Run App.py File
```bash
flask run
```
If Doesn't Create the Virtual Environment Then Run Program By
```bash
python app.py
```
### Step 5: Click the link On Terminal Then Open The Website
```bash
(http://127.0.0.1:5000)
```
