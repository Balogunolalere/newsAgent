# web_agent.py Documentation

## Overview
The `web_agent.py` module acts as a versatile search and content extraction agent. It leverages external APIs and libraries to provide relevant information and transcripts from web sources, including YouTube. 

## Key Functionalities
- **Qwant Search**: Searches web, news, images, or videos using Qwant's API.
- **Search Type Determination**: Automatically decides the most suitable search type (web, news, images, or videos) based on user input.
- **Content Extraction**: Fetches and parses website content and YouTube transcripts to generate comprehensive responses.
- **Pydantic Models**: Structures the search type assessment and final extracted content using data models for reliability.
- **Spinner and CLI**: Uses a spinner to indicate background processes and provides an interactive command-line interface.

## Setup and Installation
1. **Clone or Download** this repository.
2. Ensure **Python 3.9+** is installed.
3. Install required dependencies:
   - `requests`
   - `beautifulsoup4`
   - `pydantic`
   - `python-dotenv`
   - `youtube_transcript_api`
   - `colorama`
   - Other libraries specified in your environment
4. **Environment Variables**: Set them via `.env` if needed (e.g., for specialized keys).

## How It Works
1. **User Input**: Prompts the user for a question.
2. **Search Type**: Determines the appropriate search category (web, news, images, or videos).
3. **Results Gathering**: Fetches data from Qwant, storing both text and transcripts.
4. **Information Synthesis**: Combines search results into a single structured answer.
5. **CLI Output**: Presents a final answer, plus source URLs for verification.

## Usage
1. **Execute** `python web_agent.py` in your terminal.
2. Provide your queries interactively.
3. Use commands like `help`, `clear`, or `quit` for additional control.
4. Evaluate the printed comprehensive answer and source links in the terminal output.

## Folder Structure
- **web_agent.py**: Main script containing the agent logic, search operations, and CLI.
- **README.md**: This documentation.
- **.env**: Optional environment variables.
- **Requirements**: All dependencies listed in your package manager or environment file.

## Contributing
- Fork the repository and create feature branches for changes.
- Submit pull requests with concise commit messages.
- Ensure all tests pass and follow coding conventions.

## License
This project is available under an open license (check repository for details).

## Contact or Support
Please open an issue or discussion in the repository if you encounter problems or have suggestions.
