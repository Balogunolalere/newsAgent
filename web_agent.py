from typing import Dict, List, Union
import requests
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field
from mirascope.core import prompt_template
from mirascope.core.groq import groq_call
from mirascope.core.gemini import gemini_call
from dotenv import load_dotenv
from youtube_transcript_api import YouTubeTranscriptApi
import re
from colorama import init, Fore, Style
import time
import sys
from itertools import cycle
import threading
import os

load_dotenv()

# Qwant API class (expanded version)
class QwantApi:
    BASE_URL = "https://api.qwant.com/v3"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36"
        })
    
    def search(self, q: str, search_type: str = 'web', locale: str = 'en_US', offset: int = 0, safesearch: int = 1) -> Dict:
        params = {
            'q': q,
            'locale': locale,
            'offset': offset,
            'safesearch': safesearch
        }
        url = f"{self.BASE_URL}/search/{search_type}"
        response = self.session.get(url, params=params)
        return response.json() if response.status_code == 200 else None

# Model for structured response
class SearchResponse(BaseModel):
    answer: str = Field(description="The answer to the question")
    sources: List[str] = Field(description="The sources used to generate the answer")

class SearchType(BaseModel):
    search_type: str = Field(description="The type of search to perform (web, news, images, videos)")
    reasoning: str = Field(description="The reasoning behind the search type selection")

class OptimizedQuery(BaseModel):
    query: str = Field(description="The optimized search query")
    reasoning: str = Field(description="The reasoning behind the query optimization")


@groq_call("llama-3.3-70b-versatile", response_model=SearchType, json_mode=True)
@prompt_template(
"""
SYSTEM:
You are an expert at determining the most appropriate type of search for a given query. Your task is to analyze the user's question and decide which Qwant search type to use: web, news, images, or videos.

Follow these strict guidelines:
1. For general information queries, use 'web'.
2. For recent events, breaking news, or time-sensitive information, use 'news'.
3. For queries explicitly asking for images or visual content, use 'images'.
4. For queries about video content or asking for video results, use 'videos'.
5. If unsure, default to 'web'.

Provide your decision in a structured format with the search type and a brief explanation of your reasoning.

USER:
Determine the most appropriate search type for the following question:
{question}

ASSISTANT:
Based on the question, I will determine the most appropriate search type and provide my reasoning.
"""
)
def determine_search_type(question: str) -> SearchType:
    """
    Determine the most appropriate search type for the given question.
    """
    ...

def qwant_search(query: str, search_type: str, max_results: int = 5) -> Dict[str, str]:
    """
    Use Qwant to get information about the query using the specified search type.
    """
    print(f"Searching Qwant for '{query}' using {search_type} search...")
    search_results = {}
    urls = []  # Store original URLs
    qwant = QwantApi()
    results = qwant.search(query, search_type=search_type)
    
    if results and 'data' in results and 'result' in results['data'] and 'items' in results['data']['result']:
        items = results['data']['result']['items']
        if isinstance(items, dict) and 'mainline' in items:
            items = items['mainline']
        
        count = 0
        for item in items:
            if 'url' in item:
                url = item['url']
                print(f"Fetching content from {url}...")
                content = get_content(url)
                search_results[url] = content
                urls.append(url)  # Store the URL
                count += 1
                if count >= max_results:
                    break
            elif isinstance(item, dict) and 'items' in item:
                for subitem in item['items']:
                    if 'url' in subitem:
                        url = subitem['url']
                        print(f"Fetching content from {url}...")
                        content = get_content(url)
                        search_results[url] = content
                        urls.append(url)  # Store the URL
                        count += 1
                        if count >= max_results:
                            break
                if count >= max_results:
                    break
    
    # Add URLs to search results metadata
    search_results['_urls'] = urls
    return search_results

def extract_youtube_id(url: str) -> Union[str, None]:
    """Extract YouTube video ID from URL."""
    try:
        pattern = r'(?:youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]+)'
        match = re.search(pattern, url)
        if match:
            return match.group(1)
        return None
    except Exception as e:
        print(f"Error extracting YouTube ID: {e}")
        return None

def get_youtube_transcript(video_id: str) -> str:
    """Get English transcript for a YouTube video."""
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        try:
            transcript = transcript_list.find_transcript(['en'])
        except:
            try:
                # If English isn't available, try to get any transcript and translate it
                transcript = transcript_list.find_transcript(transcript_list.transcript_data.keys())
                transcript = transcript.translate('en')
            except Exception as e:
                print(f"Translation error: {e}")
                return ""
        
        transcript_data = transcript.fetch()
        # Clean and format transcript text to avoid JSON issues
        cleaned_text = " ".join([
            entry['text'].replace('"', "'").replace('\n', ' ').strip()
            for entry in transcript_data
        ])
        return f"[Transcript] {cleaned_text}"
    except Exception as e:
        print(f"Error fetching transcript: {e}")
        return ""

def get_content(url: str) -> str:
    """
    Fetch and parse content from a URL, including YouTube transcripts.
    """
    data = []
    try:
        # Check if it's a YouTube URL
        video_id = extract_youtube_id(url)
        if video_id:
            transcript = get_youtube_transcript(video_id)
            if transcript:
                # Clean and format content to avoid JSON issues
                cleaned_transcript = transcript.replace('"', "'").replace('\\', '').strip()
                data.append(cleaned_transcript)
        
        # Get regular webpage content
        if not video_id:  # Only fetch webpage content for non-YouTube URLs
            response = requests.get(url)
            content = response.content
            soup = BeautifulSoup(content, "html.parser")
            paragraphs = soup.find_all("p")
            for paragraph in paragraphs:
                # Clean and format content to avoid JSON issues
                cleaned_text = paragraph.text.replace('"', "'").replace('\\', '').strip()
                if cleaned_text:
                    data.append(cleaned_text)
    except Exception as e:
        print(f"Error fetching content from {url}: {e}")
    
    # Join content without truncation
    return " ".join(data)

@gemini_call("gemini-2.0-flash-exp")
@prompt_template(
"""
SYSTEM:
You are a highly knowledgeable research assistant with expertise in analyzing and synthesizing information.
Your goal is to provide comprehensive, well-researched answers using the search results.

Guidelines for analysis:
1. Thoroughly examine all provided sources
2. Cross-reference information between sources
3. Consider multiple perspectives and viewpoints
4. Identify key facts, statistics, and expert opinions
5. Look for recent and historical context
6. Evaluate the credibility of sources

Search results:
{search_results}

USER:
Analyze the following question and provide a detailed response:
{question}

Include in your analysis:
- Main findings and key points
- Supporting evidence and data
- Expert opinions and quotes
- Historical or contextual background
- Different perspectives if applicable
- Limitations or uncertainties in the information
"""
)
def search(question: str, search_results: Dict[str, str]) -> str:
    ...

@gemini_call("gemini-2.0-flash-exp", response_model=SearchResponse, json_mode=True)
@prompt_template(
"""
SYSTEM:
You are a professional content curator specializing in creating comprehensive, well-structured answers.
Your task is to synthesize information from multiple sources into a cohesive, detailed response.
Pay special attention to YouTube transcripts when available, as they may contain valuable spoken content.

Guidelines for response:
1. Start with a clear, concise summary of the main points
2. Structure the answer in logical sections with clear headings when appropriate
3. Include relevant quotes, statistics, and facts with proper citations
4. For YouTube content, cite specific content summaries
5. Provide context and background information
6. Address multiple aspects of the question
7. Cite sources using [Source X] notation for every major claim
8. End with a conclusion or summary of key takeaways

Format requirements:
- Keep responses concise and well-structured
- Use simple formatting to avoid JSON parsing issues
- Include direct quotes sparingly and with proper escaping
- Organize information in clear paragraphs
- Highlight key points without complex formatting
- Reference sources by number [Source X]
- For YouTube sources, reference them as "YouTube video [Source X]"

Search results:
{results}

USER:
{question}

Provide a clear, structured answer following the guidelines above.
"""
)
def extract(question: str, results: Dict[str, str]) -> SearchResponse:
    ...

def clean_text(text: str) -> str:
    """
    Clean the text data for better formatting and readability.
    """
    # Removing extra spaces and special characters
    return re.sub(r'\s+', ' ', text).strip()

class Spinner:
    def __init__(self, message="Loading..."):
        self.spinner = cycle(['⣾', '⣷', '⣯', '⣟', '⡿', '⢿', '⣻', '⣽'])
        self.running = False
        self.message = message
        self.thread = None

    def spin(self):
        while self.running:
            sys.stdout.write(f"\r{Fore.CYAN}{next(self.spinner)} {self.message}{Style.RESET_ALL}")
            sys.stdout.flush()
            time.sleep(0.1)
        sys.stdout.write('\r')
        sys.stdout.flush()

    def __enter__(self):
        self.running = True
        self.thread = threading.Thread(target=self.spin)
        self.thread.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.running = False
        if self.thread:
            self.thread.join()

def run(question: str) -> SearchResponse:
    """
    Orchestrate the search and extraction process to answer the user's question.
    """
    with Spinner("Determining search type..."):
        search_type_result = determine_search_type(question)
    print(f"\nSelected search type: {search_type_result.search_type}")
    print(f"Reasoning: {search_type_result.reasoning}\n")
    
    with Spinner("Searching and fetching results..."):
        search_results = qwant_search(question, search_type_result.search_type)
    
    with Spinner("Analyzing results..."):
        response = search(question, search_results)
        result = extract(question, search_results)
        
        # Update sources with original URLs if available
        if '_urls' in search_results:
            result.sources = search_results['_urls']
    
    result.answer = clean_text(result.answer)
    return result

def print_help():
    """Print help information."""
    print("\nAvailable Commands:")
    print("  help    - Show this help message")
    print("  clear   - Clear the screen")
    print("  quit    - Exit the program")
    print("  exit    - Exit the program\n")

def clear_screen():
    """Clear the terminal screen."""
    os.system('cls' if os.name == 'nt' else 'clear')

if __name__ == "__main__":
    init()  # Initialize colorama
    clear_screen()
    
    print("Welcome to the Search Assistant!")
    print("Type 'help' for available commands")

    try:
        while True:
            question = input("Your question: ").strip()
            
            if question.lower() in ['quit', 'exit']:
                print("Thank you for using the Search Assistant. Goodbye!")
                break
            elif question.lower() == 'help':
                print_help()
                continue
            elif question.lower() == 'clear':
                clear_screen()
                continue
            elif not question:
                continue
            
            try:
                response = run(question)
                print("\n" + "="*100)
                print("COMPREHENSIVE ANSWER:")
                print("="*100 + "\n")
                print(response.answer)
                print("\n" + "="*100)
                
                print("\nDETAILED SOURCES:")
                print("="*100)
                for idx, source in enumerate(response.sources, 1):
                    print(f"\n[Source {idx}]")
                    if "youtube.com" in source or "youtu.be" in source:
                        print(f"URL: {source}  (YouTube Video)")
                    else:
                        print(f"URL: {source}")
                    try:
                        response = requests.head(source, timeout=5)
                        if response.status_code == 200:
                            print(f"Status: Available | Last Referenced: {time.strftime('%Y-%m-%d %H:%M:%S')}")
                            print(f"Direct Link: {source}")
                        else:
                            print(f"Status: Not Available (Code: {response.status_code})")
                    except:
                        print("Status: Not Available (Connection Error)")
                    print("-"*100)
                
                print("\nNote: Click or copy the URLs above to access the original sources")
                print("="*100 + "\n")
                
            except Exception as e:
                print(f"\nError: {e}")
                print("Please try asking another question.")
                
    except KeyboardInterrupt:
        print("\nSearch Assistant terminated. Goodbye!")