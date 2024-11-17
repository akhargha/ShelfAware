from flask import Flask, render_template, request
from flask_bootstrap import Bootstrap
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain.llms import OpenAI

app = Flask(__name__)
Bootstrap(app)

# Set up the LLM (OpenAI's GPT-3/4 in this example)
llm = OpenAI(temperature=0, model="gpt-4", openai_api_key="YOUR_OPENAI_API_KEY")

# Define the prompt template for sentiment analysis
prompt = PromptTemplate(
    input_variables=["text"],
    template="Analyze the sentiment of the following text and classify it as 'Positive', 'Neutral', or 'Negative'."
             " Assign a score of +1 for Positive, 0 for Neutral, and -1 for Negative. Here is the text:\n{text}\n"
)

# Initialize the LLMChain
chain = LLMChain(llm=llm, prompt=prompt)

# Function to fetch and analyze reviews
def fetch_and_analyze_reviews(url):
    try:
        import requests
        from bs4 import BeautifulSoup

        # Fetch webpage content
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        # Extract main text from the page (simplified extraction)
        content = soup.get_text(separator=" ", strip=True)

        # Use LangChain to analyze the sentiment
        analysis = chain.run({"text": content})
        return {"url": url, "analysis": analysis.strip()}
    except Exception as e:
        return {"url": url, "analysis": f"Error: {str(e)}"}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    urls = request.form.get('urls')
    if not urls:
        return render_template('index.html', error="Please provide URLs.")

    # Split URLs by newline
    url_list = [url.strip() for url in urls.split("\n") if url.strip()]
    results = [fetch_and_analyze_reviews(url) for url in url_list]

    return render_template('results.html', results=results)

if __name__ == '__main__':
    app.run(debug=True)