# Queue Bot

A powerful and feature-rich Discord bot designed to manage queues, temporary voice channels, and provide robust voice channel moderation.

## 🌟 Features

- **Advanced Queue System**: Manage multiple queues for different purposes, such as main events and Twitch streams.
- **Temporary Voice Channels**: Automatically create and delete temporary voice channels as users join and leave.
- **Voice Channel Moderation**: A comprehensive suite of tools to moderate your voice channels, including a vote-kick system, channel banning, and automated quarantine for repeat offenders.
- **Twitch Integration**: A dedicated queue system for Twitch streamers to manage their viewer games.
- **Highly Configurable**: Customize the bot to your server's specific needs with a wide range of settings.
- **Slash Commands**: A modern and intuitive user experience with Discord's latest slash commands.

## 🚀 Getting Started

### Prerequisites

- Python 3.8 or higher
- A Discord Bot Token
- A MongoDB Atlas cluster

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-username/queue-bot.git
   cd queue-bot
   ```

2. **Install the dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Create a `.env` file in the root directory and add the following:**
   ```
   DISCORD_BOT_TOKEN=your_discord_bot_token
   MONGO_URI=your_mongodb_connection_string
   ```

4. **Run the bot:**
   ```bash
   python main.py
   ```

## 🤖 Commands

### Main Event Queue

- `/main_event_live_channel <channel>`: Set the voice channel for live events.
- `/main_event_queue_channels <channel>`: Add a voice channel to the queue.
- `/main_event_remove_queue_channel <channel>`: Remove a voice channel from the queue.
- `/main_event_queue_display_channel <channel>`: Set the text channel for displaying the queue.
- `/main_event_log_channel <channel>`: Set the text channel for logging events.
- `/main_event_clear_queue`: Clears the current queue.
- `/main_event_skip_queue`: Skips the first member in the queue.
- `/main_event_remove_queue <member>`: Removes a specific member from the queue.
- `/main_event`: Show the configured main event channels.

### Temporary Channels

- `/temp_channels <channel>`: Add a voice channel to create temporary channels from.
- `/remove_temp_channel <channel>`: Remove a voice channel from the temporary channel list.
- `/list_temp_channels`: List all configured temporary voice channels.

### Twitch Ward Queue

- `/set_waiting_channel <channel>`: Set the waiting room voice channel.
- `/set_live_channel <channel>`: Set the live voice channel.
- `/set_queue_log_channel <channel>`: Set the queue log text channel.
- `/set_queue_display_channel <channel>`: Set the public queue display channel.
- `/set_guests_limit <number>`: Set the max number of guests.
- `/show_queue`: Show the current queue manually.
- `/reset_queue`: Clear the entire queue.
- `/skip_queue`: Skip the next user in the waiting queue.
- `/toggle_queue_auto`: Enable or disable automatic queue filling.
- `/twitch_ward`: Display all configured Twitch Ward channels.

### VC Moderation

- `/remove_quarantine <member>`: Remove quarantine from a user.
- `/moderation_log_channel <channel>`: Set a moderation log channel.
- `/reset_ban <member>`: Reset the ban count for a user.

### General

- `/help`: Displays all available slash commands.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a pull request or open an issue.

## 🔗 Support

For support, questions, and feedback, please join our [Support Server](https://discord.gg/g3M4MWK).

To try out the bot, join the [Test Server](https://discord.gg/CB6NUzYWcn).