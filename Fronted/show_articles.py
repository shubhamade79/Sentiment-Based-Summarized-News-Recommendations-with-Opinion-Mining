from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_mysqldb import MySQL
from datetime import datetime
import MySQLdb

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# MySQL Configurations
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'login'
mysql = MySQL(app)


@app.route('/')
def home():
    # Check if user is already logged in
    if 'username' in session:
        return redirect(url_for('articles'))  # Redirect to the articles page if logged in
    return render_template('summaries.html')  # Render the login page if not logged in


@app.route('/articles')
def articles():
    logged_in = 'username' in session
    return render_template('summaries.html', logged_in=logged_in)

@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('query', '').strip()
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    if query:
        # Full-text search in title, summary, and full_text
        search_query = f"""
            SELECT title, summary, link, image_url AS category_image, category, timestamp, sentiment
            FROM articles
            WHERE title LIKE %s OR category LIKE %s 
            ORDER BY timestamp DESC
        """
        search_term = f"%{query}%"
        cursor.execute(search_query, (search_term, search_term))
    else:
        cursor.execute('''
            SELECT title, summary, link, image_url AS category_image, category, timestamp, sentiment
            FROM articles
            ORDER BY timestamp DESC
        ''')
    
    articles = cursor.fetchall()

    # Format timestamp
    for article in articles:
        if article['timestamp']:
            article['timestamp'] = article['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
    
    # Render search results in the new template
    return render_template('search_results.html', articles=articles, query=query)

@app.route('/articles_data')
def articles_data():
    if 'username' in session:
        username = session['username']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT preferences FROM accounts WHERE username = %s', (username,))
        account = cursor.fetchone()
        preferences = account['preferences'].split(',') if account['preferences'] else []

        if preferences:
            placeholders = ', '.join(['%s'] * len(preferences))
            query = f'''
                SELECT title, summary, link, image_url, category, timestamp
                FROM articles
                WHERE category IN ({placeholders})
                ORDER BY timestamp DESC
                LIMIT 5
            '''
            cursor.execute(query, preferences)
        else:
            cursor.execute('''
                SELECT title, summary, link, image_url, category, timestamp
                FROM articles
                ORDER BY timestamp DESC
                LIMIT 5
            ''')
        articles = cursor.fetchall()
        for article in articles:
            if article['timestamp']:
                article['timestamp'] = article['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
        return jsonify(articles)
    else:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('''
            SELECT title, summary, link, image_url, category, timestamp
            FROM articles
            ORDER BY timestamp DESC
            LIMIT 5
        ''')
        articles = cursor.fetchall()
        for article in articles:
            if article['timestamp']:
                article['timestamp'] = article['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
        return jsonify(articles)
    
@app.route('/all_trending_articles')
def trending_data():
    if 'username' in session:
        username = session['username']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT preferences FROM accounts WHERE username = %s', (username,))
        account = cursor.fetchone()
        preferences = account['preferences'].split(',') if account['preferences'] else []

        if preferences:
            placeholders = ', '.join(['%s'] * len(preferences))
            query = f'''
                SELECT title, summary, link, image_url, category, timestamp
                FROM articles
                WHERE category IN ({placeholders})
                ORDER BY timestamp DESC
            '''
            cursor.execute(query, preferences)
        else:
            cursor.execute('''
                SELECT title, summary, link, image_url, category, timestamp
                FROM articles
                ORDER BY timestamp DESC
            ''')
        articles = cursor.fetchall()
        for article in articles:
            if article['timestamp']:
                article['timestamp'] = article['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
        return jsonify(articles)
    else:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('''
            SELECT title, summary, link, image_url, category, timestamp
            FROM articles
            ORDER BY timestamp DESC
        ''')
        articles = cursor.fetchall()
        for article in articles:
            if article['timestamp']:
                article['timestamp'] = article['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
        return jsonify(articles)

@app.route('/all_trending_articles_page')
def all_trending_articles_page():
    return render_template('trending.html')

@app.route('/About')
def About():
    return render_template('About.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('articles'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    msg = ''
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM accounts WHERE username = %s OR email = %s', (username, email))
        account = cursor.fetchone()
        
        if account:
            msg = 'Username or email already exists!'
        else:
            cursor.execute('INSERT INTO accounts (username, password, email) VALUES (%s, %s, %s)', (username, password, email))
            mysql.connection.commit()
            msg = 'You have successfully registered!'
            return redirect(url_for('login'))

        cursor.close()
    return render_template('register.html', msg=msg)

@app.route('/login', methods=['GET', 'POST'])
def login():
    msg = ''
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM accounts WHERE email = %s', (email,))
        account = cursor.fetchone()
        
        if account and account['password'] == password:
            session['username'] = account['username']
            if account['preferences']:
                return redirect(url_for('articles'))
            else:
                return redirect(url_for('preferences'))
        else:
            msg = 'Incorrect email or password!'
    return render_template('login.html', msg=msg)

@app.route('/preferences', methods=['GET', 'POST'])
def preferences():
    username = session['username']
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    if request.method == 'POST':
        selected_preferences = request.form.getlist('preferences')
        preferences_str = ','.join(selected_preferences)
        
        cursor.execute('UPDATE accounts SET preferences = %s WHERE username = %s', (preferences_str, username))
        mysql.connection.commit()
        return redirect(url_for('articles'))
    else:
        available_keywords = ['Sports', 'Lifestyle', 'Entertainment', 'Technology', 'India News', 'Trending', 'Cities', 'Education', 'World News']
        cursor.execute('SELECT preferences FROM accounts WHERE username = %s', (username,))
        account = cursor.fetchone()
        existing_preferences = account['preferences'].split(',') if account['preferences'] else []

        return render_template('preferences.html', available_keywords=available_keywords, existing_preferences=existing_preferences)

if __name__ == '__main__':
    app.run(debug=True, port=5001)


# from flask import Flask, render_template, request, redirect, url_for, session, jsonify
# from flask_mysqldb import MySQL
# import MySQLdb

# app = Flask(__name__)
# app.secret_key = 'your_secret_key'

# # MySQL Configurations
# app.config['MYSQL_HOST'] = 'localhost'
# app.config['MYSQL_USER'] = 'root'
# app.config['MYSQL_PASSWORD'] = ''
# app.config['MYSQL_DB'] = 'login'
# mysql = MySQL(app)

# @app.route('/')
# def home():
#     return render_template('login.html')

# @app.route('/articles')
# def articles():
#     return render_template('summaries.html')

# @app.route('/articles_data')
# def articles_data():
#     username = session['username']
#     cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

#     # Fetch user preferences
#     cursor.execute('SELECT preferences FROM accounts WHERE username = %s', (username,))
#     account = cursor.fetchone()
#     preferences = account['preferences'].split(',') if account['preferences'] else []

#     # Fetch articles based on preferences
#     if preferences:
#         placeholders = ', '.join(['%s'] * len(preferences))
#         query = f'SELECT title, summary, question, link, image_url, category FROM articles WHERE category IN ({placeholders})'
#         cursor.execute(query, preferences)
#     else:
#         cursor.execute('SELECT title, summary, question, link, image_url, category FROM articles')

#     articles_data = cursor.fetchall()
#     cursor.close()
    
#     return jsonify(articles_data)

# @app.route('/logout')
# def logout():
#     session.clear()
#     return redirect(url_for('home'))

# @app.route('/register', methods=['GET', 'POST'])
# def register():
#     msg = ''
#     if request.method == 'POST':
#         username = request.form['username']
#         password = request.form['password']
#         email = request.form['email']

#         cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
#         cursor.execute('SELECT * FROM accounts WHERE username = %s OR email = %s', (username, email))
#         account = cursor.fetchone()
        
#         if account:
#             msg = 'Username or email already exists!'
#         else:
#             cursor.execute('INSERT INTO accounts (username, password, email) VALUES (%s, %s, %s)', (username, password, email))
#             mysql.connection.commit()
#             msg = 'You have successfully registered!'
#             return redirect(url_for('login'))

#         cursor.close()
#     return render_template('register.html', msg=msg)

# @app.route('/login', methods=['GET', 'POST'])
# def login():
#     msg = ''
#     if request.method == 'POST':
#         email = request.form['email']
#         password = request.form['password']
#         cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
#         cursor.execute('SELECT * FROM accounts WHERE email = %s', (email,))
#         account = cursor.fetchone()
        
#         if account and account['password'] == password:
#             session['username'] = account['username']
#             if account['preferences']:
#                 return redirect(url_for('articles'))
#             else:
#                 return redirect(url_for('preferences'))
#         else:
#             msg = 'Incorrect email or password!'
#     return render_template('login.html', msg=msg)

# @app.route('/preferences', methods=['GET', 'POST'])
# def preferences():
#     username = session['username']
#     cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

#     if request.method == 'POST':
#         selected_preferences = request.form.getlist('preferences')
#         preferences_str = ','.join(selected_preferences)
        
#         cursor.execute('UPDATE accounts SET preferences = %s WHERE username = %s', (preferences_str, username))
#         mysql.connection.commit()
#         return redirect(url_for('articles'))
#     else:
#         available_keywords = ['Sports', 'Lifestyle', 'Entertainment', 'Technology', 'India News', 'Trending', 'Cities', 'Education', 'World News']
#         cursor.execute('SELECT preferences FROM accounts WHERE username = %s', (username,))
#         account = cursor.fetchone()
#         existing_preferences = account['preferences'].split(',') if account['preferences'] else []

#         return render_template('preferences.html', available_keywords=available_keywords, existing_preferences=existing_preferences)

# if __name__ == '__main__':
#     app.run(debug=True, port=5001)


# from flask import Flask, render_template, request, redirect, url_for, session, jsonify
# from flask_mysqldb import MySQL
# import MySQLdb  # Import MySQLdb for database interactions

# app = Flask(__name__)
# app.secret_key = 'your_secret_key'  # Set your secret key for session management

# # MySQL Configurations
# app.config['MYSQL_HOST'] = 'localhost'  # Host where MySQL is running
# app.config['MYSQL_USER'] = 'root'       # MySQL username
# app.config['MYSQL_PASSWORD'] = ''        # MySQL password
# app.config['MYSQL_DB'] = 'login'         # Name of the MySQL database
# mysql = MySQL(app)                       # Initialize MySQL

# @app.route('/')
# def home():
#     """Render the login page."""
#     return render_template('login.html')

# @app.route('/articles')
# def articles():
#     username = session['username']  # Get logged-in username
#     cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
#     # Fetch user preferences
#     cursor.execute('SELECT preferences FROM accounts WHERE username = %s', (username,))
#     account = cursor.fetchone()
#     preferences = account['preferences'].split(',') if account['preferences'] else []

#     # If user has preferences, filter articles by those categories
#     if preferences:
#         placeholders = ', '.join(['%s'] * len(preferences))  # Prepare placeholders for query
#         query = f'SELECT title, summary, question, link, image_url, category FROM articles WHERE category IN ({placeholders})'
#         cursor.execute(query, preferences)
#     else:
#         # If no preferences, fetch all articles
#         cursor.execute('SELECT title, summary, question, link, image_url, category FROM articles')

#     articles_data = cursor.fetchall()
#     cursor.close()
    
#     print("Articles Data:", articles_data)  # Debugging line
#     return render_template('summaries.html', summaries=articles_data)

# @app.route('/logout')
# def logout():
#     session.clear()  # Clear the session
#     return redirect(url_for('home'))  # Redirect to the home page

# @app.route('/register', methods=['GET', 'POST'])
# def register():
#     """Handle user registration."""
#     msg = ''
#     if request.method == 'POST':
#         username = request.form['username']
#         password = request.form['password']
#         email = request.form['email']

#         cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

#         # Check if username or email already exists
#         cursor.execute('SELECT * FROM accounts WHERE username = %s OR email = %s', (username, email))
#         account = cursor.fetchone()
        
#         if account:
#             msg = 'Username or email already exists!'  # Error message if username or email is taken
#         else:
#             # Directly store the password without hashing (not recommended for security reasons)
#             cursor.execute('INSERT INTO accounts (username, password, email) VALUES (%s, %s, %s)', (username, password, email))
#             mysql.connection.commit()  # Commit the transaction to the database
#             msg = 'You have successfully registered!'
#             return redirect(url_for('login'))  # Redirect to login page after successful registration

#         cursor.close()  # Close the cursor

#     return render_template('register.html', msg=msg)  # Render the registration page with a message

# @app.route('/login', methods=['GET', 'POST'])
# def login():
#     """Handle user login."""
#     msg = ''
#     if request.method == 'POST':
#         email = request.form['email']
#         password = request.form['password']
#         cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
#         cursor.execute('SELECT * FROM accounts WHERE email = %s', (email,))
#         account = cursor.fetchone()
        
#         # Check if the account exists and if the password matches
#         if account and account['password'] == password:  # Direct comparison (not recommended for security)
#             session['username'] = account['username']  # Store username in session
            
#             # Check if the user has preferences set
#             if account['preferences']:  # If preferences exist
#                 return redirect(url_for('articles'))  # Redirect to articles page
#             else:
#                 return redirect(url_for('preferences'))  # Redirect to preferences page if no preferences set
#         else:
#             msg = 'Incorrect email or password!'  # Error message for failed login
#     return render_template('login.html', msg=msg)  # Render the login page with a message

# @app.route('/preferences', methods=['GET', 'POST'])
# def preferences():
#     username = session['username']  # Get logged-in username
#     cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

#     if request.method == 'POST':
#         # Process preferences form submission
#         selected_preferences = request.form.getlist('preferences')
#         preferences_str = ','.join(selected_preferences)  # Convert list to comma-separated string
        
#         # Update the preferences in the accounts table
#         cursor.execute('UPDATE accounts SET preferences = %s WHERE username = %s', (preferences_str, username))
#         mysql.connection.commit()  # Commit the transaction to the database
#         return redirect(url_for('articles'))  # Redirect to summaries page after saving
#     else:
#         # Retrieve available keywords and existing preferences
#         available_keywords = ['Sports', 'Lifestyle', 'Entertainment', 'Technology', 'India News', 'Trending', 'Cities', 'Education', 'World News']
#         cursor.execute('SELECT preferences FROM accounts WHERE username = %s', (username,))
#         account = cursor.fetchone()
        
#         # Split preferences string into a list
#         existing_preferences = account['preferences'].split(',') if account['preferences'] else []

#         return render_template('preferences.html', available_keywords=available_keywords, existing_preferences=existing_preferences)

# if __name__ == '__main__':
#     print("Starting the application...")  # Console message to indicate app start
#     app.run(debug=True, port=5001)  # Run the application on the specified port

# # from flask import Flask, render_template, jsonify
# # from flask_mysqldb import MySQL
# # import MySQLdb  # Add this import

# # app = Flask(__name__)

# # # MySQL Configurations
# # app.config['MYSQL_HOST'] = 'localhost'
# # app.config['MYSQL_USER'] = 'root'
# # app.config['MYSQL_PASSWORD'] = ''
# # app.config['MYSQL_DB'] = 'login'
# # mysql = MySQL(app)

# # @app.route('/')
# # def home():
# #     return render_template('summaries.html')

# # @app.route('/articles')
# # def articles():
# #     cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
# #     cursor.execute('SELECT title, summary, question, link, image_url,category FROM articles')
# #     articles_data = cursor.fetchall()
# #     return jsonify(articles_data)

# # if __name__ == '__main__':
# #     print("Starting the show articles application...")
# #     app.run(debug=True, port=5001)  # Change the port if neededfrom flask import Flask, render_template, request, redirect, url_for, session, jsonify


# from flask import Flask, render_template, request, redirect, url_for, session, jsonify
# from flask_mysqldb import MySQL
# import MySQLdb  # Import MySQLdb for database interactions

# app = Flask(__name__)
# app.secret_key = 'your_secret_key'  # Set your secret key for session management

# # MySQL Configurations
# app.config['MYSQL_HOST'] = 'localhost'  # Host where MySQL is running
# app.config['MYSQL_USER'] = 'root'       # MySQL username
# app.config['MYSQL_PASSWORD'] = ''        # MySQL password
# app.config['MYSQL_DB'] = 'login'         # Name of the MySQL database
# mysql = MySQL(app)                       # Initialize MySQL

# @app.route('/')
# def home():
#     """Render the login page."""
#     return render_template('login.html')

# @app.route('/articles')
# def articles():
#     cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
#     cursor.execute('SELECT title, summary, question, link, image_url, category FROM articles')
#     articles_data = cursor.fetchall()
#     cursor.close()
    
#     print("Articles Data:", articles_data)  # Debugging line
#     return render_template('summaries.html', summaries=articles_data)
# @app.route('/logout')
# def logout():
#     session.clear()  # Clear the session
#     return redirect(url_for('login'))  # Redirect to the home page

# @app.route('/register', methods=['GET', 'POST'])
# def register():
#     """Handle user registration."""
#     msg = ''
#     if request.method == 'POST':
#         username = request.form['username']
#         password = request.form['password']
#         email = request.form['email']

#         cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

#         # Check if username or email already exists
#         cursor.execute('SELECT * FROM accounts WHERE username = %s OR email = %s', (username, email))
#         account = cursor.fetchone()
        
#         if account:
#             msg = 'Username or email already exists!'  # Error message if username or email is taken
#         else:
#             # Directly store the password without hashing (not recommended for security reasons)
#             cursor.execute('INSERT INTO accounts (username, password, email) VALUES (%s, %s, %s)', (username, password, email))
#             mysql.connection.commit()  # Commit the transaction to the database
#             msg = 'You have successfully registered!'
#             return redirect(url_for('login'))  # Redirect to login page after successful registration

#         cursor.close()  # Close the cursor

#     return render_template('register.html', msg=msg)  # Render the registration page with a message

# @app.route('/login', methods=['GET', 'POST'])
# def login():
#     """Handle user login."""
#     msg = ''
#     if request.method == 'POST':
#         email = request.form['email']
#         password = request.form['password']
#         cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
#         cursor.execute('SELECT * FROM accounts WHERE email = %s', (email,))
#         account = cursor.fetchone()
        
#         # Check if the account exists and if the password matches
#         if account and account['password'] == password:  # Direct comparison (not recommended for security)
#             session['username'] = account['username']  # Store username in session
#             return redirect(url_for('articles'))  # Redirect to articles page after successful login
#         else:
#             msg = 'Incorrect email or password!'  # Error message for failed login
#     return render_template('login.html', msg=msg)  # Render the login page with a message

# @app.route('/preferences', methods=['GET', 'POST'])
# def preferences():
#     if request.method == 'POST':
#         # Process preferences form submission
#         selected_preferences = request.form.getlist('preferences')
#         # Save selected preferences to the database
#         return redirect(url_for('summerize'))  # Redirect to another page after saving
#     else:
#         # Retrieve available keywords and existing preferences
#         available_keywords = ['Sports', 'Lifestyle', 'Entertainment', 'Technology', 'India News', 'Trending', 'Cities', 'Education', 'World News']
#         existing_preferences = []  # Fetch this from the database for the logged-in user
#         return render_template('preferences.html', available_keywords=available_keywords, existing_preferences=existing_preferences)

# @app.route('/edit_preferences', methods=['GET', 'POST'])
# def edit_preferences():
#     if request.method == 'POST':
#         # Process edit preferences form submission
#         updated_preferences = request.form.getlist('preferences')
#         # Update preferences in the database
#         return redirect(url_for('some_other_page'))  # Redirect to another page after updating
#     else:
#         # Retrieve available keywords and existing preferences
#         available_keywords = ['Sports', 'Lifestyle', 'Entertainment', 'Technology', 'India News', 'Trending', 'Cities', 'Education', 'World News']
#         existing_preferences = []  # Fetch this from the database for the logged-in user
#         return render_template('edit_preferences.html', available_keywords=available_keywords, existing_preferences=existing_preferences)

# if __name__ == '__main__':
#     print("Starting the application...")  # Console message to indicate app start
#     app.run(debug=True, port=5001)  # Run the application on the specified port
