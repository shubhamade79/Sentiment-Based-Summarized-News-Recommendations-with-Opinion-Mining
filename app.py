from flask import Flask, render_template, redirect, url_for, request, session
import requests
from bs4 import BeautifulSoup
from transformers import pipeline
import pickle
import os
import MySQLdb.cursors
from flask_mysqldb import MySQL
import re

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# MySQL Configurations
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'login'
mysql = MySQL(app)
# # Function to fetch news articles

def fetch_news_articles():
    base_url = "https://www.hindustantimes.com/latest-news"
    titles, links, full_articles, images = [], [], [], []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    for page_num in range(1, 2):  # Adjust range for more pages
        url = f"{base_url}/page-{page_num}"
        r = requests.get(url, headers=headers)

        if r.status_code != 200:
            print(f"Failed to retrieve page {page_num}. Status code: {r.status_code}")
            continue

        soup = BeautifulSoup(r.text, "lxml")
        articles = soup.find_all("a", href=True)

        for article in articles:
            if "data-articleid" in article.attrs:
                title = article.text.strip()
                link = article.get("href")
                if link.startswith("/"):
                    link = f"https://www.hindustantimes.com{link}"

                # Check if this article has already been processed
                if link in links:
                    print(f"Skipping duplicate article: {link}")  # Debugging line
                    continue

                # Add the title and link only if it's not already in the list
                titles.append(title)
                links.append(link)

                # Fetch full article text and image
                try:
                    print(f"Fetching article from: {link}")  # Debugging line
                    article_r = requests.get(link, headers=headers)
                    article_r.raise_for_status()  # Raise for HTTP errors
                except requests.RequestException as e:
                    print(f"Error fetching article: {e}")
                    full_articles.append("Failed to retrieve article.")
                    images.append("No image available")
                    continue  # Skip to the next article

                if article_r.status_code == 200:
                    article_soup = BeautifulSoup(article_r.text, "lxml")
                    paragraphs = article_soup.find_all("p")
                    full_article = "\n".join(p.text.strip() for p in paragraphs) if paragraphs else "Content not found."
                    full_articles.append(full_article)

                    # Fetch the image
                    image1 = article_soup.find("div", class_='storyParagraphFigure')
                    image_url = "No image available"
                    if image1:
                        image2 = image1.find("figure")
                        if image2:
                            image3 = image2.find("span")
                            if image3:
                                image = image3.find("picture")
                                if image:
                                    img_tag = image.find("img")
                                    if img_tag and img_tag.get("src"):
                                        image_url = img_tag.get("src")
                                        if not image_url.startswith("http"):
                                            image_url = f"https://www.hindustantimes.com{image_url}"
                    images.append(image_url)
                else:
                    full_articles.append("Failed to retrieve article.")
                    images.append("No image available")
    
    print(f"Fetched {len(titles)} articles.")  # Debugging line
    return titles, links, full_articles, images



# Function to classify articles by keyword
def classify_articles_by_keyword(titles, full_articles, links, images):
    # Define category keywords
    category_keywords = {
        "Sports": ["cricket", "sports",],
        "Lifestyle": ["lifestyle"],
        "Entertainment": ["entertainment"],
        "Technology": ["technology"],
        "Education": ["education"],
        "Cities": ["cities"],
        "World-News": ["world-news"],
        "India-News": ["india-news"]
    }

    # Dictionary to hold categorized articles
    keyword_articles = {category: [] for category in category_keywords}
    
    # Set to keep track of processed article titles
    added_articles = set()

    for title, full_article, link, image in zip(titles, full_articles, links, images):
        for category, keywords in category_keywords.items():
            if title not in added_articles:
                # Check if any of the keywords match in title or link
                if any(keyword in title.lower() or keyword in link.lower() for keyword in keywords):
                    keyword_articles[category].append((title, full_article, link, image))
                    added_articles.add(title)
                    print(f"Added article '{title}' to category '{category}'")  # Debug print
    
    return keyword_articles


# Function to summarize selected articles
def summarize_articles(selected_articles):
    summarizer = pipeline("summarization", model="facebook/bart-large-cnn")
    summaries = []

    for title, article, link, image in selected_articles:
        if not title:
            continue
        try:
            article_excerpt = article[:1000]
            summary = summarizer(article_excerpt, max_length=150, min_length=80, do_sample=False)
            question = generate_yes_no_question(summary[0]['summary_text'])
            if question.lower().startswith("question:"):
                question = question[9:].strip()
            summaries.append((title, summary[0]['summary_text'], link, image, question))
        except Exception as e:
            print(f"Error summarizing article '{title}': {e}")
            summaries.append((title, "Summary generation failed.", link, image,"Question generation failed."))
    print(summaries)
    return summaries

@app.route('/')
def index():
    return render_template('login.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    msg = ''
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form:
        username = request.form['username']
        password = request.form['password']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM accounts WHERE username = %s AND password = %s', (username, password,))
        account = cursor.fetchone()
        if account:
            session['loggedin'] = True
            session['id'] = account['id']
            session['username'] = account['username']

            titles, links, full_articles, images = fetch_news_articles()
            keyword_articles = classify_articles_by_keyword(titles, full_articles, links, images)

            with open('keyword_articles.pkl', 'wb') as f:
                pickle.dump(keyword_articles, f)

            return redirect(url_for('preferences'))
        else:
            msg = "Invalid credentials. Please try again."

    return render_template('login.html', msg=msg)

@app.route('/logout')
def logout():
    session.pop('loggedin', None)
    session.pop('id', None)
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    msg = ''
    if request.method == 'POST':
        # Get form fields
        username = request.form.get('username')
        password = request.form.get('password')
        email = request.form.get('email')

        # Check for the existence of all fields
        if not all([username, password, email]):
            msg = 'Please fill out the form!'  # All fields must be filled
        elif not re.match(r'[A-Za-z0-9]+', username):
            msg = 'Username must contain only characters and numbers!'  # Username validation
        elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            msg = 'Invalid email address!'  # Email validation
        else:
            # Check if username already exists
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute('SELECT * FROM accounts WHERE username = %s', (username,))
            account = cursor.fetchone()

            if account:
                msg = 'Account already exists!'  # Username already taken
            else:
                # Insert the new account into the database
                cursor.execute('INSERT INTO accounts (username, password, email) VALUES (%s, %s, %s)', (username, password, email))
                mysql.connection.commit()  # Commit changes to the database
                msg = 'You have successfully registered!'  # Successful registration message

    return render_template('register.html', msg=msg)  # Render the registration template with message

@app.route('/preferences', methods=['GET', 'POST'])
def preferences():
    if 'username' not in session:
        return redirect(url_for('login'))

    # Fetch existing preferences from the database
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT preferences FROM accounts WHERE id = %s', (session['id'],))
    account = cursor.fetchone()

    # Convert the stored preferences string back to a list
    existing_preferences = account['preferences'].split(',') if account['preferences'] else []
    available_keywords = [
        "Sports", "Lifestyle", "Entertainment", "Technology",
        "Education", "Cities", "World-News", "India-News","Trending"
    ]
    # If preferences already exist, redirect to summarize
    if existing_preferences:
        return redirect(url_for('summarize'))

    if request.method == 'POST':
        selected_preferences = request.form.getlist('preferences')
        session['preferences'] = selected_preferences

        # Convert preferences list to a comma-separated string
        preferences_str = ','.join(selected_preferences)

        # Update user preferences in the database
        cursor.execute('UPDATE accounts SET preferences = %s WHERE id = %s', (preferences_str, session['id']))
        mysql.connection.commit()

        return redirect(url_for('summarize'))

    return render_template('preferences.html', existing_preferences=existing_preferences,available_keywords=available_keywords)

@app.route('/refresh', methods=['POST'])
def refresh():
    # Fetch new articles
    titles, links, full_articles, images = fetch_news_articles()  # Ensure correct variable order
    keyword_articles = classify_articles_by_keyword(titles, full_articles, links, images)
    
    # Save the new articles to the pickle file
    try:
        with open('keyword_articles.pkl', 'wb') as f:
            pickle.dump(keyword_articles, f)
        print("Pickle file updated successfully.")
    except Exception as e:
        print(f"Error updating pickle file: {e}")

    return redirect(url_for('summarize'))



@app.route('/summarize', methods=['GET'])
def summarize():
    if 'username' not in session:
        return redirect(url_for('login'))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT preferences FROM accounts WHERE id = %s', (session['id'],))
    account = cursor.fetchone()

    user_preferences = account['preferences'].split(',') if account['preferences'] else []

    if os.path.exists('keyword_articles.pkl'):
        with open('keyword_articles.pkl', 'rb') as f:
            keyword_articles = pickle.load(f)
    else:
        return redirect(url_for('index'))

    selected_articles = [
        (article, preference) for preference in user_preferences
        for article in keyword_articles.get(preference, [])
    ]

    summaries_with_category = []
    if selected_articles:
        for preference in user_preferences:
            # Get articles for each preference
            articles_for_preference = keyword_articles.get(preference, [])
            if articles_for_preference:
                summaries = summarize_articles(articles_for_preference)
                # Append summaries with their category
                summaries_with_category.extend([(summary[0], summary[1], summary[2], summary[3], preference,summary[4]) for summary in summaries])

    if summaries_with_category:
        print(summaries_with_category)
        return render_template('summaries.html', summaries=summaries_with_category, keyword=user_preferences)
    else:
        return "No articles found for the selected preferences."


# Add the edit preferences route
@app.route('/edit_preferences', methods=['GET', 'POST'])
def edit_preferences():
    if 'username' not in session:
        return redirect(url_for('login'))

    # Fetch existing preferences from the database
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT preferences FROM accounts WHERE id = %s', (session['id'],))
    account = cursor.fetchone()

    # Convert the stored preferences string back to a list
    existing_preferences = account['preferences'].split(',') if account['preferences'] else []

    # Available keywords
    available_keywords = [
        "Sports", "Lifestyle", "Entertainment", "Technology",
        "Education", "Cities", "World-News", "India-News","Trending"
    ]

    if request.method == 'POST':
        selected_preferences = request.form.getlist('preferences')
        session['preferences'] = selected_preferences

        # Convert preferences list to a comma-separated string
        preferences_str = ','.join(selected_preferences)

        # Update user preferences in the database
        cursor.execute('UPDATE accounts SET preferences = %s WHERE id = %s', (preferences_str, session['id']))
        mysql.connection.commit()

        return redirect(url_for('summarize'))

    return render_template('edit_preferences.html', existing_preferences=existing_preferences, available_keywords=available_keywords)

from transformers import T5ForConditionalGeneration, T5Tokenizer

def generate_yes_no_question(context, variation=None):
    model = T5ForConditionalGeneration.from_pretrained("ramsrigouthamg/t5_squad_v1")
    tokenizer = T5Tokenizer.from_pretrained("ramsrigouthamg/t5_squad_v1")

    input_text = f"generate yes/no question: context: {context}" if not variation else f"generate yes/no question: context: {context}. Variation: {variation}"
    input_ids = tokenizer.encode(input_text, return_tensors='pt')
    outputs = model.generate(input_ids, max_length=64, num_beams=4, early_stopping=True)

    return tokenizer.decode(outputs[0], skip_special_tokens=True)

