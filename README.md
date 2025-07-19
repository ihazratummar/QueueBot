# Discord Queue Bot

This bot is designed to manage a queue of users waiting to join a voice channel. It's perfect for streamers, community events, or any situation where you need to control the flow of users into a "live" voice channel.



## How it Works

The bot uses a simple and effective system:

1.  **Waiting Room:** Users who want to join the live channel first join a designated "waiting room" voice channel.
2.  **Queue:** When a user joins the waiting room, they are automatically added to a queue.
3.  **Live Room & Server Owner:** The bot checks if the server owner is in the "live" voice channel. If the owner is present and there are open spots, the bot will automatically move users from the queue into the live channel until the guest limit is reached.
4.  **Queue Display:** A special text channel displays the current queue in real-time, so everyone can see who's next.

## Features

*   **Automatic Queue Management:** Users are automatically added to the queue when they join the waiting room.
*   **Automatic User-Moving:** The bot automatically moves users from the queue to the live channel when a spot opens up, as long as the server owner is also in the live channel.
*   **Live Queue Display:** A dedicated channel shows the current queue, which updates in real-time.
*   **Admin Commands:** Simple commands allow administrators to set up and manage the bot.
*   **Guest Limit:** You can set a limit on how many guests can be in the live channel at one time.
*   **Toggleable Auto-Queue:** You can enable or disable the automatic queue filling at any time.

## Commands

Here are the commands you can use to control the bot. All commands are slash commands (e.g., `/set_waiting_channel`).

### Admin Commands

These commands can only be used by server administrators.

*   `/set_waiting_channel [channel]` - Sets the voice channel that will be used as the waiting room.
*   `/set_live_channel [channel]` - Sets the voice channel that users will be moved to from the queue.
*   `/set_queue_log_channel [channel]` - Sets the text channel where the bot will log its actions (e.g., when it moves a user).
*   `/set_queue_display_channel [channel]` - Sets the text channel where the live queue will be displayed.
*   `/set_guests_limit [number]` - Sets the maximum number of guests that can be in the live channel at one time (not including the server owner).
*   `/reset_queue` - Clears the entire queue.
*   `/skip_queue` - Skips the next user in the queue.
*   `/toggle_queue_auto` - Enables or disables the automatic queue filling.

### User Commands

*   `/show_queue` - Manually updates the queue display.

## How to Use

1.  **Invite the Bot:** Invite the bot to your Discord server.
2.  **Create Channels:** Create the voice and text channels you want to use for the waiting room, live room, queue log, and queue display.
3.  **Set Up the Bot:** Use the admin commands to tell the bot which channels to use.
4.  **Start Queuing:** Have users join the waiting room voice channel. They will be automatically added to the queue.
5.  **Enjoy!** The bot will handle the rest, moving users from the queue to the live channel as space becomes available.
# QueueDiscordBot
# QueueBot-
