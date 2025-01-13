from flask import Flask, render_template, redirect, url_for
from transformers import pipeline, T5ForConditionalGeneration, T5Tokenizer,BartTokenizer, BartForConditionalGeneration
import requests
from bs4 import BeautifulSoup
import MySQLdb.cursors
from flask_mysqldb import MySQL
from apscheduler.schedulers.background import BackgroundScheduler
from textblob import TextBlob  # Import TextBlob for sentiment analysis
from flask import current_app


app = Flask(__name__)
app.secret_key = 'your_secret_key'

# MySQL Configurations
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'login'
mysql = MySQL(app)

# Initialize models
print("Initializing models...")
tokenizer = BartTokenizer.from_pretrained('facebook/bart-large-cnn')
model = BartForConditionalGeneration.from_pretrained('facebook/bart-large-cnn')
question_model = T5ForConditionalGeneration.from_pretrained("ramsrigouthamg/t5_squad_v1")
question_tokenizer = T5Tokenizer.from_pretrained("ramsrigouthamg/t5_squad_v1")
print("Models initialized successfully.")

# Function to classify articles by keyword (remains unchanged)
def classify_articles_by_keyword(titles, full_articles, links, images):
    category_keywords = {
        "Sports": ["cricket", "sports"],
        "Lifestyle": ["lifestyle"],
        "Entertainment": ["entertainment"],
        "Technology": ["technology"],
        "Education": ["education"],
        "Cities": ["cities"],
        "Trending": ["trending"],
        "World News": ["world-news"],
        "India News": ["india-news"]
    }

    keyword_articles = {category: [] for category in category_keywords}
    added_articles = set()

    for title, full_article, link, image in zip(titles, full_articles, links, images):
        if title not in added_articles:
            for category, keywords in category_keywords.items():
                if any(keyword in link.lower() for keyword in keywords):
                    keyword_articles[category].append((title, full_article, link, image))
                    added_articles.add(title)
                    print(f"Added article '{title}' to category '{category}'")
                    break

    return keyword_articles


# Function to fetch and process news articles
def fetch_and_process_articles():
    base_url = "https://www.hindustantimes.com/latest-news"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    titles, links, summaries, images, questions, full_articles = [], [], [], [], [], []

    for page_num in range(1, 2):  # Change the range for more pages
        url = f"{base_url}/page-{page_num}"
        print(f"Fetching page: {url}")
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

                if link in links:
                    print(f"Skipping duplicate link: {link}")
                    continue

                titles.append(title)
                links.append(link)

                # Fetch full article text and image
                try:
                    print(f"Fetching article from: {link}")
                    article_r = requests.get(link, headers=headers)
                    article_r.raise_for_status()
                except requests.RequestException as e:
                    print(f"Error fetching article: {e}")
                    full_articles.append("Failed to retrieve article.")
                    images.append("No image available")
                    continue

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

                    # Summarize article
                    print("Summarizing article...")
                    # Summarize article
                    inputs = tokenizer([full_article], return_tensors='pt', max_length=1024, truncation=True)
                    summary_ids = model.generate(inputs['input_ids'], max_length=150, min_length=50, length_penalty=2.0, num_beams=4, early_stopping=True)
                    summary = tokenizer.decode(summary_ids[0], skip_special_tokens=True)
                    summaries.append(summary)
                    print(f"Summary generated: {summary}")

                    # Generate question
                    print("Generating yes/no question...")
                    question = generate_yes_no_question(summary)
                    questions.append(question)
                    print(f"Question generated: {question}")

                    # Perform sentiment analysis
                    sentiment = analyze_sentiment(full_article)
                    print(f"Sentiment analysis result: {sentiment}")

                    # Classify article by keyword
                    keyword_articles = classify_articles_by_keyword([title], [full_article], [link], [image_url])
                    categories = [category for category in keyword_articles if keyword_articles[category]]
                    category = categories[0] if categories else "Uncategorized"

                    # Store each article in the database
                    with mysql.connection.cursor() as cursor:
                        try:
                            cursor.execute('SELECT * FROM articles WHERE title = %s', (title,))
                            if cursor.fetchone() is None:  # Article does not exist
                                cursor.execute(
                                    'INSERT INTO articles (title, link, full_text, summary, question, image_url, category, sentiment) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)',
                                    (title, link, full_article, summary, question, image_url, category, sentiment)
                                )
                                mysql.connection.commit()
                                print(f"Stored article '{title}' in the database with category '{category}' and sentiment '{sentiment}'.")
                            else:
                                print(f"Article '{title}' already exists in the database.")
                        except Exception as e:
                            print(f"Error storing article: {e}")

    return titles, summaries, questions

# Function to analyze sentiment of the article
def analyze_sentiment(article_text):
    blob = TextBlob(article_text)
    polarity = blob.sentiment.polarity  # Range from -1 (negative) to 1 (positive)
    if polarity > 0:
        return 'Positive'
    elif polarity < 0:
        return 'Negative'
    else:
        return 'Neutral'


# Function to generate Yes/No question (remains unchanged)
def generate_yes_no_question(context):
    input_text = f"generate yes/no question: context: {context}"
    input_ids = question_tokenizer.encode(input_text, return_tensors='pt')
    outputs = question_model.generate(input_ids, max_length=64, num_beams=4, early_stopping=True)
    
    # Decode the generated output
    decoded_output = question_tokenizer.decode(outputs[0], skip_special_tokens=True)
    
    # Check if the output starts with "question:"
    if decoded_output.lower().startswith("question:"):
        # Extract the question text after "question:"
        decoded_output = decoded_output[9:].strip()  # Remove "question: " prefix
    
    return decoded_output


# Function to delete all data from the articles table
def delete_all_articles():
    with mysql.connection.cursor() as cursor:
        try:
            cursor.execute('DELETE FROM articles')
            mysql.connection.commit()
            print("All articles have been deleted from the database.")
        except Exception as e:
            print(f"Error deleting articles: {e}")

@app.route('/')
def home():
    return redirect(url_for('summarize'))

@app.route('/summarize', methods=['GET'])
def summarize():
    # Fetch and process articles when this route is accessed
    fetch_and_process_articles()

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT title, summary, question, link, image_url FROM articles')
    articles_data = cursor.fetchall()

    if articles_data:
        print(f"Found {len(articles_data)} articles in the database.")
        return "http://127.0.0.1:5001"
        # return render_template('summaries.html')
    else:
        print("No articles found in the database.")
        return "No articles found."


# Wrap fetch_and_process_articles to ensure it runs within an application context
def fetch_and_process_articles_job():
    with app.app_context():
        fetch_and_process_articles()

# Wrap delete_all_articles similarly
def delete_all_articles_job():
    with app.app_context():
        delete_all_articles()

def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(fetch_and_process_articles_job, 'interval', minutes=10)  # Run fetch job every 15 minutes
    scheduler.add_job(delete_all_articles_job, 'interval', minutes=20)  # Run delete job every 29 minutes
    scheduler.start()
    print("Scheduler started.")

import webbrowser

if __name__ == '__main__':
    print("Starting the Flask application...")
    start_scheduler()  # Start the scheduler
    # Open the web browser automatically
    webbrowser.open_new("http://127.0.0.1:5000/")
    webbrowser.open_new("http://127.0.0.1:5001/")

    app.run(debug=False)

