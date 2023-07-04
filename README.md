# BoomBot: Create your own music samples on Discord

BoomBot is a Discord bot that generates music samples in seconds using [MusicGen](https://github.com/facebookresearch/audiocraft). See the demo live [here](https://rachelspark--boombot-app-dev.modal.run/). You can try BoomBot out for yourself by joining the Discord server [here](https://discord.gg/CBekEF42) and typing `/generate` in the `#general` channel.

<img src="/fast-boombot-demo.gif" width="500" height="auto"/>

This entire app, from the backend API to the web app, is deployed serverlessly on [Modal](https://modal.com/).

## File structure

1. React Frontend (`src/frontend/`)
2. FastAPI server (`src/bot.py`)
3. Language model (`src/main.py`)

Read our accompanying [docs](https://modal.com/docs/guide/discord-musicgen) for further detail on how it all works.

## Developing locally

### Set up Modal

1. Create a [Modal](https://modal.com/) account.
2. Install `modal` in your current Python virtual environment (`pip install modal`)
3. Set up a Modal token in your environment (`modal token new`)

### Create a Discord app

Follow the steps in our [docs](https://modal.com/docs/guide/discord-musicgen#discord-bot) to create a new Discord app and [set up a Modal secret](https://modal.com/secrets/create) called `boombot-discord-secret` with the key `DISCORD_PUBLIC_KEY`.

You can serve the app ephemerally on Modal by running this command from the repo's root directory:

```shell
modal serve src.bot
```

You'll then see a URL printed in the terminal output (like `https://rachelspark--boombot-app-dev.modal.run`) that you can then use to navigate to the web app in your browser, and use as a root path for the webhook your Discord app will request when a user interacts with it. You should point your Discord app to your `POST` endpoint on this URL in the Discord Developer Portal (as explained in the [docs](https://modal.com/docs/guide/discord-musicgen#create-and-deploy-modal-webhook)) and develop the bot while the `modal serve` process is running, as changes to any of the project files will be automatically applied.

### Deploy your app

Once you're satisfied with your changes, your can deploy your app using

```shell
modal deploy src.bot
```

Make sure to update the URL your Discord app points to.
