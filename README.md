# Jina.ai Markdown Processor

A desktop application for processing markdown content from web pages using Jina.ai API and GPT-4.

## Features

- Fetch markdown content from any web URL
- Process content with customizable system prompts
- Proxy support for requests
- Clean GUI interface with tabs for original and processed content
- Cross-platform compatibility

## Installation

### Prerequisites

- Python 3.8+
- pip

### Steps

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/jina-md-processor.git
   cd jina-md-processor
Install dependencies:

bash
Copy
pip install -r requirements.txt
Create a .env file in the project directory with your Jina.ai API key:

Copy
JINA_API_KEY=your_api_key_here
# Optional proxy configuration
PROXY_URL=your_proxy_url_here
Run the application:

bash
Copy
python main.py
Usage
Enter the URL of the webpage you want to process

(Optional) Configure proxy settings if needed

Adjust the system prompt if desired (or reset to default)

Click "Process Listing" to fetch and process the content

View results in the "Original Markdown" and "Processed Content" tabs

Configuration
You can customize the default prompts by editing the prompts.yaml file:

yaml
Copy
system_prompt: "Your default system prompt here"
user_prompt: "Your user prompt template here (use {content} for markdown insertion)"
Screenshot
Application Screenshot

Troubleshooting
If you get API errors, verify your Jina.ai API key is correct

For proxy issues, check your proxy URL and network settings

Ensure the target website is accessible and not blocking automated requests

License
MIT License

Contributing
Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.