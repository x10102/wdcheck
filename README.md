# WDCheck
A discord bot for viewing an responding to WikiDot site applications

# Usage
1. Create a new WikiDot account and make it an administrator on your wiki

2. Set up a discord developer account, create a bot and invite it to your server

3. Clone the repo
    ```bash
    git clone https://github.com/x10102/wdcheck.git 
    ```

4. Install requirements
    ```bash
    pip install -r requirements.txt
    ```

5. Set up environment variables or a `.env` file
    ```dotenv
    BOT_TOKEN=<YOUR BOT TOKEN>
    WIKI_USER=<WIKI ADMIN USERNAME>
    WIKI_PASSWORD=<WIKI ADMIN PASSWORD>
    WIKI_NAME=<WIKI NAME (scp-wiki etc.)>
    DB_FILE=<DATABASE FILE NAME>
    LOG_FILE=<LOG FILE NAME>
    CONSOLE_CHANNEL=<YOUR ADMIN CHANNEL ID> 
    ```

6. Run the bot
    ```bash
    python3 main.py
    ```